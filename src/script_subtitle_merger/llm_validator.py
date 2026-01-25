"""
LLM Validator Module

Uses OpenAI to validate and enrich merged script-subtitle data.
Fixes incorrect matches, fills missing data, and improves overall quality.
"""

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    raise ImportError("openai package required. Install with: pip install openai")

from dotenv import load_dotenv

from .merger import MergedDataset, MergedEntry, OUTPUT_DIR


# Load environment variables
load_dotenv()


@dataclass
class ValidatedEntry:
    """A validated/corrected entry from LLM."""
    index: int
    validation_status: str  # "correct", "corrected", "unmatched"
    character: Optional[str]
    scene_number: Optional[int]
    scene_heading: Optional[str]
    script_dialogue: Optional[str]
    is_ad_lib: bool
    confidence_adjustment: float
    correction_notes: Optional[str]


def get_validation_prompt(movie_title: str) -> str:
    """Get the system prompt for LLM validation."""
    return f'''You are a movie dialogue analyst. Your task is to validate and enrich merged subtitle-script data for the film "{movie_title}".

## Context
You have been given:
1. **merged_entries** - Pre-merged subtitle entries with script matches (fuzzy-matched)
2. **subtitles** - Original subtitle content with timestamps
3. **script** - Original screenplay with scene headings, character names, and dialogue

## Your Tasks

### 1. VALIDATE MATCHES
For each entry in the merged data, verify the match quality:
- **correct**: The `script_dialogue` accurately matches the `subtitle_text` (same speaker, same line)
- **corrected**: The match was wrong and you found the correct one
- **unmatched**: No valid match exists in the script (ad-lib or changed line)

### 2. FIX INCORRECT MATCHES
For entries with low confidence or incorrect matches:
- Search the script to find the correct corresponding dialogue
- Update the `character`, `scene_number`, `scene_heading`, and `script_dialogue` fields
- If no match exists in the script (ad-lib, changed line), set `is_ad_lib: true`

### 3. FILL MISSING DATA
For entries with null values:
- Infer the `character` from context (previous/next lines, voice patterns)
- Infer the `scene_number` from surrounding matched entries
- Provide the correct `scene_heading` if determinable

### 4. OUTPUT FORMAT
Return ONLY a valid JSON array with ALL entries (both corrected and unchanged). For each entry:
```json
{{
  "index": <original_index>,
  "validation_status": "correct" | "corrected" | "unmatched",
  "character": "<character_name or null>",
  "scene_number": <scene_number or null>,
  "scene_heading": "<scene heading or null>",
  "script_dialogue": "<matched script line or null>",
  "is_ad_lib": <true if not in script, false otherwise>,
  "confidence_adjustment": <new confidence 0.0-1.0>,
  "correction_notes": "<brief explanation if corrected, null otherwise>"
}}
```

## Guidelines
- Trust high-confidence matches (≥0.8) unless clearly wrong
- Consider dialogue order - lines typically follow script sequence
- Account for subtitle line breaks (one script line may span multiple subtitles)
- Character names in scripts are UPPERCASE; match to subtitle context
- Scene headings follow format: INT./EXT. LOCATION - TIME
- Return ONLY the JSON array, no other text or markdown formatting'''


def create_batch_prompt(
    entries: list[dict],
    subtitles_content: str,
    script_content: str,
    batch_start: int,
    batch_end: int
) -> str:
    """Create the user prompt for a batch of entries."""
    return f'''## Merged Entries (batch {batch_start}-{batch_end})
```json
{json.dumps(entries, indent=2)}
```

## Original Subtitles (relevant section)
```
{subtitles_content[:15000]}
```

## Original Script (relevant section)
```
{script_content[:30000]}
```

Validate and return the corrected JSON array for these {len(entries)} entries.'''


class LLMValidator:
    """
    Validates and enriches merged script-subtitle data using OpenAI.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        batch_size: int = 50
    ):
        """
        Initialize the LLM validator.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: OpenAI model to use
            batch_size: Number of entries to process per API call
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.batch_size = batch_size
    
    def validate_batch(
        self,
        entries: list[dict],
        subtitles_content: str,
        script_content: str,
        movie_title: str,
        batch_start: int,
        batch_end: int
    ) -> list[dict]:
        """
        Validate a batch of entries using the LLM.
        
        Returns:
            List of validated/corrected entry dictionaries
        """
        system_prompt = get_validation_prompt(movie_title)
        user_prompt = create_batch_prompt(
            entries, subtitles_content, script_content, batch_start, batch_end
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for consistency
                max_tokens=4096
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean up response - remove markdown code blocks if present
            if content.startswith("```"):
                # Remove opening ```json or ```
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            return json.loads(content)
            
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse LLM response as JSON: {e}")
            print(f"Response was: {content[:500]}...")
            return []
        except Exception as e:
            print(f"Warning: LLM API call failed: {e}")
            return []
    
    def validate_dataset(
        self,
        merged_json_path: Path,
        srt_path: Path,
        script_path: Path,
        output_path: Optional[Path] = None,
        movie_title: Optional[str] = None
    ) -> dict:
        """
        Validate an entire merged dataset.
        
        Args:
            merged_json_path: Path to the v1 merged JSON file
            srt_path: Path to original .srt file
            script_path: Path to original script .txt file
            output_path: Path for v2 output (defaults to output/movie_v2.json)
            movie_title: Movie title (extracted from JSON if not provided)
        
        Returns:
            Dictionary with validation results and statistics
        """
        # Load inputs
        with open(merged_json_path, 'r', encoding='utf-8') as f:
            merged_data = json.load(f)
        
        with open(srt_path, 'r', encoding='utf-8') as f:
            subtitles_content = f.read()
        
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
        
        # Extract metadata
        if movie_title is None:
            movie_title = merged_data.get("metadata", {}).get("movie_title", "Unknown Movie")
        
        entries = merged_data.get("entries", [])
        total_entries = len(entries)
        
        print(f"Validating {total_entries} entries for '{movie_title}'...")
        print(f"Using model: {self.model}, batch size: {self.batch_size}")
        
        # Process in batches
        validated_entries = []
        stats = {
            "total": total_entries,
            "correct": 0,
            "corrected": 0,
            "unmatched": 0,
            "failed": 0
        }
        
        for i in range(0, total_entries, self.batch_size):
            batch_end = min(i + self.batch_size, total_entries)
            batch = entries[i:batch_end]
            
            print(f"Processing batch {i+1}-{batch_end} of {total_entries}...")
            
            validated_batch = self.validate_batch(
                batch,
                subtitles_content,
                script_content,
                movie_title,
                i + 1,
                batch_end
            )
            
            if validated_batch:
                validated_entries.extend(validated_batch)
                
                # Update stats
                for entry in validated_batch:
                    status = entry.get("validation_status", "correct")
                    if status in stats:
                        stats[status] += 1
            else:
                # If batch failed, keep original entries with minimal validation
                stats["failed"] += len(batch)
                for entry in batch:
                    validated_entries.append({
                        "index": entry["index"],
                        "validation_status": "unvalidated",
                        "character": entry.get("character"),
                        "scene_number": entry.get("scene_number"),
                        "scene_heading": entry.get("scene_heading"),
                        "script_dialogue": entry.get("script_dialogue"),
                        "is_ad_lib": False,
                        "confidence_adjustment": entry.get("match_confidence", 0.0),
                        "correction_notes": "LLM validation failed for this batch"
                    })
        
        # Merge validated data back with original entries
        validated_lookup = {e["index"]: e for e in validated_entries}
        
        final_entries = []
        for orig_entry in entries:
            idx = orig_entry["index"]
            validated = validated_lookup.get(idx, {})
            
            # Create merged entry with validated updates
            final_entry = {
                **orig_entry,
                "character": validated.get("character", orig_entry.get("character")),
                "scene_number": validated.get("scene_number", orig_entry.get("scene_number")),
                "scene_heading": validated.get("scene_heading", orig_entry.get("scene_heading")),
                "script_dialogue": validated.get("script_dialogue", orig_entry.get("script_dialogue")),
                "match_confidence": validated.get("confidence_adjustment", orig_entry.get("match_confidence", 0.0)),
                "validation_status": validated.get("validation_status", "unvalidated"),
                "is_ad_lib": validated.get("is_ad_lib", False),
                "correction_notes": validated.get("correction_notes")
            }
            final_entries.append(final_entry)
        
        # Build output
        output_data = {
            "metadata": {
                **merged_data.get("metadata", {}),
                "validation_stats": stats,
                "llm_model": self.model,
                "version": "v2"
            },
            "entries": final_entries
        }
        
        # Determine output path
        if output_path is None:
            safe_title = movie_title.lower().replace(" ", "_")
            output_path = OUTPUT_DIR / f"{safe_title}_v2.json"
        
        # Save output
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nValidation complete!")
        print(f"  Correct:    {stats['correct']}")
        print(f"  Corrected:  {stats['corrected']}")
        print(f"  Unmatched:  {stats['unmatched']}")
        print(f"  Failed:     {stats['failed']}")
        print(f"\nOutput saved to: {output_path}")
        
        return {
            "output_path": output_path,
            "stats": stats,
            "data": output_data
        }


def validate_merged_json(
    merged_json_path: str | Path,
    srt_path: str | Path,
    script_path: str | Path,
    output_path: Optional[str | Path] = None,
    movie_title: Optional[str] = None,
    model: str = "gpt-4o-mini",
    batch_size: int = 50,
    api_key: Optional[str] = None
) -> dict:
    """
    Convenience function to validate a merged JSON file.
    
    Args:
        merged_json_path: Path to the v1 merged JSON
        srt_path: Path to original .srt subtitle file
        script_path: Path to original script .txt file
        output_path: Path for v2 output JSON
        movie_title: Movie title
        model: OpenAI model to use
        batch_size: Entries per API call
        api_key: OpenAI API key (defaults to env var)
    
    Returns:
        Dictionary with output_path, stats, and data
    """
    validator = LLMValidator(
        api_key=api_key,
        model=model,
        batch_size=batch_size
    )
    
    return validator.validate_dataset(
        merged_json_path=Path(merged_json_path),
        srt_path=Path(srt_path),
        script_path=Path(script_path),
        output_path=Path(output_path) if output_path else None,
        movie_title=movie_title
    )
