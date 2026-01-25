"""Segment aggregation and merging."""

from .utils import parse_timestamp

# Severity ranking for comparison (halal guidelines)
SEVERITY_RANK = {"halal": 0, "none": 0, "questionable": 1, "mild": 2, "moderate": 3, "severe": 4}


def _max_severity(sev1: str, sev2: str) -> str:
    """Return the higher severity level."""
    return sev1 if SEVERITY_RANK.get(sev1, 0) >= SEVERITY_RANK.get(sev2, 0) else sev2


def _merge_issues(issues1: list, issues2: list) -> list:
    """Merge two issue lists without duplicates."""
    combined = list(issues1) if issues1 else []
    for issue in (issues2 or []):
        if issue not in combined:
            combined.append(issue)
    return combined


def _get_priority_replacement(rep1: str, rep2: str) -> str:
    """Return the more restrictive replacement suggestion."""
    priority = {"none": 0, "audio_only": 1, "blur_scene": 2, "skip": 3, "cut_segment": 4}
    return rep1 if priority.get(rep1, 0) >= priority.get(rep2, 0) else rep2


def merge_adjacent_segments(
    segments: list[dict], 
    gap_threshold: float = 2.0
) -> list[dict]:
    """
    Merge segments that are adjacent or very close together.
    
    Args:
        segments: List of segment dicts with start, end, severity, description, issues, etc.
        gap_threshold: Maximum gap in seconds to consider segments adjacent (default: 2.0)
    
    Returns:
        List of merged segment dicts
    """
    if not segments:
        return []
    
    # Sort by start time
    sorted_segments = sorted(segments, key=lambda x: parse_timestamp(x["start"]))
    
    merged = [sorted_segments[0].copy()]
    
    for segment in sorted_segments[1:]:
        prev = merged[-1]
        prev_end = parse_timestamp(prev["end"])
        curr_start = parse_timestamp(segment["start"])
        
        if curr_start - prev_end <= gap_threshold:
            # Merge: extend end time, combine descriptions, keep highest severity
            merged[-1]["end"] = segment["end"]
            
            # Update end_seconds if present
            if "end_seconds" in segment:
                merged[-1]["end_seconds"] = segment["end_seconds"]
            
            # Combine descriptions (use description or fall back to reason)
            prev_desc = prev.get("description", prev.get("reason", ""))
            curr_desc = segment.get("description", segment.get("reason", ""))
            if curr_desc and curr_desc not in prev_desc:
                merged[-1]["description"] = f"{prev_desc} | {curr_desc}"
            
            # Keep backward compatibility with 'reason' field
            if "reason" in prev:
                curr_reason = segment.get("reason", "")
                if curr_reason and curr_reason not in prev["reason"]:
                    merged[-1]["reason"] = f"{prev['reason']}; {curr_reason}"
            
            # Merge issues lists
            prev_issues = prev.get("issues", [])
            curr_issues = segment.get("issues", [])
            merged[-1]["issues"] = _merge_issues(prev_issues, curr_issues)
            
            # Keep highest score (haram_score or confidence)
            prev_score = prev.get("haram_score", prev.get("confidence", 0))
            curr_score = segment.get("haram_score", segment.get("confidence", 0))
            merged[-1]["haram_score"] = max(prev_score, curr_score)
            merged[-1]["confidence"] = max(prev_score, curr_score)  # backward compat
            
            # Keep highest severity
            merged[-1]["severity"] = _max_severity(
                prev.get("severity", "halal"), 
                segment.get("severity", "halal")
            )
            
            # Keep most restrictive replacement
            prev_rep = prev.get("replacement", "none")
            curr_rep = segment.get("replacement", "none")
            merged[-1]["replacement"] = _get_priority_replacement(prev_rep, curr_rep)
            
        else:
            merged.append(segment.copy())
    
    return merged
