"""Scene detection using PySceneDetect."""

import cv2
from scenedetect import detect, ContentDetector


def detect_scenes(video_path: str, min_scene_length: float = 2.0) -> list[tuple[float, float]]:
    """
    Detect scene boundaries in a video using PySceneDetect.
    
    Args:
        video_path: Path to the video file
        min_scene_length: Minimum scene length in seconds (shorter scenes get merged)
    
    Returns:
        List of (start_seconds, end_seconds) tuples
    """
    print(f"Detecting scenes in {video_path}...")
    
    # Detect scenes using content detector
    # Lower threshold (22.0) catches more scene changes for better granularity
    scene_list = detect(video_path, ContentDetector(threshold=22.0))
    
    if not scene_list:
        # If no scenes detected, treat entire video as one scene
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        cap.release()
        return [(0.0, duration)]
    
    # Convert to (start, end) tuples in seconds
    scenes = []
    for scene in scene_list:
        start = scene[0].get_seconds()
        end = scene[1].get_seconds()
        scenes.append((start, end))
    
    # Merge short scenes
    merged = _merge_short_scenes(scenes, min_scene_length)
    
    print(f"Found {len(merged)} scenes (after merging short scenes)")
    return merged


def _merge_short_scenes(
    scenes: list[tuple[float, float]], 
    min_length: float
) -> list[tuple[float, float]]:
    """Merge scenes shorter than min_length into adjacent scenes."""
    if not scenes:
        return []
    
    merged = []
    for start, end in scenes:
        if merged and (end - start) < min_length:
            # Merge with previous scene
            prev_start, _ = merged[-1]
            merged[-1] = (prev_start, end)
        elif merged and (start - merged[-1][1]) < 0.1:
            # Continuous with previous, check if previous is short
            prev_start, prev_end = merged[-1]
            if (prev_end - prev_start) < min_length:
                merged[-1] = (prev_start, end)
            else:
                merged.append((start, end))
        else:
            merged.append((start, end))
    
    return merged
