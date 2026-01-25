"""Frame extraction from video files."""

import base64
from io import BytesIO

import cv2
from PIL import Image


def calculate_adaptive_frames(duration: float, base_frames: int = 10) -> int:
    """
    Calculate optimal number of frames based on scene duration.
    
    Shorter scenes need proportionally more frames to catch quick moments.
    Longer scenes can use fewer frames per second.
    
    Args:
        duration: Scene duration in seconds
        base_frames: Base number of frames to extract
    
    Returns:
        Optimal number of frames for this scene
    """
    if duration <= 2.0:
        # Very short scenes: 4-5 fps to catch quick moments
        return max(base_frames, int(duration * 4))
    elif duration <= 5.0:
        # Short scenes: 3 fps
        return max(base_frames, int(duration * 3))
    elif duration <= 10.0:
        # Medium scenes: 2 fps
        return max(base_frames, int(duration * 2))
    else:
        # Long scenes: 1.5 fps, cap at 20 frames
        return min(20, max(base_frames, int(duration * 1.5)))


def extract_frames(
    video_path: str,
    start_time: float,
    end_time: float,
    num_frames: int = 10,
    target_width: int = 512,
    adaptive: bool = False
) -> list[str]:
    """
    Extract evenly-spaced frames from a video segment.
    
    Args:
        video_path: Path to the video file
        start_time: Start time in seconds
        end_time: End time in seconds
        num_frames: Number of frames to extract (or base for adaptive)
        target_width: Resize frames to this width (maintains aspect ratio)
        adaptive: If True, calculate optimal frames based on scene duration
    
    Returns:
        List of base64-encoded JPEG images
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    if fps <= 0:
        cap.release()
        return []
    
    duration = end_time - start_time
    if duration <= 0:
        cap.release()
        return []
    
    # Use adaptive frame count if enabled
    if adaptive:
        num_frames = calculate_adaptive_frames(duration, num_frames)
    
    # Calculate frame positions (evenly spaced)
    interval = duration / (num_frames + 1)
    timestamps = [start_time + interval * (i + 1) for i in range(num_frames)]
    
    frames_b64 = []
    for ts in timestamps:
        frame_number = int(ts * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        
        if not ret:
            continue
        
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
        img.save(buffer, format="JPEG", quality=85)
        b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
        frames_b64.append(b64_data)
    
    cap.release()
    return frames_b64


def extract_dense_frames(
    video_path: str,
    start_time: float,
    end_time: float,
    num_frames: int = 16,
    target_width: int = 512
) -> tuple[list[str], list[float]]:
    """
    Extract dense frames with their timestamps for precise timing analysis.
    
    Args:
        video_path: Path to the video file
        start_time: Start time in seconds
        end_time: End time in seconds
        num_frames: Number of frames to extract
        target_width: Resize frames to this width (maintains aspect ratio)
    
    Returns:
        Tuple of (list of base64-encoded JPEG images, list of timestamps)
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    if fps <= 0:
        cap.release()
        return [], []
    
    duration = end_time - start_time
    if duration <= 0:
        cap.release()
        return [], []
    
    # Calculate frame positions (evenly spaced, including edges)
    if num_frames == 1:
        timestamps = [(start_time + end_time) / 2]
    else:
        interval = duration / (num_frames - 1)
        timestamps = [start_time + interval * i for i in range(num_frames)]
    
    frames_b64 = []
    actual_timestamps = []
    
    for ts in timestamps:
        frame_number = int(ts * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        
        if not ret:
            continue
        
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
        img.save(buffer, format="JPEG", quality=85)
        b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
        frames_b64.append(b64_data)
        actual_timestamps.append(ts)
    
    cap.release()
    return frames_b64, actual_timestamps
