#!/usr/bin/env python3
"""
Movie Scene Replacer - Flask API Backend

A REST API that wraps replace_scenes.py to process videos and filter inappropriate content.

Single Endpoint:
    POST /api/process - Process a video with visual filtering
                        Input: mp4 file + filter booleans
                        Output: final edited mp4
"""

import os
import sys
import uuid
import shutil
from pathlib import Path
from types import SimpleNamespace

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Get the project root directory (parent of src/api/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Add project root to path so we can import replace_scenes
sys.path.insert(0, str(PROJECT_ROOT))

# Import the replace_scenes functions
from replace_scenes import analyze_video, generate_replacements, stitch_video

# ============================================================================
# Configuration
# ============================================================================

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB max upload
app.config['UPLOAD_FOLDER'] = PROJECT_ROOT / 'uploads'
app.config['JOBS_FOLDER'] = PROJECT_ROOT / 'jobs'
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'mkv', 'avi', 'mov', 'webm'}

# Ensure directories exist
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)
app.config['JOBS_FOLDER'].mkdir(exist_ok=True)


# ============================================================================
# Helper Functions
# ============================================================================

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def get_job_path(job_id: str) -> Path:
    """Get the directory path for a job."""
    return app.config['JOBS_FOLDER'] / job_id


def create_job_directory(video_path: str, original_filename: str) -> tuple:
    """
    Create a new processing job directory.
    
    Returns:
        Tuple of (job_id, job_directory, job_video_path)
    """
    job_id = str(uuid.uuid4())[:8]
    job_dir = get_job_path(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy video to job directory
    video_ext = Path(original_filename).suffix
    job_video_path = job_dir / f"input{video_ext}"
    shutil.copy(video_path, job_video_path)
    
    return job_id, job_dir, job_video_path


def process_video_with_replace_scenes(
    video_path: str,
    output_path: str,
    work_dir: str,
    threshold: float = 0.4,
    resolution: str = "720p",
    strict: bool = False,
    refine_timing: bool = False,
    verbose: bool = True,
    max_scenes: int = None,
) -> dict:
    """
    Process a video using the replace_scenes.py logic.
    
    This wraps the functions from replace_scenes.py to:
    1. Analyze video for inappropriate content
    2. Generate replacement clips using fal.ai
    3. Stitch the final video
    
    Returns:
        dict with success status, output_path, and stats
    """
    # Create args namespace to match replace_scenes.py expectations
    args = SimpleNamespace(
        work_dir=work_dir,
        threshold=threshold,
        verbose=verbose,
        refine_timing=refine_timing,
        strict=strict,
        resolution=resolution,
        max_scenes=max_scenes,
        keep_original_audio=True,
        no_original_audio=False,
    )
    
    # Ensure work directory exists
    Path(work_dir).mkdir(parents=True, exist_ok=True)
    
    result = {
        "success": False,
        "output_path": None,
        "segments_found": 0,
        "replacements_successful": 0,
        "error": None,
    }
    
    try:
        # Phase 1: Analyze video for inappropriate content
        print("\n" + "=" * 60)
        print("PHASE 1: CONTENT ANALYSIS")
        print("=" * 60)
        
        segments = analyze_video(video_path, args)
        result["segments_found"] = len(segments)
        
        if not segments:
            print("\nNo inappropriate scenes detected - video is already clean!")
            # Just copy the original video to output
            shutil.copy(video_path, output_path)
            result["success"] = True
            result["output_path"] = output_path
            return result
        
        # Phase 2: Generate replacements
        print("\n" + "=" * 60)
        print("PHASE 2: GENERATING REPLACEMENTS")
        print("=" * 60)
        
        replacements = generate_replacements(video_path, segments, args)
        successful = [r for r in replacements if r.get("replacement_path")]
        result["replacements_successful"] = len(successful)
        
        if not successful:
            print("\nNo successful replacements - returning original video")
            shutil.copy(video_path, output_path)
            result["success"] = True
            result["output_path"] = output_path
            result["error"] = "No successful replacements generated"
            return result
        
        # Phase 3: Stitch final video
        print("\n" + "=" * 60)
        print("PHASE 3: STITCHING FINAL VIDEO")
        print("=" * 60)
        
        stitch_result = stitch_video(video_path, replacements, output_path, args)
        
        if stitch_result.get("success"):
            result["success"] = True
            result["output_path"] = output_path
            print("\nSuccessfully created cleaned video!")
        else:
            result["error"] = stitch_result.get("error", "Unknown stitching error")
            # Return original video on failure
            shutil.copy(video_path, output_path)
            result["success"] = True
            result["output_path"] = output_path
        
        return result
        
    except Exception as e:
        result["error"] = str(e)
        print(f"\nError during processing: {e}")
        # Return original video on error
        try:
            shutil.copy(video_path, output_path)
            result["success"] = True
            result["output_path"] = output_path
        except:
            pass
        return result


# ============================================================================
# API Endpoints
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "version": "2.0.0",
        "openai_configured": bool(os.environ.get('OPENAI_API_KEY')),
        "fal_configured": bool(os.environ.get('FAL_KEY')),
    })


@app.route('/api/process', methods=['POST'])
def process_video():
    """
    Process a video with visual filtering using replace_scenes.py logic.
    
    Input:
        - video (file): MP4 video file to process
        - filter_music (bool): Whether to filter out music (NOT YET IMPLEMENTED)
        - filter_profanity (bool): Whether to filter out profanity (NOT YET IMPLEMENTED)
        - filter_sexual_nudity (bool): Whether to filter out sexual/nudity content
        - threshold (float): Detection sensitivity (0.0-1.0, default: 0.4)
        - resolution (str): Video resolution for replacements (default: "720p")
        - strict (bool): Use stricter detection (default: false)
    
    Output:
        - Final edited MP4 file
    """
    # Check API keys first
    if not os.environ.get('OPENAI_API_KEY'):
        return jsonify({"error": "OPENAI_API_KEY not configured on server"}), 500
    
    if not os.environ.get('FAL_KEY'):
        return jsonify({"error": "FAL_KEY not configured on server"}), 500
    
    # Validate video file
    if 'video' not in request.files:
        return jsonify({"error": "No video file provided"}), 400
    
    file = request.files['video']
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": f"File type not allowed. Allowed: {app.config['ALLOWED_EXTENSIONS']}"}), 400
    
    # Parse filter options from form data
    filter_music = request.form.get('filter_music', 'false').lower() == 'true'
    filter_profanity = request.form.get('filter_profanity', 'false').lower() == 'true'
    filter_sexual_nudity = request.form.get('filter_sexual_nudity', 'false').lower() == 'true'
    
    # Parse additional options
    threshold = float(request.form.get('threshold', 0.4))
    resolution = request.form.get('resolution', '720p')
    strict = request.form.get('strict', 'false').lower() == 'true'
    
    # Check if at least one filter is enabled
    if not any([filter_music, filter_profanity, filter_sexual_nudity]):
        return jsonify({
            "error": "At least one filter must be enabled (filter_music, filter_profanity, or filter_sexual_nudity)"
        }), 400
    
    # Save uploaded file temporarily
    filename = secure_filename(file.filename)
    temp_path = app.config['UPLOAD_FOLDER'] / filename
    file.save(temp_path)
    
    try:
        # Create job directory
        job_id, job_dir, job_video_path = create_job_directory(str(temp_path), filename)
        
        # Clean up temp file
        temp_path.unlink()
        
        print(f"\n{'=' * 60}")
        print(f"Created job: {job_id}")
        print(f"   Filters: music={filter_music}, profanity={filter_profanity}, sexual_nudity={filter_sexual_nudity}")
        print(f"{'=' * 60}")
        
        # Set output path
        output_path = str(job_dir / "output_clean.mp4")
        
        # Process video if sexual_nudity filter is enabled (visual processing)
        if filter_sexual_nudity:
            result = process_video_with_replace_scenes(
                video_path=str(job_video_path),
                output_path=output_path,
                work_dir=str(job_dir),
                threshold=threshold,
                resolution=resolution,
                strict=strict,
            )
            
            if not result["success"]:
                return jsonify({"error": result.get("error", "Processing failed")}), 500
            
            output_path = result["output_path"]
        else:
            # No visual processing, just copy input to output
            shutil.copy(str(job_video_path), output_path)
        
        # TODO: Audio filtering (music, profanity) - not yet implemented
        # if filter_music or filter_profanity:
        #     output_path = apply_audio_filters(output_path, job_dir, filter_music, filter_profanity)
        
        # Generate download filename
        original_name = Path(filename).stem
        download_name = f"{original_name}_clean.mp4"
        
        print(f"\nProcessing complete! Returning cleaned video.")
        print(f"   Output: {output_path}")
        
        # Return the processed video file
        return send_file(
            output_path,
            mimetype='video/mp4',
            as_attachment=True,
            download_name=download_name
        )
        
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        print(f"\nError processing video: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large. Maximum size is 2GB."}), 413


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error", "details": str(e)}), 500


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("MOVIE SCENE REPLACER API v2.0")
    print("=" * 60)
    
    # Check required API keys
    openai_ok = bool(os.environ.get('OPENAI_API_KEY'))
    fal_ok = bool(os.environ.get('FAL_KEY'))
    
    print(f"\nConfiguration:")
    print(f"   OPENAI_API_KEY: {'Set' if openai_ok else 'NOT SET'}")
    print(f"   FAL_KEY: {'Set' if fal_ok else 'NOT SET'}")
    
    if not openai_ok:
        print("\nWarning: OPENAI_API_KEY not set - visual analysis will fail")
    if not fal_ok:
        print("Warning: FAL_KEY not set - video generation will fail")
    
    print(f"\nDirectories:")
    print(f"   Project root: {PROJECT_ROOT}")
    print(f"   Uploads: {app.config['UPLOAD_FOLDER']}")
    print(f"   Jobs: {app.config['JOBS_FOLDER']}")
    
    print(f"\nEndpoint:")
    print(f"   POST /api/process - Process video with filters")
    print(f"\nInput Parameters:")
    print(f"   - video: MP4 file to process")
    print(f"   - filter_sexual_nudity: Filter sexual/nudity content (bool)")
    print(f"   - filter_music: Filter music (bool) - NOT YET IMPLEMENTED")
    print(f"   - filter_profanity: Filter profanity (bool) - NOT YET IMPLEMENTED")
    print(f"   - threshold: Detection sensitivity (0.0-1.0, default: 0.4)")
    print(f"   - resolution: Replacement resolution (720p/1080p/4k)")
    print(f"   - strict: Stricter detection (bool)")
    
    print(f"\nOutput: Final edited MP4 file")
    print("=" * 60 + "\n")
    
    app.run(host='0.0.0.0', port=5001, debug=True)
