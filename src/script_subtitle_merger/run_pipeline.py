#!/usr/bin/env python3
"""
Script-Subtitle Merger Pipeline

Full pipeline that:
1. Merges subtitle (.srt) and script (.txt) files using fuzzy matching (v1)
2. Validates and enriches the merged data using an LLM (v2)

Usage:
    python run_pipeline.py <srt_file> <script_file> [options]

Examples:
    python run_pipeline.py whiplash_subs.srt whiplash_script.txt -t "Whiplash"
    python run_pipeline.py movie.srt movie_script.txt -t "Movie" --skip-llm
    python run_pipeline.py subs.srt script.txt -t "Film" --model gpt-4o
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.script_subtitle_merger import (
    merge_script_and_subtitles,
    get_default_output_path,
    OUTPUT_DIR,
    FUZZY_LIB,
)


def run_merge_step(
    srt_path: Path,
    script_path: Path,
    movie_title: str,
    match_threshold: float,
    verbose: bool
) -> Path:
    """
    Step 1: Run fuzzy matching to create v1 merged JSON.
    
    Returns:
        Path to the v1 output file
    """
    print("=" * 60)
    print("STEP 1: Fuzzy Matching Merge")
    print("=" * 60)
    
    if verbose:
        print(f"Fuzzy matching library: {FUZZY_LIB}")
        print(f"Subtitle file: {srt_path}")
        print(f"Script file: {script_path}")
        print(f"Match threshold: {match_threshold}")
        print()
    
    # Get output path for v1
    safe_title = movie_title.lower().replace(" ", "_")
    v1_output = OUTPUT_DIR / f"{safe_title}_v1.json"
    
    print("Merging script and subtitles...")
    
    dataset = merge_script_and_subtitles(
        srt_path=srt_path,
        script_path=script_path,
        output_path=v1_output,
        movie_title=movie_title,
        match_threshold=match_threshold,
    )
    
    print(f"\nMerge Results:")
    print(f"  Total subtitle entries:    {dataset.total_entries}")
    print(f"  Total script scenes:       {dataset.total_scenes}")
    print(f"  High confidence matches:   {dataset.high_confidence_matches}")
    print(f"  Low confidence matches:    {dataset.low_confidence_matches}")
    print(f"  Unmatched entries:         {dataset.unmatched_entries}")
    
    if dataset.total_entries > 0:
        match_rate = (dataset.high_confidence_matches + dataset.low_confidence_matches) / dataset.total_entries * 100
        high_rate = dataset.high_confidence_matches / dataset.total_entries * 100
        print(f"\n  Overall match rate:        {match_rate:.1f}%")
        print(f"  High confidence rate:      {high_rate:.1f}%")
    
    print(f"\nV1 output saved to: {v1_output}")
    
    return v1_output


def run_llm_validation_step(
    v1_json_path: Path,
    srt_path: Path,
    script_path: Path,
    movie_title: str,
    model: str,
    batch_size: int,
    verbose: bool
) -> Path:
    """
    Step 2: Run LLM validation to create v2 enriched JSON.
    
    Returns:
        Path to the v2 output file
    """
    print("\n" + "=" * 60)
    print("STEP 2: LLM Validation & Enrichment")
    print("=" * 60)
    
    # Import here to avoid requiring openai if --skip-llm is used
    try:
        from src.script_subtitle_merger import validate_merged_json
    except ImportError as e:
        print(f"Error: Could not import LLM validator: {e}")
        print("Make sure openai and python-dotenv are installed:")
        print("  pip install openai python-dotenv")
        sys.exit(1)
    
    if verbose:
        print(f"Model: {model}")
        print(f"Batch size: {batch_size}")
        print(f"V1 input: {v1_json_path}")
        print()
    
    safe_title = movie_title.lower().replace(" ", "_")
    v2_output = OUTPUT_DIR / f"{safe_title}_v2.json"
    
    try:
        result = validate_merged_json(
            merged_json_path=v1_json_path,
            srt_path=srt_path,
            script_path=script_path,
            output_path=v2_output,
            movie_title=movie_title,
            model=model,
            batch_size=batch_size
        )
        
        return result["output_path"]
        
    except ValueError as e:
        print(f"\nError: {e}")
        print("\nTo use LLM validation, set your OpenAI API key:")
        print("  1. Copy .env_sample to .env")
        print("  2. Add your API key: OPENAI_API_KEY=sk-...")
        sys.exit(1)
    except Exception as e:
        print(f"\nError during LLM validation: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Full pipeline: merge subtitles with scripts, then validate with LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s whiplash_subs.srt whiplash_script.txt -t "Whiplash"
  %(prog)s movie.srt script.txt -t "My Movie" --skip-llm
  %(prog)s subs.srt script.txt -t "Film" --model gpt-4o --batch-size 30
        """
    )
    
    parser.add_argument(
        "srt_file",
        type=Path,
        help="Path to the subtitle file (.srt)"
    )
    
    parser.add_argument(
        "script_file",
        type=Path,
        help="Path to the screenplay script file (.txt)"
    )
    
    parser.add_argument(
        "-t", "--title",
        type=str,
        default="Unknown Movie",
        help="Movie title for output files and metadata (default: Unknown Movie)"
    )
    
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Match confidence threshold 0.0-1.0 for fuzzy matching (default: 0.5)"
    )
    
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip LLM validation step (only produce v1 output)"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="OpenAI model to use for validation (default: gpt-4o-mini)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of entries per LLM API call (default: 50)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.srt_file.exists():
        print(f"Error: Subtitle file not found: {args.srt_file}", file=sys.stderr)
        sys.exit(1)
    
    if not args.script_file.exists():
        print(f"Error: Script file not found: {args.script_file}", file=sys.stderr)
        sys.exit(1)
    
    print(f"\n{'#' * 60}")
    print(f"# SCRIPT-SUBTITLE MERGER PIPELINE")
    print(f"# Movie: {args.title}")
    print(f"{'#' * 60}\n")
    
    # Step 1: Fuzzy matching merge
    v1_path = run_merge_step(
        srt_path=args.srt_file,
        script_path=args.script_file,
        movie_title=args.title,
        match_threshold=args.threshold,
        verbose=args.verbose
    )
    
    # Step 2: LLM validation (optional)
    if args.skip_llm:
        print("\n" + "=" * 60)
        print("STEP 2: Skipped (--skip-llm flag)")
        print("=" * 60)
        v2_path = None
    else:
        v2_path = run_llm_validation_step(
            v1_json_path=v1_path,
            srt_path=args.srt_file,
            script_path=args.script_file,
            movie_title=args.title,
            model=args.model,
            batch_size=args.batch_size,
            verbose=args.verbose
        )
    
    # Summary
    print("\n" + "#" * 60)
    print("# PIPELINE COMPLETE")
    print("#" * 60)
    print(f"\nOutputs:")
    print(f"  V1 (fuzzy match):     {v1_path}")
    if v2_path:
        print(f"  V2 (LLM validated):   {v2_path}")
    print()


if __name__ == "__main__":
    main()
