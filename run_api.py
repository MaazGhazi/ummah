#!/usr/bin/env python3
"""
Movie Scene Replacer - Run API Server

Start the Flask API server for the movie scene replacer backend.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.api.app import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
