"""Persistent API usage tracking."""

import json
from datetime import datetime
from pathlib import Path

# GPT-4o pricing (as of 2024)
PRICE_INPUT_PER_1M = 2.50   # $2.50 per 1M input tokens
PRICE_OUTPUT_PER_1M = 10.00  # $10.00 per 1M output tokens

DEFAULT_LOG_PATH = Path(__file__).parent.parent / "usage_log.json"


def calculate_cost(tokens_in: int, tokens_out: int) -> float:
    """Calculate cost in USD from token counts."""
    cost_in = (tokens_in / 1_000_000) * PRICE_INPUT_PER_1M
    cost_out = (tokens_out / 1_000_000) * PRICE_OUTPUT_PER_1M
    return cost_in + cost_out


def log_usage(
    video_name: str,
    scenes_count: int,
    tokens_in: int,
    tokens_out: int,
    segments_found: int,
    log_path: Path = DEFAULT_LOG_PATH
) -> dict:
    """
    Append usage record to the log file.
    
    Returns the new record that was added.
    """
    cost = calculate_cost(tokens_in, tokens_out)
    
    record = {
        "timestamp": datetime.now().isoformat(),
        "video": video_name,
        "scenes": scenes_count,
        "segments_found": segments_found,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": round(cost, 6)
    }
    
    # Load existing log or create new
    if log_path.exists():
        with open(log_path, "r") as f:
            log_data = json.load(f)
    else:
        log_data = {"runs": [], "totals": {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0}}
    
    # Append new record
    log_data["runs"].append(record)
    
    # Update totals
    log_data["totals"]["tokens_in"] += tokens_in
    log_data["totals"]["tokens_out"] += tokens_out
    log_data["totals"]["cost_usd"] = round(
        log_data["totals"]["cost_usd"] + cost, 6
    )
    
    # Write back
    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=2)
    
    return record


def get_usage_summary(log_path: Path = DEFAULT_LOG_PATH) -> dict | None:
    """Get usage summary from log file."""
    if not log_path.exists():
        return None
    
    with open(log_path, "r") as f:
        log_data = json.load(f)
    
    return {
        "total_runs": len(log_data["runs"]),
        "total_tokens_in": log_data["totals"]["tokens_in"],
        "total_tokens_out": log_data["totals"]["tokens_out"],
        "total_cost_usd": log_data["totals"]["cost_usd"]
    }


def print_usage_summary(log_path: Path = DEFAULT_LOG_PATH):
    """Print a formatted usage summary."""
    summary = get_usage_summary(log_path)
    
    if not summary:
        print("No usage history found.")
        return
    
    print("\n" + "="*50)
    print("CUMULATIVE API USAGE")
    print("="*50)
    print(f"  Total runs:        {summary['total_runs']}")
    print(f"  Total input tokens:  {summary['total_tokens_in']:,}")
    print(f"  Total output tokens: {summary['total_tokens_out']:,}")
    print(f"  Total cost:        ${summary['total_cost_usd']:.4f}")
    print("="*50)
