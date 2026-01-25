"""
Scene replacement using fal.ai Veo 3.1 first-last-frame-to-video model.

Generates replacement clips for flagged scenes using boundary frames.
"""

import os
import base64
import time
from io import BytesIO
from pathlib import Path

import cv2
import fal_client
from PIL import Image

from .config import get_fal_key


def extract_frames_at_times(
    video_path: str,
    first_time: float,
    last_time: float,
    target_width: int = 1280,
) -> tuple[str, str]:
    """
    Extract frames at exact timestamps.
    
    Args:
        video_path: Path to the video file
        first_time: Time for first frame (seconds)
        last_time: Time for last frame (seconds)
        target_width: Width to resize frames to
    
    Returns:
        Tuple of (first_frame_b64, last_frame_b64) as base64-encoded JPEGs
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    if fps <= 0:
        cap.release()
        raise ValueError(f"Could not read video FPS from {video_path}")
    
    frames_b64 = []
    
    for ts in [first_time, last_time]:
        frame_num = int(ts * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        
        if not ret:
            cap.release()
            raise ValueError(f"Could not read frame at {ts}s from video")
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        
        # Resize maintaining aspect ratio
        aspect = img.height / img.width
        new_width = target_width
        new_height = int(target_width * aspect)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Encode to base64 JPEG
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=95)
        b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
        frames_b64.append(b64_data)
    
    cap.release()
    return frames_b64[0], frames_b64[1]


def extract_boundary_frames(
    video_path: str,
    start_time: float,
    end_time: float,
    target_width: int = 1280,
    buffer_seconds: float = 1.5
) -> tuple[str, str, float, float]:
    """
    Extract the first frame BEFORE and last frame AFTER an intimate scene.
    
    The buffer ensures we get frames where the intimate content is NOT visible,
    so the AI can generate a clean transition between them.
    
    Args:
        video_path: Path to the video file
        start_time: Start time of the flagged segment (seconds)
        end_time: End time of the flagged segment (seconds)
        target_width: Width to resize frames to
        buffer_seconds: How far before/after the scene to grab frames (default 1.5s)
    
    Returns:
        Tuple of (first_frame_b64, last_frame_b64, actual_start, actual_end)
        Returns base64-encoded JPEG images
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    
    if fps <= 0:
        cap.release()
        raise ValueError(f"Could not read video FPS from {video_path}")
    
    # Get frame WELL BEFORE the scene starts (before kissing begins)
    # This frame should show the characters in a neutral state
    first_time = max(0, start_time - buffer_seconds)
    first_frame_num = int(first_time * fps)
    
    # Get frame WELL AFTER the scene ends (after kissing is over)
    # This frame should show the characters back in a neutral state
    last_time = min(duration, end_time + buffer_seconds)
    last_frame_num = int(last_time * fps)
    
    frames_b64 = []
    
    for frame_num in [first_frame_num, last_frame_num]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        
        if not ret:
            cap.release()
            raise ValueError(f"Could not read frame {frame_num} from video")
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        
        # Resize maintaining aspect ratio
        aspect = img.height / img.width
        new_width = target_width
        new_height = int(target_width * aspect)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Encode to base64 JPEG
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=95)
        b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
        frames_b64.append(b64_data)
    
    cap.release()
    return frames_b64[0], frames_b64[1], first_time, last_time


def save_frame_to_file(b64_data: str, output_path: str) -> str:
    """Save a base64-encoded image to a file."""
    img_data = base64.b64decode(b64_data)
    with open(output_path, "wb") as f:
        f.write(img_data)
    return output_path


def upload_frame_to_fal(b64_data: str, filename: str = "frame.jpg") -> str:
    """
    Upload a base64-encoded image to fal.ai storage.
    
    Returns the public URL of the uploaded image.
    """
    # Decode base64 to bytes
    img_bytes = base64.b64decode(b64_data)
    
    # Upload to fal.ai storage
    url = fal_client.upload(img_bytes, content_type="image/jpeg")
    return url


def generate_replacement_clip(
    first_frame_b64: str,
    last_frame_b64: str,
    scene_duration: float,
    scene_description: str = "",
    issues: list[str] = None,
    output_path: str | None = None,
    resolution: str = "720p",
    generate_audio: bool = False,
) -> dict:
    """
    Generate a replacement clip using Veo 3.1 first-last-frame-to-video.
    
    Args:
        first_frame_b64: Base64-encoded first frame
        last_frame_b64: Base64-encoded last frame
        scene_duration: Duration of the original scene in seconds
        scene_description: Description of the original scene (for context)
        issues: List of detected issues (e.g., ["kissing", "revealing_clothing"])
        output_path: Optional path to save the generated video
        resolution: Video resolution ("720p", "1080p", "4k")
        generate_audio: Whether to generate audio
    
    Returns:
        Dict with video URL and metadata
    """
    # Upload frames to fal.ai storage to get public URLs
    print("  📤 Uploading boundary frames to fal.ai...")
    first_frame_url = upload_frame_to_fal(first_frame_b64, "first_frame.jpg")
    last_frame_url = upload_frame_to_fal(last_frame_b64, "last_frame.jpg")
    
    # Determine duration for Veo (4s, 6s, or 8s)
    if scene_duration <= 5:
        veo_duration = "4s"
    elif scene_duration <= 7:
        veo_duration = "6s"
    else:
        veo_duration = "8s"
    
    # Create the replacement prompt based on issue type
    prompt = _build_replacement_prompt(scene_description, issues)
    
    # Log what type of replacement we're generating
    if issues:
        print(f"  🏷️  Issues detected: {', '.join(issues)}")
    
    print(f"  🎬 Generating {veo_duration} replacement clip with Veo 3.1...")
    print(f"  📝 Prompt: {prompt[:100]}...")
    
    def on_queue_update(update):
        if isinstance(update, fal_client.InProgress):
            for log in update.logs:
                print(f"    ⏳ {log.get('message', log)}")
    
    result = fal_client.subscribe(
        "fal-ai/veo3.1/first-last-frame-to-video",
        arguments={
            "prompt": prompt,
            "first_frame_url": first_frame_url,
            "last_frame_url": last_frame_url,
            "duration": veo_duration,
            "resolution": resolution,
            "generate_audio": generate_audio,
            "negative_prompt": "kissing, intimate, sexual, nudity, embrace, romantic, touching, sensual",
            "auto_fix": True,  # Attempt to fix content policy issues automatically
        },
        with_logs=True,
        on_queue_update=on_queue_update,
    )
    
    video_url = result.get("video", {}).get("url", "")
    
    # Download video if output path specified
    if output_path and video_url:
        import requests
        print(f"  💾 Downloading replacement video...")
        response = requests.get(video_url)
        with open(output_path, "wb") as f:
            f.write(response.content)
        print(f"  ✅ Saved to {output_path}")
    
    return {
        "video_url": video_url,
        "duration": veo_duration,
        "prompt": prompt,
        "first_frame_url": first_frame_url,
        "last_frame_url": last_frame_url,
        "output_path": output_path,
    }


def _build_replacement_prompt(scene_description: str = "", issues: list[str] = None) -> str:
    """
    Build a prompt for generating a family-friendly replacement.
    
    Generates different replacements based on issue type:
    - Kissing/intimate: Characters do a fist bump instead
    - Revealing clothing/nudity: Characters are shown fully clothed
    - General: Neutral friendly interaction
    """
    issues = issues or []
    issues_lower = [i.lower() for i in issues]
    
    # Detect issue type and choose appropriate replacement
    is_clothing_issue = any(kw in issues_lower for kw in [
        "revealing_clothing", "partial_nudity", "nudity", "swimwear", 
        "bikini", "lingerie", "bathing", "underwear", "shirtless"
    ])
    
    is_kissing_issue = any(kw in issues_lower for kw in [
        "kissing", "intimate_touching", "embracing", "sexual_activity",
        "bed_scene", "romantic"
    ])
    
    # Build appropriate prompt based on issue type
    if is_clothing_issue:
        base_prompt = (
            "The people in the scene are wearing modest, fully covering clothing. "
            "They are dressed appropriately in casual everyday attire - "
            "long pants, shirts with sleeves, normal modest clothing. "
            "They interact naturally, having a friendly conversation or going about their day. "
            "Everyone is completely and modestly dressed. Family-friendly scene."
        )
    elif is_kissing_issue:
        base_prompt = (
            "Two people share a brief, friendly fist bump and smile at each other. "
            "They stand facing each other, extend their fists, bump them together gently, "
            "and share a warm, platonic smile. The interaction is casual, natural, and friendly. "
            "They appear happy and comfortable, like good friends or colleagues. "
            "Completely family-friendly moment with no romantic or intimate behavior."
        )
    else:
        # Generic replacement for other issues
        base_prompt = (
            "People in the scene interact in a friendly, appropriate manner. "
            "They are modestly dressed and behaving naturally. "
            "The scene is completely family-friendly with no inappropriate content. "
            "Everyone appears comfortable and the interaction is casual and platonic."
        )
    
    # Add context about the scene setting if available
    if scene_description:
        setting_hints = []
        keywords = ["ship", "deck", "night", "evening", "stars", "ocean", "sea", "boat",
                   "room", "bedroom", "living room", "office", "outdoor", "car", "restaurant", 
                   "beach", "pool", "day", "dark", "bright", "sunset", "water", "swimming"]
        desc_lower = scene_description.lower()
        for kw in keywords:
            if kw in desc_lower:
                setting_hints.append(kw)
        
        if setting_hints:
            setting_str = ", ".join(setting_hints[:3])
            base_prompt = f"Scene setting: {setting_str}. " + base_prompt
    
    return base_prompt


def replace_scene(
    video_path: str,
    start_time: float,
    end_time: float,
    scene_description: str = "",
    issues: list[str] = None,
    output_dir: str = "replacements",
    scene_index: int = 0,
    resolution: str = "720p",
    buffer_seconds: float = 1.5,
    max_veo_duration: float = 8.0,
) -> dict:
    """
    Full pipeline to replace a single scene.
    
    Args:
        video_path: Path to the source video
        start_time: Start of flagged segment (seconds)
        end_time: End of flagged segment (seconds)
        scene_description: Description of the scene content
        issues: List of detected issues (e.g., ["kissing", "revealing_clothing"])
        output_dir: Directory to save replacement clips
        scene_index: Index for naming output files
        resolution: Video resolution for replacement
        buffer_seconds: How far before/after to grab clean frames
        max_veo_duration: Maximum duration Veo can generate (8s)
    
    Returns:
        Dict with replacement metadata
    """
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    
    # Calculate the original scene duration
    original_duration = end_time - start_time
    
    # Calculate ideal replacement window (scene + buffers)
    ideal_start = max(0, start_time - buffer_seconds)
    ideal_end = end_time + buffer_seconds
    ideal_duration = ideal_end - ideal_start
    
    # If the scene is too long for Veo, cut it to fit within max_veo_duration
    # We prioritize keeping the START of the scene (where the issue begins)
    if ideal_duration > max_veo_duration:
        # Calculate how much we need to trim
        excess = ideal_duration - max_veo_duration
        
        # Reduce the end buffer first, then cut into the scene if needed
        # This ensures we capture the START of the intimate scene
        new_end = ideal_end - excess
        
        # Make sure we still cover at least the start of the flagged content
        # with a small buffer after
        min_end = start_time + 1.0  # At least 1 second into the flagged scene
        new_end = max(new_end, min_end)
        
        replace_start = ideal_start
        replace_end = new_end
        was_trimmed = True
        trimmed_seconds = excess
    else:
        replace_start = ideal_start
        replace_end = ideal_end
        was_trimmed = False
        trimmed_seconds = 0
    
    actual_duration = replace_end - replace_start
    
    print(f"\n🔄 Replacing scene {scene_index + 1}:")
    print(f"   Flagged: {start_time:.1f}s - {end_time:.1f}s ({original_duration:.1f}s)")
    if was_trimmed:
        print(f"   ⚠️  Scene too long for Veo ({ideal_duration:.1f}s > {max_veo_duration}s)")
        print(f"   ✂️  Trimmed {trimmed_seconds:.1f}s to fit within {max_veo_duration}s")
    print(f"   Will cut: {replace_start:.1f}s - {replace_end:.1f}s ({actual_duration:.1f}s)")
    
    # Extract boundary frames at the exact cut points (replace_start and replace_end)
    print("  📸 Extracting clean boundary frames...")
    first_b64, last_b64 = extract_frames_at_times(
        video_path, replace_start, replace_end
    )
    
    # Save frames for reference
    frames_dir = output_dir_path / "frames"
    frames_dir.mkdir(exist_ok=True)
    save_frame_to_file(first_b64, str(frames_dir / f"scene_{scene_index}_first.jpg"))
    save_frame_to_file(last_b64, str(frames_dir / f"scene_{scene_index}_last.jpg"))
    
    # The replacement duration is the cut window we calculated
    scene_duration = actual_duration
    
    # Generate replacement
    output_path = str(output_dir_path / f"replacement_{scene_index}.mp4")
    
    result = generate_replacement_clip(
        first_frame_b64=first_b64,
        last_frame_b64=last_b64,
        scene_duration=scene_duration,
        scene_description=scene_description,
        issues=issues,
        output_path=output_path,
        resolution=resolution,
    )
    
    return {
        "scene_index": scene_index,
        "original_start": start_time,
        "original_end": end_time,
        "replacement_start": replace_start,  # This is where we cut FROM
        "replacement_end": replace_end,      # This is where we cut TO
        "replacement_path": result.get("output_path"),
        "replacement_url": result.get("video_url"),
        "duration": scene_duration,
        "veo_duration": result.get("duration"),
        "prompt": result.get("prompt"),
        "buffer_seconds": buffer_seconds,
        "was_trimmed": was_trimmed,
        "trimmed_seconds": trimmed_seconds,
    }


def process_all_replacements(
    video_path: str,
    segments: list[dict],
    output_dir: str = "replacements",
    resolution: str = "720p",
    max_scenes: int | None = None,
) -> list[dict]:
    """
    Process all flagged segments and generate replacements.
    
    Args:
        video_path: Path to the source video
        segments: List of segment dicts with start_seconds, end_seconds, description
        output_dir: Directory to save replacements
        resolution: Video resolution
        max_scenes: Optional limit on number of scenes to process
    
    Returns:
        List of replacement metadata dicts
    """
    if max_scenes:
        segments = segments[:max_scenes]
    
    print(f"\n🎬 Generating replacements for {len(segments)} scenes...")
    
    replacements = []
    for i, segment in enumerate(segments):
        # Support both timestamp formats
        start = segment.get("start_seconds", 0)
        end = segment.get("end_seconds", 0)
        
        # Parse from string format if needed
        if start == 0 and "start" in segment:
            from .utils import parse_timestamp
            start = parse_timestamp(segment["start"])
            end = parse_timestamp(segment["end"])
        
        description = segment.get("description", segment.get("reason", ""))
        issues = segment.get("issues", [])
        
        try:
            result = replace_scene(
                video_path=video_path,
                start_time=start,
                end_time=end,
                scene_description=description,
                issues=issues,
                output_dir=output_dir,
                scene_index=i,
                resolution=resolution,
            )
            replacements.append(result)
        except Exception as e:
            print(f"  ❌ Error replacing scene {i + 1}: {e}")
            replacements.append({
                "scene_index": i,
                "error": str(e),
                "original_start": start,
                "original_end": end,
            })
    
    return replacements
