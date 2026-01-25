#!/usr/bin/env python3
"""
Movie Scene Replacer - CLI Tool

Command-line interface for processing videos locally.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import argparse
from src.core.analysis import analyze_movie

def main():
    parser = argparse.ArgumentParser(description="Analyze movie for inappropriate content")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("-o", "--output", default="segments.json", help="Output file")
    parser.add_argument("--threshold", type=float, default=0.4, help="Detection threshold")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    analyze_movie(
        args.video,
        output_path=args.output,
        threshold=args.threshold,
        verbose=args.verbose,
    )

if __name__ == "__main__":
    main()
