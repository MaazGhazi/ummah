#!/usr/bin/env python3
"""
Movie Scene Replacer - Replace intimate/inappropriate scenes with family-friendly alternatives.

This tool:
1. Analyzes a movie using OpenAI GPT-4o vision to detect intimate/sexual scenes
2. Extracts boundary frames (first frame before, last frame after each scene)
3. Uses fal.ai Veo 3.1 to generate replacement clips (characters doing a fist bump)
4. Stitches the movie back together with replaced scenes

Usage:
    python replace_scenes.py movie.mp4 -o cleaned_movie.mp4
    python replace_scenes.py movie.mp4 --segments segments.json  # Use existing analysis
    python replace_scenes.py movie.mp4 --analyze-only  # Just detect, don't replace
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure FAL_KEY is set for fal_client
if os.environ.get("FAL_KEY"):
    os.environ["FAL_KEY"] = os.environ["FAL_KEY"]


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Replace intimate movie scenes with family-friendly alternatives using AI"
    )
    parser.add_argument(
        "video",
        type=str,
        help="Path to the input video file (MP4)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output video path (default: {input}_clean.mp4)"
    )
    parser.add_argument(
        "--segments",
        type=str,
        default=None,
        help="Path to existing segments.json (skip analysis phase)"
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only analyze the video, don't generate replacements"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.4,
        help="Detection threshold (0.0-1.0, default: 0.4 for moderate+ content)"
    )
    parser.add_argument(
        "--work-dir",
        type=str,
        default=None,
        help="Working directory for intermediate files (default: ./scene_replacer_work)"
    )
    parser.add_argument(
        "--resolution",
        type=str,
        choices=["720p", "1080p", "4k"],
        default="720p",
        help="Resolution for replacement clips (default: 720p)"
    )
    parser.add_argument(
        "--max-scenes",
        type=int,
        default=None,
        help="Maximum number of scenes to replace (for testing)"
    )
    parser.add_argument(
        "--keep-original-audio",
        action="store_true",
        default=True,
        help="Keep original audio during replaced scenes (default: True)"
    )
    parser.add_argument(
        "--no-original-audio",
        action="store_true",
        help="Don't keep original audio during replaced scenes"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed progress"
    )
    parser.add_argument(
        "--refine-timing",
        action="store_true",
        help="Use second-pass analysis for more precise scene boundaries"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Use stricter detection (catches more subtle content)"
    )
    
    return parser.parse_args()


def analyze_video(video_path: str, args) -> list[dict]:
    """Run content analysis on the video."""
    from src.core.analysis import analyze_movie
    
    print("\n" + "=" * 60)
    print("📹 PHASE 1: CONTENT ANALYSIS")
    print("=" * 60)
    
    # Run analysis
    result = analyze_movie(
        video_path,
        output_path=str(Path(args.work_dir) / "segments.json"),
        threshold=args.threshold,
        verbose=args.verbose,
        refine_timing=args.refine_timing,
        strict=args.strict,
        high_accuracy=True,  # Better accuracy for scene boundary detection
        quiet=False,
        save_output=True,
    )
    
    segments = result.get("segments", [])
    stats = result.get("stats", {})
    
    print(f"\n📊 Analysis complete:")
    print(f"   Scenes analyzed: {stats.get('total_scenes', 0)}")
    print(f"   Flagged segments: {len(segments)}")
    print(f"   API cost: ${stats.get('cost', 0):.4f}")
    
    return segments


def load_segments(segments_path: str) -> list[dict]:
    """Load pre-analyzed segments from JSON file."""
    print(f"\n📂 Loading existing analysis from {segments_path}")
    
    with open(segments_path) as f:
        segments = json.load(f)
    
    print(f"   Found {len(segments)} flagged segments")
    return segments


def generate_replacements(video_path: str, segments: list[dict], args) -> list[dict]:
    """Generate replacement clips for all flagged segments."""
    from src.core.scene_replacer import process_all_replacements
    
    print("\n" + "=" * 60)
    print("🎬 PHASE 2: GENERATING REPLACEMENTS")
    print("=" * 60)
    
    replacements_dir = Path(args.work_dir) / "replacements"
    
    replacements = process_all_replacements(
        video_path=video_path,
        segments=segments,
        output_dir=str(replacements_dir),
        resolution=args.resolution,
        max_scenes=args.max_scenes,
    )
    
    successful = [r for r in replacements if r.get("replacement_path")]
    failed = [r for r in replacements if r.get("error")]
    
    print(f"\n📊 Replacement generation complete:")
    print(f"   Successful: {len(successful)}")
    print(f"   Failed: {len(failed)}")
    
    if failed:
        print("   Failed scenes:")
        for r in failed:
            print(f"     - Scene {r.get('scene_index', '?') + 1}: {r.get('error', 'unknown')[:50]}")
    
    # Save replacements metadata
    replacements_json = Path(args.work_dir) / "replacements.json"
    with open(replacements_json, "w") as f:
        json.dump(replacements, f, indent=2)
    
    return replacements


def stitch_video(video_path: str, replacements: list[dict], output_path: str, args) -> dict:
    """Stitch the final video with replacements."""
    from src.core.video_stitcher import stitch_movie_with_replacements
    
    print("\n" + "=" * 60)
    print("📼 PHASE 3: STITCHING FINAL VIDEO")
    print("=" * 60)
    
    # Filter to only successful replacements
    successful_replacements = [r for r in replacements if r.get("replacement_path")]
    
    if not successful_replacements:
        print("   ⚠️  No successful replacements to stitch")
        return {"success": False, "error": "No replacements available"}
    
    keep_audio = args.keep_original_audio and not args.no_original_audio
    
    result = stitch_movie_with_replacements(
        original_video=video_path,
        replacements=successful_replacements,
        output_path=output_path,
        work_dir=str(Path(args.work_dir) / "stitch_work"),
        keep_original_audio=keep_audio,
    )
    
    return result


def main():
    """Main entry point."""
    args = parse_args()
    
    # Validate input
    video_path = Path(args.video)
    if not video_path.exists():
        print(f"❌ Error: Video file not found: {video_path}")
        sys.exit(1)
    
    # Set up working directory
    if args.work_dir:
        work_dir = Path(args.work_dir)
    else:
        work_dir = Path.cwd() / "scene_replacer_work"
    
    work_dir.mkdir(parents=True, exist_ok=True)
    args.work_dir = str(work_dir)
    
    # Set output path
    if args.output:
        output_path = args.output
    else:
        output_path = str(video_path.parent / f"{video_path.stem}_clean{video_path.suffix}")
    
    print("=" * 60)
    print("🎬 MOVIE SCENE REPLACER")
    print("=" * 60)
    print(f"Input:  {video_path}")
    print(f"Output: {output_path}")
    print(f"Work:   {work_dir}")
    print(f"Threshold: {args.threshold}")
    
    # Check API keys
    if not os.environ.get("OPENAI_API_KEY"):
        print("\n❌ Error: OPENAI_API_KEY not set")
        print("   Set it in your environment or .env file")
        sys.exit(1)
    
    if not args.analyze_only and not os.environ.get("FAL_KEY"):
        print("\n❌ Error: FAL_KEY not set (required for video generation)")
        print("   Set it in your environment or .env file")
        print("   Get your key at: https://fal.ai/dashboard/keys")
        sys.exit(1)
    
    # Phase 1: Analyze or load segments
    if args.segments:
        segments = load_segments(args.segments)
    else:
        segments = analyze_video(str(video_path), args)
    
    if not segments:
        print("\n✅ No intimate scenes detected - video is already family-friendly!")
        sys.exit(0)
    
    if args.analyze_only:
        print(f"\n✅ Analysis complete. Segments saved to: {work_dir / 'segments.json'}")
        print("   Run again without --analyze-only to generate replacements")
        sys.exit(0)
    
    # Phase 2: Generate replacements
    replacements = generate_replacements(str(video_path), segments, args)
    
    # Phase 3: Stitch final video
    result = stitch_video(str(video_path), replacements, output_path, args)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 FINAL SUMMARY")
    print("=" * 60)
    
    if result.get("success"):
        print(f"✅ Successfully created family-friendly version!")
        print(f"   Output: {output_path}")
        print(f"   Scenes replaced: {result.get('replacements_applied', 0)}")
        print(f"\n   Working files saved in: {work_dir}")
        print("   (Delete this folder to clean up)")
    else:
        print(f"❌ Failed to create output video")
        print(f"   Error: {result.get('error', 'Unknown')}")
        print(f"   Check working directory for partial results: {work_dir}")
        sys.exit(1)


if __name__ == "__main__":
    main()
