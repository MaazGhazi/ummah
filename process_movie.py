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


def analyze_movie(
    video: str | Path,
    *,
    output_path: str | Path = "segments.json",
    threshold: float = 0.3,
    frames_per_scene: int = 10,
    min_scene_length: float = 1.0,
    max_workers: int = 4,
    frame_width: int = 640,
    verbose: bool = False,
    refine_timing: bool = False,
    strict: bool = False,
    high_accuracy: bool = False,
    sample_rate: float | None = None,
    quiet: bool = False,
    save_output: bool = True,
    log_usage_flag: bool = True,
    client: OpenAI | None = None,
) -> dict:
    """
    Analyze a movie file for haram content, optionally writing segment metadata and returning stats.
    This is the core workflow that both the CLI and any HTTP endpoint should call.
    """

    def _log(*args, **kwargs):
        if quiet:
            return
        print(*args, **kwargs)

    video_path = Path(video)
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if strict:
        threshold = 0.2
        _log("🔒 Strict mode enabled (threshold: 0.2)")

    if client is None:
        client = OpenAI(api_key=get_openai_key())

    scenes = detect_scenes(str(video_path), min_scene_length)
    if not scenes:
        _log("No scenes detected in video")
        return {
            "segments": [],
            "stats": {
                "total_scenes": 0,
                "total_frames": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "haram_segments": 0,
                "threshold": threshold,
            },
        }

    use_adaptive = high_accuracy
    if sample_rate:
        _log(f"📊 Using fixed sample rate: {sample_rate} fps")
    elif use_adaptive:
        _log("🎯 High accuracy mode: adaptive frame extraction (2-4 fps based on scene length)")

    _log(f"\n🎬 Analyzing {len(scenes)} scenes for halal compliance...")

    scene_args = []
    for i, (start, end) in enumerate(scenes):
        if sample_rate:
            duration = end - start
            num_frames = max(4, int(duration * sample_rate))
        else:
            num_frames = frames_per_scene
        scene_args.append(
            (i, start, end, str(video_path), client, num_frames, frame_width, use_adaptive)
        )

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_scene, arg): arg[0] for arg in scene_args
        }

        with tqdm(total=len(scenes), desc="Scanning scenes", disable=quiet) as pbar:
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                pbar.update(1)

    results.sort(key=lambda x: x[0])

    segments = []
    all_scores = []
    total_tokens_in = total_tokens_out = total_frames = 0
    flagged_for_refinement = []

    for scene_index, start_time, end_time, analysis in results:
        total_frames += analysis.get("frames_analyzed", 0)
        score = analysis.get("haram_score", max(analysis.get("nudity", 0), analysis.get("sexual_activity", 0)))
        total_tokens_in += analysis.get("tokens_in", 0)
        total_tokens_out += analysis.get("tokens_out", 0)

        issues = analysis.get("issues_detected", [])
        issues_str = ", ".join(issues) if issues else "none"

        all_scores.append({
            "scene": scene_index + 1,
            "time": f"{format_timestamp(start_time)} - {format_timestamp(end_time)}",
            "haram_score": score,
            "severity": analysis.get("severity", "halal"),
            "description": analysis.get("scene_description", analysis.get("reason", "")),
            "issues": issues_str,
            "replacement": analysis.get("replacement_suggestion", "none"),
        })

        if score >= threshold:
            seg = {
                "start": format_timestamp(start_time),
                "end": format_timestamp(end_time),
                "start_seconds": start_time,
                "end_seconds": end_time,
                "severity": analysis.get("severity", "mild"),
                "description": analysis.get("scene_description", analysis.get("reason", "")),
                "issues": issues,
                "replacement": analysis.get("replacement_suggestion", "skip"),
                "haram_score": round(score, 2),
            }
            segments.append(seg)
            if refine_timing:
                flagged_for_refinement.append((scene_index, start_time, end_time))

    if refine_timing and flagged_for_refinement:
        _log(f"\n🔍 Refining timing for {len(flagged_for_refinement)} flagged segments...")
        for scene_idx, start, end in tqdm(flagged_for_refinement, desc="Refining timing", disable=quiet):
            refined_start, refined_end, tokens_in, tokens_out = refine_scene_timing(
                client, str(video_path), start, end, scene_idx, frame_width
            )
            total_tokens_in += tokens_in
            total_tokens_out += tokens_out

            for seg in segments:
                if seg["start_seconds"] == start and seg["end_seconds"] == end:
                    seg.update({
                        "start": format_timestamp(refined_start),
                        "end": format_timestamp(refined_end),
                        "start_seconds": refined_start,
                        "end_seconds": refined_end,
                        "timing_refined": True,
                    })
                    break

    merged_segments = merge_adjacent_segments(segments)
    output_segments = []
    for seg in merged_segments:
        output_segments.append({
            "start": seg["start"],
            "end": seg["end"],
            "severity": seg["severity"],
            "description": seg.get("description", seg.get("reason", "")),
            "issues": seg.get("issues", []),
            "replacement": seg.get("replacement", "skip"),
            "haram_score": seg.get("haram_score", seg.get("confidence", 0.0)),
        })

    if save_output:
        output_path_obj = Path(output_path)
        with open(output_path_obj, "w") as f:
            json.dump(output_segments, f, indent=2)
    else:
        output_path_obj = Path(output_path)

    if verbose and not quiet:
        _log("\n" + "=" * 100)
        _log("ALL SCENE ANALYSIS (verbose mode)")
        _log("=" * 100)
        for s in all_scores:
            flag = "⚠️  HARAM" if s["haram_score"] >= threshold else "✅ HALAL"
            severity_display = s["severity"].upper()
            _log(f"\nScene {s['scene']:2d} | {s['time']} | Score: {s['haram_score']:.2f} | {severity_display} | {flag}")
            _log(f"  Issues: {s['issues']}")
            _log(f"  Description: {s['description'][:120]}...")
            if s["haram_score"] >= threshold:
                _log(f"  Suggested action: {s['replacement'].upper()}")
        _log("=" * 100)

    total_cost = calculate_cost(total_tokens_in, total_tokens_out)

    if log_usage_flag:
        log_usage(
            video_name=video_path.name,
            scenes_count=len(scenes),
            tokens_in=total_tokens_in,
            tokens_out=total_tokens_out,
            segments_found=len(output_segments),
        )

    if not quiet:
        _log(f"\n📊 Results:")
        _log(f"  Total scenes analyzed: {len(scenes)}")
        _log(f"  Total frames analyzed: {total_frames}")
        _log(f"  Haram segments found: {len(output_segments)}")
        _log(f"  Threshold used: {threshold}")
        _log(f"  Output written to: {output_path_obj}")
        _log(f"\n💰 API Usage (this run):")
        _log(f"  Input tokens:  {total_tokens_in:,}")
        _log(f"  Output tokens: {total_tokens_out:,}")
        _log(f"  Cost: ${total_cost:.4f}")
        _log(f"\n  (Usage logged to usage_log.json - run with --usage to see totals)")

        if output_segments:
            _log("\n⚠️  Flagged segments to skip/replace:")
            _log("-" * 80)
            for seg in output_segments:
                severity_emoji = {"mild": "🟡", "moderate": "🟠", "severe": "🔴", "questionable": "🟡"}.get(
                    seg["severity"], "⚪"
                )
                issues_str = ", ".join(seg.get("issues", [])) if seg.get("issues") else "unspecified"
                _log(f"\n  {severity_emoji} {seg['start']} → {seg['end']} [{seg['severity'].upper()}]")
                _log(f"     Issues: {issues_str}")
                _log(f"     {seg['description'][:150]}")
                _log(f"     Action: {seg['replacement'].upper()} (score: {seg['haram_score']})")
            _log("-" * 80)
        else:
            _log("\n✅ No haram content detected - video appears halal-friendly!")

    return {
        "segments": output_segments,
        "stats": {
            "total_scenes": len(scenes),
            "total_frames": total_frames,
            "tokens_in": total_tokens_in,
            "tokens_out": total_tokens_out,
            "haram_segments": len(output_segments),
            "threshold": threshold,
            "cost": total_cost,
            "output_path": str(output_path_obj),
        },
    }


def main():
    """CLI entrypoint."""
    args = parse_args()
    if args.usage:
        print_usage_summary()
        return

    if not args.video:
        print("Error: Please provide a video file path")
        print("Usage: python process_movie.py movie.mp4")
        sys.exit(1)

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)

    try:
        analyze_movie(
            video_path,
            output_path=args.output,
            threshold=args.threshold,
            frames_per_scene=args.frames_per_scene,
            min_scene_length=args.min_scene_length,
            max_workers=args.max_workers,
            frame_width=args.frame_width,
            verbose=args.verbose,
            refine_timing=args.refine_timing,
            strict=args.strict,
            high_accuracy=args.high_accuracy,
            sample_rate=args.sample_rate,
            quiet=False,
        )
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
