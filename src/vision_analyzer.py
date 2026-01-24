"""GPT-4o vision analysis for Halal content detection."""

import json

from openai import OpenAI

from .config import VISION_PROMPT, DETAILED_TIMING_PROMPT
from .frame_extractor import extract_frames, extract_dense_frames


def analyze_scene_with_vision(
    client: OpenAI,
    frames_b64: list[str],
    scene_index: int
) -> dict:
    """
    Analyze frames using GPT-4o vision API for halal content detection.
    
    Args:
        client: OpenAI client instance
        frames_b64: List of base64-encoded JPEG images
        scene_index: Scene index for logging purposes
    
    Returns:
        Dict with haram_score, severity, scene_description, issues_detected, 
        replacement_suggestion, confidence
    """
    if not frames_b64:
        return {
            "haram_score": 0.0,
            "nudity": 0.0,  # Keep for backward compatibility
            "sexual_activity": 0.0,  # Keep for backward compatibility
            "severity": "halal",
            "reason": "no frames extracted",
            "scene_description": "No frames could be extracted from this scene.",
            "issues_detected": [],
            "replacement_suggestion": "none",
            "confidence": 0.0,
            "tokens_in": 0,
            "tokens_out": 0
        }
    
    # Build message content with images
    content = [{"type": "text", "text": VISION_PROMPT}]
    
    for b64_img in frames_b64:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{b64_img}",
                "detail": "high"  # Use high detail for better accuracy
            }
        })
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": content}],
            max_tokens=500,  # Increased for detailed descriptions
            temperature=0.1
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Handle potential markdown code blocks
        if result_text.startswith("```"):
            lines = result_text.split("\n")
            # Remove first and last line (```json and ```)
            if lines[-1].strip() == "```":
                result_text = "\n".join(lines[1:-1])
            else:
                result_text = "\n".join(lines[1:])
        
        result = json.loads(result_text)
        
        # Extract token usage for cost tracking
        usage = response.usage
        
        # Map new format to include backward-compatible fields
        haram_score = float(result.get("haram_score", 0.0))
        
        return {
            "haram_score": haram_score,
            "nudity": haram_score,  # Backward compatibility
            "sexual_activity": haram_score,  # Backward compatibility
            "severity": result.get("severity", "halal"),
            "reason": result.get("scene_description", ""),
            "scene_description": result.get("scene_description", ""),
            "issues_detected": result.get("issues_detected", []),
            "replacement_suggestion": result.get("replacement_suggestion", "none"),
            "confidence": float(result.get("confidence", 0.5)),
            "tokens_in": usage.prompt_tokens if usage else 0,
            "tokens_out": usage.completion_tokens if usage else 0
        }
        
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse API response for scene {scene_index}: {e}")
        print(f"Response was: {result_text[:200]}...")
        return {
            "haram_score": 0.0,
            "nudity": 0.0,
            "sexual_activity": 0.0,
            "severity": "halal",
            "reason": "parse error",
            "scene_description": "Error parsing API response",
            "issues_detected": [],
            "replacement_suggestion": "none",
            "confidence": 0.0,
            "tokens_in": 0,
            "tokens_out": 0
        }
    except Exception as e:
        print(f"Warning: API error for scene {scene_index}: {e}")
        return {
            "haram_score": 0.0,
            "nudity": 0.0,
            "sexual_activity": 0.0,
            "severity": "halal",
            "reason": f"error: {str(e)}",
            "scene_description": f"Error: {str(e)}",
            "issues_detected": [],
            "replacement_suggestion": "none",
            "confidence": 0.0,
            "tokens_in": 0,
            "tokens_out": 0
        }


def refine_scene_timing(
    client: OpenAI,
    video_path: str,
    start_time: float,
    end_time: float,
    scene_index: int,
    target_width: int = 512
) -> tuple[float, float, int, int]:
    """
    Perform a second-pass analysis to find exact start/end of haram content.
    
    Extracts more frames and analyzes each to find precise boundaries.
    
    Args:
        client: OpenAI client
        video_path: Path to video
        start_time: Original scene start
        end_time: Original scene end
        scene_index: Scene index for logging
        target_width: Frame resize width
    
    Returns:
        Tuple of (refined_start, refined_end, tokens_in, tokens_out)
    """
    # Extract dense frames (1 per 0.5 seconds)
    duration = end_time - start_time
    num_frames = max(4, min(16, int(duration * 2)))  # 2 fps, max 16 frames
    
    frames_b64, timestamps = extract_dense_frames(
        video_path, start_time, end_time, num_frames, target_width
    )
    
    if len(frames_b64) < 2:
        return start_time, end_time, 0, 0
    
    # Build content with numbered frames
    content = [{"type": "text", "text": DETAILED_TIMING_PROMPT}]
    
    for i, b64_img in enumerate(frames_b64):
        content.append({"type": "text", "text": f"Frame {i+1} (at {timestamps[i]:.1f}s):"})
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{b64_img}",
                "detail": "low"
            }
        })
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": content}],
            max_tokens=300,
            temperature=0.1
        )
        
        result_text = response.choices[0].message.content.strip()
        
        if result_text.startswith("```"):
            lines = result_text.split("\n")
            if lines[-1].strip() == "```":
                result_text = "\n".join(lines[1:-1])
            else:
                result_text = "\n".join(lines[1:])
        
        frame_results = json.loads(result_text)
        usage = response.usage
        
        # Find first and last frames with issues
        first_issue = None
        last_issue = None
        
        for fr in frame_results:
            if fr.get("has_issue", False):
                frame_idx = fr.get("frame", 1) - 1
                if 0 <= frame_idx < len(timestamps):
                    if first_issue is None:
                        first_issue = frame_idx
                    last_issue = frame_idx
        
        if first_issue is not None and last_issue is not None:
            # Add small buffer (0.5s before and after)
            refined_start = max(start_time, timestamps[first_issue] - 0.5)
            refined_end = min(end_time, timestamps[last_issue] + 0.5)
            return refined_start, refined_end, usage.prompt_tokens, usage.completion_tokens
        
        return start_time, end_time, usage.prompt_tokens if usage else 0, usage.completion_tokens if usage else 0
        
    except Exception as e:
        print(f"Warning: Timing refinement failed for scene {scene_index}: {e}")
        return start_time, end_time, 0, 0


def process_scene(args: tuple) -> tuple[int, float, float, dict]:
    """
    Process a single scene: extract frames and analyze.
    
    Args:
        args: Tuple of (scene_index, start_time, end_time, video_path, 
              client, num_frames, frame_width) or
              (scene_index, start_time, end_time, video_path, 
              client, num_frames, frame_width, adaptive)
    
    Returns:
        Tuple of (scene_index, start_time, end_time, analysis_result)
    """
    # Handle both old and new argument formats
    if len(args) == 8:
        scene_index, start_time, end_time, video_path, client, num_frames, frame_width, adaptive = args
    else:
        scene_index, start_time, end_time, video_path, client, num_frames, frame_width = args
        adaptive = False
    
    frames = extract_frames(video_path, start_time, end_time, num_frames, frame_width, adaptive)
    analysis = analyze_scene_with_vision(client, frames, scene_index)
    
    # Add frame count to analysis for tracking
    analysis["frames_analyzed"] = len(frames)
    
    return (scene_index, start_time, end_time, analysis)
