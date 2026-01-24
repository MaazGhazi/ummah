#!/usr/bin/env python3
"""
Halal Movie Scene Filter
Detects content that violates Islamic viewing guidelines using GPT-4o vision analysis.
Helps Muslims identify scenes to skip or replace to make movies family-appropriate.

Usage:
    python process_movie.py movie.mp4 -o segments.json --threshold 0.3
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI
from tqdm import tqdm

from src.config import get_openai_key
from src.scene_detector import detect_scenes
from src.vision_analyzer import process_scene, refine_scene_timing
from src.aggregator import merge_adjacent_segments
from src.utils import format_timestamp
from src.usage_tracker import log_usage, calculate_cost, print_usage_summary


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Detect haram content in movies for halal viewing using GPT-4o vision"
    )
    parser.add_argument(
        "video",
        type=str,
        nargs="?",  # Optional when using --usage
        help="Path to the video file (MP4)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="segments.json",
        help="Output JSON file path (default: segments.json)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.3,
        help="Haram score threshold for flagging (0.0-1.0, default: 0.3 catches romantic content)"
    )
    parser.add_argument(
        "--frames-per-scene",
        type=int,
        default=10,
        help="Number of frames to extract per scene (default: 10)"
    )
    parser.add_argument(
        "--min-scene-length",
        type=float,
        default=1.0,
        help="Minimum scene length in seconds (default: 1.0 - catches quick moments)"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum parallel API requests (default: 4)"
    )
    parser.add_argument(
        "--frame-width",
        type=int,
        default=640,
        help="Resize frame width for API (default: 640)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show scores for ALL scenes (not just flagged ones)"
    )
    parser.add_argument(
        "--usage",
        action="store_true",
        help="Show cumulative API usage from all runs"
    )
    parser.add_argument(
        "--refine-timing",
        action="store_true",
        help="Perform second-pass analysis to refine exact timing of flagged segments (uses more API calls)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Use stricter detection (lower threshold to 0.2)"
    )
    parser.add_argument(
        "--high-accuracy",
        action="store_true",
        help="Use adaptive frame extraction for higher accuracy (more frames for short scenes, uses more API tokens)"
    )
    parser.add_argument(
        "--sample-rate",
        type=float,
        default=None,
        help="Frames per second to sample (e.g., 3.0 for 3fps). Overrides --frames-per-scene."
    )
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Show usage summary if requested
    if args.usage:
        print_usage_summary()
        return
    
    # Validate input file
    if not args.video:
        print("Error: Please provide a video file path")
        print("Usage: python process_movie.py movie.mp4")
        sys.exit(1)
    
    video_path = Path(args.video)
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)
    
    # Get OpenAI API key (from .env or environment)
    try:
        api_key = get_openai_key()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Apply strict mode if requested
    threshold = args.threshold
    if args.strict:
        threshold = 0.2
        print("🔒 Strict mode enabled (threshold: 0.2)")
    
    client = OpenAI(api_key=api_key)
    
    # Step 1: Detect scenes
    scenes = detect_scenes(str(video_path), args.min_scene_length)
    
    if not scenes:
        print("No scenes detected in video")
        sys.exit(1)
    
    # Determine frame extraction settings
    use_adaptive = args.high_accuracy
    if args.sample_rate:
        print(f"📊 Using fixed sample rate: {args.sample_rate} fps")
    elif use_adaptive:
        print(f"🎯 High accuracy mode: adaptive frame extraction (2-4 fps based on scene length)")
    
    print(f"\n🎬 Analyzing {len(scenes)} scenes for halal compliance...")
    
    # Step 2: Process scenes (with parallel API calls)
    results = []
    
    # Prepare arguments for parallel processing
    scene_args = []
    for i, (start, end) in enumerate(scenes):
        # Calculate frames based on mode
        if args.sample_rate:
            # Fixed sample rate mode
            duration = end - start
            num_frames = max(4, int(duration * args.sample_rate))
        else:
            num_frames = args.frames_per_scene
        
        scene_args.append(
            (i, start, end, str(video_path), client, num_frames, args.frame_width, use_adaptive)
        )
    
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = {
            executor.submit(process_scene, arg): arg[0] 
            for arg in scene_args
        }
        
        with tqdm(total=len(scenes), desc="Scanning scenes") as pbar:
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                pbar.update(1)
    
    # Sort results by scene index
    results.sort(key=lambda x: x[0])
    
    # Step 3: Filter and build segments + track costs
    segments = []
    all_scores = []  # For verbose output
    total_tokens_in = 0
    total_tokens_out = 0
    total_frames = 0  # Track total frames analyzed
    flagged_for_refinement = []  # Scenes that need timing refinement
    
    for scene_index, start_time, end_time, analysis in results:
        # Track frames analyzed
        total_frames += analysis.get("frames_analyzed", 0)
        # Use haram_score as primary score
        score = analysis.get("haram_score", max(analysis.get("nudity", 0), analysis.get("sexual_activity", 0)))
        
        # Track token usage
        total_tokens_in += analysis.get("tokens_in", 0)
        total_tokens_out += analysis.get("tokens_out", 0)
        
        # Get issues as formatted string
        issues = analysis.get("issues_detected", [])
        issues_str = ", ".join(issues) if issues else "none"
        
        all_scores.append({
            "scene": scene_index + 1,
            "time": f"{format_timestamp(start_time)} - {format_timestamp(end_time)}",
            "haram_score": score,
            "severity": analysis.get("severity", "halal"),
            "description": analysis.get("scene_description", analysis.get("reason", "")),
            "issues": issues_str,
            "replacement": analysis.get("replacement_suggestion", "none")
        })
        
        if score >= threshold:
            segments.append({
                "start": format_timestamp(start_time),
                "end": format_timestamp(end_time),
                "start_seconds": start_time,
                "end_seconds": end_time,
                "severity": analysis.get("severity", "mild"),
                "description": analysis.get("scene_description", analysis.get("reason", "")),
                "issues": issues,
                "replacement": analysis.get("replacement_suggestion", "skip"),
                "haram_score": round(score, 2)
            })
            
            # Track for potential refinement
            if args.refine_timing:
                flagged_for_refinement.append((scene_index, start_time, end_time))
    
    # Step 3.5: Refine timing for flagged segments if requested
    if args.refine_timing and flagged_for_refinement:
        print(f"\n🔍 Refining timing for {len(flagged_for_refinement)} flagged segments...")
        
        for i, (scene_idx, start, end) in enumerate(tqdm(flagged_for_refinement, desc="Refining timing")):
            refined_start, refined_end, tokens_in, tokens_out = refine_scene_timing(
                client, str(video_path), start, end, scene_idx, args.frame_width
            )
            
            total_tokens_in += tokens_in
            total_tokens_out += tokens_out
            
            # Update the corresponding segment
            for seg in segments:
                if seg["start_seconds"] == start and seg["end_seconds"] == end:
                    seg["start"] = format_timestamp(refined_start)
                    seg["end"] = format_timestamp(refined_end)
                    seg["start_seconds"] = refined_start
                    seg["end_seconds"] = refined_end
                    seg["timing_refined"] = True
                    break
    
    # Step 4: Merge adjacent segments
    merged_segments = merge_adjacent_segments(segments)
    
    # Clean up internal fields before output
    output_segments = []
    for seg in merged_segments:
        output_seg = {
            "start": seg["start"],
            "end": seg["end"],
            "severity": seg["severity"],
            "description": seg.get("description", seg.get("reason", "")),
            "issues": seg.get("issues", []),
            "replacement": seg.get("replacement", "skip"),
            "haram_score": seg.get("haram_score", seg.get("confidence", 0.0))
        }
        output_segments.append(output_seg)
    
    # Step 5: Write output
    output_path = Path(args.output)
    with open(output_path, "w") as f:
        json.dump(output_segments, f, indent=2)
    
    # Show verbose output if requested
    if args.verbose:
        print("\n" + "="*100)
        print("ALL SCENE ANALYSIS (verbose mode)")
        print("="*100)
        for s in all_scores:
            flag = "⚠️  HARAM" if s["haram_score"] >= threshold else "✅ HALAL"
            severity_display = s["severity"].upper()
            print(f"\nScene {s['scene']:2d} | {s['time']} | Score: {s['haram_score']:.2f} | {severity_display} | {flag}")
            print(f"  Issues: {s['issues']}")
            print(f"  Description: {s['description'][:120]}...")
            if s["haram_score"] >= threshold:
                print(f"  Suggested action: {s['replacement'].upper()}")
        print("="*100)
    
    # Calculate and log cost
    total_cost = calculate_cost(total_tokens_in, total_tokens_out)
    
    # Log usage to persistent file
    log_usage(
        video_name=video_path.name,
        scenes_count=len(scenes),
        tokens_in=total_tokens_in,
        tokens_out=total_tokens_out,
        segments_found=len(output_segments)
    )
    
    print(f"\n📊 Results:")
    print(f"  Total scenes analyzed: {len(scenes)}")
    print(f"  Total frames analyzed: {total_frames}")
    print(f"  Haram segments found: {len(output_segments)}")
    print(f"  Threshold used: {threshold}")
    print(f"  Output written to: {output_path}")
    print(f"\n💰 API Usage (this run):")
    print(f"  Input tokens:  {total_tokens_in:,}")
    print(f"  Output tokens: {total_tokens_out:,}")
    print(f"  Cost: ${total_cost:.4f}")
    print(f"\n  (Usage logged to usage_log.json - run with --usage to see totals)")
    
    if output_segments:
        print("\n⚠️  Flagged segments to skip/replace:")
        print("-" * 80)
        for seg in output_segments:
            severity_emoji = {"mild": "🟡", "moderate": "🟠", "severe": "🔴", "questionable": "🟡"}.get(seg["severity"], "⚪")
            issues_str = ", ".join(seg.get("issues", [])) if seg.get("issues") else "unspecified"
            print(f"\n  {severity_emoji} {seg['start']} → {seg['end']} [{seg['severity'].upper()}]")
            print(f"     Issues: {issues_str}")
            print(f"     {seg['description'][:150]}")
            print(f"     Action: {seg['replacement'].upper()} (score: {seg['haram_score']})")
        print("-" * 80)
    else:
        print("\n✅ No haram content detected - video appears halal-friendly!")


if __name__ == "__main__":
    main()
