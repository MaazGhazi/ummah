"""
Script-Subtitle Merger Module

Combines subtitle timestamps with script scene context using fuzzy matching.
Produces a unified JSON dataset with timestamped dialogue and scene descriptions.
"""

import json
import re
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

# Try to import rapidfuzz, fall back to difflib if not available
try:
    from rapidfuzz import fuzz, process
    FUZZY_LIB = "rapidfuzz"
except ImportError:
    from difflib import SequenceMatcher
    FUZZY_LIB = "difflib"

from .srt_parser import SubtitleEntry, parse_srt, get_cleaned_entries, clean_subtitle_text
from .script_parser import (
    ScriptScene, ScriptElement, ElementType,
    parse_script, get_all_dialogue, get_scene_by_number
)


@dataclass
class DialogueMatch:
    """Represents a match between subtitle and script dialogue."""
    subtitle_text: str
    script_text: str
    character: str | None
    scene_number: int
    scene_heading: str
    similarity: float
    match_method: str


@dataclass
class MergedEntry:
    """A single entry in the merged dataset."""
    # Timestamp info
    index: int
    start_time: str
    end_time: str
    start_ms: int
    end_ms: int
    
    # Dialogue info
    subtitle_text: str
    cleaned_text: str
    character: str | None
    
    # Scene info
    scene_number: int | None
    scene_heading: str | None
    scene_location: str | None
    scene_time_of_day: str | None
    scene_description: str | None
    
    # Match metadata
    match_confidence: float
    match_method: str
    script_dialogue: str | None
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MergedDataset:
    """Complete merged dataset."""
    movie_title: str
    total_entries: int
    total_scenes: int
    high_confidence_matches: int
    low_confidence_matches: int
    unmatched_entries: int
    entries: list[MergedEntry] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "metadata": {
                "movie_title": self.movie_title,
                "total_entries": self.total_entries,
                "total_scenes": self.total_scenes,
                "high_confidence_matches": self.high_confidence_matches,
                "low_confidence_matches": self.low_confidence_matches,
                "unmatched_entries": self.unmatched_entries,
            },
            "entries": [e.to_dict() for e in self.entries]
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def save(self, filepath: str | Path):
        """Save dataset to JSON file."""
        Path(filepath).write_text(self.to_json(), encoding='utf-8')


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison.
    
    - Lowercase
    - Remove punctuation
    - Collapse whitespace
    """
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = ' '.join(text.split())
    return text


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two texts.
    
    Returns:
        Similarity score between 0.0 and 1.0
    """
    # Normalize both texts
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    
    if not norm1 or not norm2:
        return 0.0
    
    if FUZZY_LIB == "rapidfuzz":
        # Use token_sort_ratio for better matching of reordered words
        return fuzz.token_sort_ratio(norm1, norm2) / 100.0
    else:
        # Fallback to difflib
        return SequenceMatcher(None, norm1, norm2).ratio()


def find_best_dialogue_match(
    subtitle_text: str,
    script_dialogues: list[dict],
    threshold: float = 0.5,
    used_indices: set[int] | None = None
) -> tuple[dict | None, float, int]:
    """
    Find the best matching script dialogue for a subtitle entry.
    
    Args:
        subtitle_text: The subtitle text to match
        script_dialogues: List of {scene_number, scene_heading, character, text}
        threshold: Minimum similarity score to consider a match
        used_indices: Set of already-matched dialogue indices (for sequential matching)
    
    Returns:
        (matched_dialogue, similarity_score, index) or (None, 0.0, -1) if no match
    """
    if used_indices is None:
        used_indices = set()
    
    best_match = None
    best_score = 0.0
    best_idx = -1
    
    cleaned_subtitle = clean_subtitle_text(subtitle_text)
    
    for idx, dialogue in enumerate(script_dialogues):
        if idx in used_indices:
            continue
        
        score = calculate_similarity(cleaned_subtitle, dialogue["text"])
        
        if score > best_score and score >= threshold:
            best_score = score
            best_match = dialogue
            best_idx = idx
    
    return best_match, best_score, best_idx


def find_sequential_matches(
    subtitles: list[SubtitleEntry],
    script_dialogues: list[dict],
    threshold: float = 0.5
) -> list[tuple[SubtitleEntry, dict | None, float]]:
    """
    Match subtitles to script dialogues using a sliding window approach.
    
    This approach assumes the script and subtitles follow roughly the same order,
    but allows for flexibility when the same line appears multiple times.
    
    The key insight: we prioritize matches that are CLOSE to our current position
    in the script, not just the best match anywhere.
    
    Returns:
        List of (subtitle, matched_dialogue, confidence) tuples
    """
    results = []
    used_indices = set()
    current_script_position = 0
    
    # Parameters for the sliding window
    LOOK_AHEAD = 50  # How far ahead to look for matches
    LOOK_BEHIND = 5  # How far behind to look (for missed matches)
    POSITION_BONUS = 0.15  # Bonus for matches near expected position
    
    for sub in subtitles:
        cleaned = clean_subtitle_text(sub.text)
        
        if not cleaned or len(cleaned) < 3:
            results.append((sub, None, 0.0))
            continue
        
        best_match = None
        best_score = 0.0
        best_idx = -1
        
        # Define search window around current position
        window_start = max(0, current_script_position - LOOK_BEHIND)
        window_end = min(len(script_dialogues), current_script_position + LOOK_AHEAD)
        
        for idx in range(window_start, window_end):
            if idx in used_indices:
                continue
            
            dialogue = script_dialogues[idx]
            base_score = calculate_similarity(cleaned, dialogue["text"])
            
            # Add position bonus for matches near expected position
            # Closer to current position = higher bonus
            distance = abs(idx - current_script_position)
            if distance <= 5:
                position_bonus = POSITION_BONUS
            elif distance <= 15:
                position_bonus = POSITION_BONUS * 0.5
            else:
                position_bonus = 0
            
            adjusted_score = min(1.0, base_score + position_bonus)
            
            if base_score >= threshold and adjusted_score > best_score:
                best_score = adjusted_score
                best_match = dialogue
                best_idx = idx
                # Store the actual similarity (not adjusted) for reporting
                best_score = base_score
        
        if best_match and best_idx >= 0:
            used_indices.add(best_idx)
            # Move position forward, but not too aggressively
            current_script_position = max(current_script_position, best_idx + 1)
        
        results.append((sub, best_match, best_score))
    
    return results


def find_global_best_matches(
    subtitles: list[SubtitleEntry],
    script_dialogues: list[dict],
    threshold: float = 0.5
) -> list[tuple[SubtitleEntry, dict | None, float]]:
    """
    Match subtitles to script dialogues using global best-match approach.
    
    This ignores order and just finds the best matching dialogue for each subtitle.
    Better for scripts with unique dialogue lines.
    
    Returns:
        List of (subtitle, matched_dialogue, confidence) tuples
    """
    results = []
    
    for sub in subtitles:
        cleaned = clean_subtitle_text(sub.text)
        
        if not cleaned or len(cleaned) < 3:
            results.append((sub, None, 0.0))
            continue
        
        best_match = None
        best_score = 0.0
        
        for dialogue in script_dialogues:
            score = calculate_similarity(cleaned, dialogue["text"])
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = dialogue
        
        results.append((sub, best_match, best_score))
    
    return results


class ScriptSubtitleMerger:
    """
    Merges subtitle files with script files to create a unified dataset.
    """
    
    def __init__(
        self,
        srt_path: str | Path,
        script_path: str | Path,
        movie_title: str = "Unknown Movie"
    ):
        self.srt_path = Path(srt_path)
        self.script_path = Path(script_path)
        self.movie_title = movie_title
        
        # Parse inputs
        self.subtitles = get_cleaned_entries(self.srt_path)
        self.scenes = parse_script(self.script_path)
        self.all_dialogue = get_all_dialogue(self.scenes)
        
        # Build scene lookup
        self._scene_map = {s.scene_number: s for s in self.scenes}
    
    
    def get_scene_context(self, scene_number: int) -> dict:
        """Get context information for a scene."""
        scene = self._scene_map.get(scene_number)
        if not scene:
            return {
                "heading": None,
                "location": None,
                "time_of_day": None,
                "description": None,
            }
        
        # Get action lines as scene description
        actions = [
            e.text for e in scene.elements
            if e.element_type == ElementType.ACTION.value
        ]
        description = " ".join(actions[:5])  # Limit to first 5 action lines
        
        return {
            "heading": scene.heading,
            "location": scene.location,
            "time_of_day": scene.time_of_day,
            "description": description if description else None,
        }
    
    def merge(
        self,
        match_threshold: float = 0.5,
        use_sequential: bool = False,
        match_strategy: str = "global"
    ) -> MergedDataset:
        """
        Perform the merge operation.
        
        Args:
            match_threshold: Minimum similarity score for a valid match
            use_sequential: Deprecated - use match_strategy instead
            match_strategy: "global" (best match anywhere), "sequential" (order-preserving)
        
        Returns:
            MergedDataset with all entries
        """
        entries = []
        high_conf = 0
        low_conf = 0
        unmatched = 0
        
        current_scene_num = None
        current_scene_heading = None
        
        # Choose matching strategy
        if match_strategy == "sequential" or use_sequential:
            matches = find_sequential_matches(
                self.subtitles,
                self.all_dialogue,
                threshold=match_threshold
            )
        else:  # global (default)
            matches = find_global_best_matches(
                self.subtitles,
                self.all_dialogue,
                threshold=match_threshold
            )
        
        for sub, matched_dialogue, confidence in matches:
            # Update current scene if we have a match
            if matched_dialogue:
                current_scene_num = matched_dialogue["scene_number"]
                current_scene_heading = matched_dialogue["scene_heading"]
            
            # Get scene context
            if current_scene_num:
                context = self.get_scene_context(current_scene_num)
            else:
                context = {
                    "heading": None,
                    "location": None,
                    "time_of_day": None,
                    "description": None,
                }
            
            # Determine match quality
            if confidence >= 0.8:
                match_method = "high_confidence_match"
                high_conf += 1
            elif confidence >= match_threshold:
                match_method = "low_confidence_match"
                low_conf += 1
            else:
                match_method = "unmatched_interpolated"
                unmatched += 1
            
            entry = MergedEntry(
                index=sub.index,
                start_time=sub.start_time,
                end_time=sub.end_time,
                start_ms=sub.start_ms,
                end_ms=sub.end_ms,
                subtitle_text=sub.text,
                cleaned_text=clean_subtitle_text(sub.text),
                character=matched_dialogue["character"] if matched_dialogue else None,
                scene_number=current_scene_num,
                scene_heading=context["heading"],
                scene_location=context["location"],
                scene_time_of_day=context["time_of_day"],
                scene_description=context["description"],
                match_confidence=confidence,
                match_method=match_method,
                script_dialogue=matched_dialogue["text"] if matched_dialogue else None,
            )
            
            entries.append(entry)
        
        return MergedDataset(
            movie_title=self.movie_title,
            total_entries=len(entries),
            total_scenes=len(self.scenes),
            high_confidence_matches=high_conf,
            low_confidence_matches=low_conf,
            unmatched_entries=unmatched,
            entries=entries,
        )


def merge_script_and_subtitles(
    srt_path: str | Path,
    script_path: str | Path,
    output_path: str | Path | None = None,
    movie_title: str = "Unknown Movie",
    match_threshold: float = 0.5,
) -> MergedDataset:
    """
    Convenience function to merge script and subtitles.
    
    Args:
        srt_path: Path to .srt subtitle file
        script_path: Path to script .txt file
        output_path: Optional path to save JSON output
        movie_title: Title of the movie
        match_threshold: Minimum similarity for matches
    
    Returns:
        MergedDataset object
    """
    merger = ScriptSubtitleMerger(srt_path, script_path, movie_title)
    dataset = merger.merge(match_threshold=match_threshold)
    
    if output_path:
        dataset.save(output_path)
    
    return dataset


if __name__ == "__main__":
    # Test with whiplash files
    project_root = Path(__file__).parent.parent
    srt_path = project_root / "whiplash_subs.srt"
    script_path = project_root / "whiplash_script.txt"
    output_path = project_root / "whiplash_merged.json"
    
    if srt_path.exists() and script_path.exists():
        print(f"Using fuzzy matching library: {FUZZY_LIB}")
        print(f"\nMerging:")
        print(f"  Subtitles: {srt_path}")
        print(f"  Script: {script_path}")
        
        dataset = merge_script_and_subtitles(
            srt_path=srt_path,
            script_path=script_path,
            output_path=output_path,
            movie_title="Whiplash",
            match_threshold=0.5,
        )
        
        print(f"\n=== Merge Results ===")
        print(f"Total entries: {dataset.total_entries}")
        print(f"Total scenes: {dataset.total_scenes}")
        print(f"High confidence matches: {dataset.high_confidence_matches}")
        print(f"Low confidence matches: {dataset.low_confidence_matches}")
        print(f"Unmatched entries: {dataset.unmatched_entries}")
        
        match_rate = (dataset.high_confidence_matches + dataset.low_confidence_matches) / dataset.total_entries * 100
        print(f"Match rate: {match_rate:.1f}%")
        
        print(f"\n=== Sample Entries ===")
        for entry in dataset.entries[:10]:
            print(f"\n[{entry.start_time}] ({entry.match_method}, conf={entry.match_confidence:.2f})")
            print(f"  Subtitle: {entry.subtitle_text[:60]}...")
            if entry.character:
                print(f"  Character: {entry.character}")
            if entry.scene_heading:
                print(f"  Scene: {entry.scene_heading[:60]}...")
        
        print(f"\nSaved to: {output_path}")
    else:
        print("Test files not found")
        if not srt_path.exists():
            print(f"  Missing: {srt_path}")
        if not script_path.exists():
            print(f"  Missing: {script_path}")
