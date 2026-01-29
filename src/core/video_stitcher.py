"""
Video stitching module for reassembling movies with replaced scenes.

Uses FFmpeg to cut, join, and combine video segments.
"""

import subprocess
import json
import shutil
from pathlib import Path
from typing import Optional

import cv2


def get_video_info(video_path: str) -> dict:
    """Get video metadata using FFprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", video_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        video_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
            {}
        )
        audio_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "audio"),
            {}
        )
        
        return {
            "duration": float(data.get("format", {}).get("duration", 0)),
            "width": video_stream.get("width", 0),
            "height": video_stream.get("height", 0),
            "fps": eval(video_stream.get("r_frame_rate", "30/1")),
            "video_codec": video_stream.get("codec_name", "h264"),
            "audio_codec": audio_stream.get("codec_name", "aac"),
            "has_audio": bool(audio_stream),
        }
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError) as e:
        # Fallback to OpenCV for basic info
        cap = cv2.VideoCapture(video_path)
        info = {
            "duration": cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(1, cap.get(cv2.CAP_PROP_FPS)),
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": cap.get(cv2.CAP_PROP_FPS),
            "video_codec": "h264",
            "audio_codec": "aac",
            "has_audio": True,
        }
        cap.release()
        return info


def extract_segment(
    input_path: str,
    output_path: str,
    start_time: float,
    end_time: float,
    reencode: bool = False
) -> bool:
    """
    Extract a segment from a video using FFmpeg.
    
    Args:
        input_path: Source video path
        output_path: Output segment path
        start_time: Start time in seconds
        end_time: End time in seconds
        reencode: Whether to re-encode (slower but more accurate cuts)
    
    Returns:
        True if successful
    """
    duration = end_time - start_time
    
    if reencode:
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-ss", str(start_time), "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            output_path
        ]
    else:
        # Fast copy without re-encoding (may have slight timing issues)
        cmd = [
            "ffmpeg", "-y", "-ss", str(start_time),
            "-i", input_path, "-t", str(duration),
            "-c", "copy", "-avoid_negative_ts", "make_zero",
            output_path
        ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Warning: FFmpeg error extracting segment: {e.stderr.decode()[:200]}")
        return False


def scale_video_to_match(
    input_path: str,
    output_path: str,
    target_width: int,
    target_height: int,
    target_fps: float
) -> bool:
    """
    Scale and adjust a video to match target dimensions and framerate.
    
    Args:
        input_path: Source video path
        output_path: Output video path
        target_width: Target width
        target_height: Target height
        target_fps: Target framerate
    
    Returns:
        True if successful
    """
    # Build filter for scaling and padding to exact dimensions
    filter_str = (
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black,"
        f"fps={target_fps}"
    )
    
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", filter_str,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        output_path
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Warning: FFmpeg scaling error: {e.stderr.decode()[:200]}")
        return False


def adjust_replacement_duration(
    input_path: str,
    output_path: str,
    target_duration: float
) -> bool:
    """
    Adjust a replacement video to match the exact target duration.
    
    Strategy:
    - If replacement is longer: trim to target duration
    - If replacement is slightly shorter (within 20%): slow down video slightly
    - If replacement is much shorter: just use it as-is (scene was already cut to fit)
    """
    # Get current duration
    info = get_video_info(input_path)
    current_duration = info["duration"]
    
    diff = abs(current_duration - target_duration)
    
    # If very close, just copy
    if diff < 0.2:
        shutil.copy(input_path, output_path)
        return True
    
    if current_duration > target_duration:
        # Replacement is LONGER than needed - trim it
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-t", str(target_duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            output_path
        ]
    elif current_duration < target_duration:
        # Replacement is SHORTER than needed
        speed_factor = current_duration / target_duration
        
        if speed_factor >= 0.8:
            # Within 20% - slow down slightly (barely noticeable)
            video_filter = f"setpts={1/speed_factor}*PTS"
            
            # Check if input has audio
            if info.get("has_audio", False):
                # Adjust audio tempo too
                audio_filter = f"atempo={speed_factor}"
                cmd = [
                    "ffmpeg", "-y", "-i", input_path,
                    "-filter_complex", f"[0:v]{video_filter}[v];[0:a]{audio_filter}[a]",
                    "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-c:a", "aac", "-b:a", "192k",
                    output_path
                ]
            else:
                # No audio, just adjust video
                cmd = [
                    "ffmpeg", "-y", "-i", input_path,
                    "-vf", video_filter,
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-an",
                    output_path
                ]
        else:
            # More than 20% shorter - scene was cut to fit Veo's max duration
            # Just use the replacement as-is (the cut points were already adjusted)
            shutil.copy(input_path, output_path)
            return True
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Warning: Duration adjustment failed: {e.stderr.decode()[:200]}")
        # Fallback: just copy the file
        shutil.copy(input_path, output_path)
        return True  # Return True since we have a usable file


def concatenate_segments(
    segment_paths: list[str],
    output_path: str,
    work_dir: Optional[str] = None
) -> bool:
    """
    Concatenate multiple video segments into a single video.
    
    Args:
        segment_paths: List of video file paths to concatenate
        output_path: Output video path
        work_dir: Working directory for temp files
    
    Returns:
        True if successful
    """
    if not segment_paths:
        return False
    
    if len(segment_paths) == 1:
        shutil.copy(segment_paths[0], output_path)
        return True
    
    work_path = Path(work_dir) if work_dir else Path(output_path).parent
    concat_list = work_path / "concat_list.txt"
    
    # Write concat file
    with open(concat_list, "w") as f:
        for path in segment_paths:
            # Escape single quotes in paths
            escaped_path = str(Path(path).absolute()).replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")
    
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        output_path
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        concat_list.unlink()  # Clean up
        return True
    except subprocess.CalledProcessError as e:
        print(f"Warning: Concatenation failed: {e.stderr.decode()[:200]}")
        # Try re-encoding approach
        return _concatenate_with_reencode(segment_paths, output_path, concat_list)


def _concatenate_with_reencode(
    segment_paths: list[str],
    output_path: str,
    concat_list: Path
) -> bool:
    """Fallback concatenation with re-encoding for incompatible streams."""
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        output_path
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        concat_list.unlink()
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: Re-encode concatenation also failed: {e.stderr.decode()[:300]}")
        if concat_list.exists():
            concat_list.unlink()
        return False


def stitch_movie_with_replacements(
    original_video: str,
    replacements: list[dict],
    output_path: str,
    work_dir: Optional[str] = None,
    keep_original_audio: bool = True,
) -> dict:
    """
    Stitch together the original movie with replacement clips.
    
    Args:
        original_video: Path to original video
        replacements: List of dicts with:
            - replacement_start: Start time of section to replace
            - replacement_end: End time of section to replace
            - replacement_path: Path to replacement video clip
        output_path: Final output video path
        work_dir: Working directory for temp files
        keep_original_audio: Whether to extract and overlay original audio
    
    Returns:
        Dict with stitching results
    """
    print(f"\n🎬 Stitching movie with {len(replacements)} replacements...")
    
    original_path = Path(original_video)
    output_dir = Path(work_dir) if work_dir else original_path.parent / "stitch_work"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get original video info
    video_info = get_video_info(original_video)
    print(f"  📹 Original: {video_info['width']}x{video_info['height']} @ {video_info['fps']:.2f}fps")
    
    # Sort replacements by start time
    sorted_replacements = sorted(replacements, key=lambda x: x.get("replacement_start", 0))
    
    # Build list of segments to concatenate
    segments = []
    current_time = 0.0
    segment_idx = 0
    
    for rep in sorted_replacements:
        rep_start = rep.get("replacement_start", rep.get("original_start", 0))
        rep_end = rep.get("replacement_end", rep.get("original_end", 0))
        rep_path = rep.get("replacement_path")
        
        if not rep_path or not Path(rep_path).exists():
            print(f"  ⚠️  Skipping replacement (no file): {rep_start:.1f}s - {rep_end:.1f}s")
            continue
        
        # Extract segment before this replacement
        if current_time < rep_start:
            before_path = str(output_dir / f"segment_{segment_idx:03d}_original.mp4")
            print(f"  📎 Extracting original: {current_time:.1f}s - {rep_start:.1f}s")
            
            if extract_segment(original_video, before_path, current_time, rep_start, reencode=True):
                segments.append(before_path)
                segment_idx += 1
        
        # Process replacement clip
        cut_duration = rep_end - rep_start
        
        # Scale replacement to match original video dimensions and fps
        scaled_path = str(output_dir / f"segment_{segment_idx:03d}_replacement_scaled.mp4")
        print(f"  🔄 Processing replacement: {rep_start:.1f}s - {rep_end:.1f}s (cutting {cut_duration:.1f}s)")
        
        if scale_video_to_match(
            rep_path, scaled_path,
            video_info["width"], video_info["height"], video_info["fps"]
        ):
            # Get the actual replacement duration
            rep_info = get_video_info(scaled_path)
            rep_duration = rep_info.get("duration", 0)
            
            # DON'T stretch the replacement - use it as-is
            # If the replacement is shorter than the cut, that's fine
            # The video will just be shorter overall (which is what we want - remove ALL the bad content)
            adjusted_path = scaled_path  # Use the scaled clip directly
            
            if rep_duration < cut_duration:
                print(f"     📉 Replacement is {rep_duration:.1f}s (video will be {cut_duration - rep_duration:.1f}s shorter)")
            
            # Optionally extract and overlay original audio
            # Use the REPLACEMENT duration for audio, not the cut duration
            if keep_original_audio:
                with_audio_path = str(output_dir / f"segment_{segment_idx:03d}_with_audio.mp4")
                # Get audio from the START of the replacement window (rep_start) for the replacement's duration
                if _overlay_original_audio(
                    adjusted_path, original_video, rep_start, rep_start + rep_duration, with_audio_path
                ):
                    segments.append(with_audio_path)
                else:
                    segments.append(adjusted_path)
            else:
                segments.append(adjusted_path)
            
            segment_idx += 1
        
        current_time = rep_end
    
    # Extract remaining segment after last replacement
    if current_time < video_info["duration"]:
        after_path = str(output_dir / f"segment_{segment_idx:03d}_original.mp4")
        print(f"  📎 Extracting original: {current_time:.1f}s - {video_info['duration']:.1f}s")
        
        if extract_segment(original_video, after_path, current_time, video_info["duration"], reencode=True):
            segments.append(after_path)
    
    # Concatenate all segments
    print(f"\n  📼 Concatenating {len(segments)} segments...")
    success = concatenate_segments(segments, output_path, str(output_dir))
    
    result = {
        "success": success,
        "output_path": output_path if success else None,
        "segments_count": len(segments),
        "replacements_applied": len([r for r in replacements if r.get("replacement_path")]),
        "work_dir": str(output_dir),
    }
    
    if success:
        print(f"\n  ✅ Movie stitched successfully: {output_path}")
        final_info = get_video_info(output_path)
        print(f"  📹 Final: {final_info['duration']:.1f}s")
    else:
        print(f"\n  ❌ Stitching failed")
    
    return result


def _overlay_original_audio(
    video_path: str,
    original_video: str,
    start_time: float,
    end_time: float,
    output_path: str
) -> bool:
    """
    Replace the audio in a video with audio from the original at the same timestamp.
    """
    duration = end_time - start_time
    
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-ss", str(start_time), "-t", str(duration), "-i", original_video,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_path
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError:
        # If audio extraction fails, just copy video without audio change
        return False


def cleanup_work_dir(work_dir: str, keep_final: bool = True) -> None:
    """Clean up temporary working directory."""
    work_path = Path(work_dir)
    if work_path.exists():
        for f in work_path.iterdir():
            if f.is_file() and (not keep_final or "segment_" in f.name):
                f.unlink()
