#!/usr/bin/env python3
"""
Movie Scene Replacer - Flask API Backend

A REST API for analyzing movies, detecting inappropriate content,
and generating family-friendly replacements using AI.

Endpoints:
    POST /api/upload          - Upload a video file
    POST /api/analyze         - Analyze video for inappropriate content
    POST /api/replace         - Generate replacement clips for flagged scenes
    POST /api/stitch          - Stitch the final cleaned video
    POST /api/process         - Full pipeline (analyze + replace + stitch)
    GET  /api/status/<job_id> - Check job status
    GET  /api/download/<job_id> - Download the cleaned video
    GET  /api/segments/<job_id> - Get detected segments
    DELETE /api/job/<job_id>  - Delete a job and its files
"""

import os
import json
import uuid
import shutil
import threading
from pathlib import Path
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our modules
from src.core.analysis import analyze_movie
from src.core.scene_replacer import process_all_replacements
from src.core.video_stitcher import stitch_movie_with_replacements, get_video_info

# ============================================================================
# Configuration
# ============================================================================

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB max upload
app.config['UPLOAD_FOLDER'] = Path('uploads')
app.config['JOBS_FOLDER'] = Path('jobs')
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'mkv', 'avi', 'mov', 'webm'}

# Ensure directories exist
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)
app.config['JOBS_FOLDER'].mkdir(exist_ok=True)

# Job status tracking (in-memory, use Redis for production)
jobs = {}

# ============================================================================
# Helpers
# ============================================================================

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def get_job_path(job_id: str) -> Path:
    """Get the directory path for a job."""
    return app.config['JOBS_FOLDER'] / job_id


def create_job(video_path: str, original_filename: str) -> dict:
    """Create a new processing job."""
    job_id = str(uuid.uuid4())[:8]
    job_dir = get_job_path(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy video to job directory
    video_ext = Path(original_filename).suffix
    job_video_path = job_dir / f"input{video_ext}"
    shutil.copy(video_path, job_video_path)
    
    # Get video info
    video_info = get_video_info(str(job_video_path))
    
    job = {
        "id": job_id,
        "status": "created",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "original_filename": original_filename,
        "video_path": str(job_video_path),
        "video_info": video_info,
        "segments": [],
        "replacements": [],
        "output_path": None,
        "error": None,
        "progress": {
            "phase": "created",
            "percent": 0,
            "message": "Job created"
        }
    }
    
    jobs[job_id] = job
    save_job(job)
    return job


def save_job(job: dict):
    """Persist job data to disk."""
    job_dir = get_job_path(job["id"])
    with open(job_dir / "job.json", "w") as f:
        json.dump(job, f, indent=2, default=str)


def load_job(job_id: str) -> dict | None:
    """Load job data from disk."""
    if job_id in jobs:
        return jobs[job_id]
    
    job_file = get_job_path(job_id) / "job.json"
    if job_file.exists():
        with open(job_file) as f:
            job = json.load(f)
            jobs[job_id] = job
            return job
    return None


def update_job(job_id: str, **updates):
    """Update job with new data."""
    job = load_job(job_id)
    if job:
        job.update(updates)
        job["updated_at"] = datetime.now().isoformat()
        jobs[job_id] = job
        save_job(job)
    return job


def require_api_key(f):
    """Decorator to require API key for endpoints (optional security)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Skip API key check if not configured
        api_key = os.environ.get('API_KEY')
        if api_key:
            provided_key = request.headers.get('X-API-Key')
            if provided_key != api_key:
                return jsonify({"error": "Invalid or missing API key"}), 401
        return f(*args, **kwargs)
    return decorated


# ============================================================================
# Background Processing Functions
# ============================================================================

def run_analysis(job_id: str, threshold: float = 0.4, strict: bool = False):
    """Run video analysis in background thread."""
    try:
        job = load_job(job_id)
        if not job:
            return
        
        update_job(job_id, 
                   status="analyzing",
                   progress={"phase": "analyzing", "percent": 10, "message": "Starting content analysis..."})
        
        video_path = job["video_path"]
        job_dir = get_job_path(job_id)
        
        # Run analysis
        result = analyze_movie(
            video_path,
            output_path=str(job_dir / "segments.json"),
            threshold=threshold,
            strict=strict,
            high_accuracy=True,
            quiet=True,
            save_output=True,
            log_usage_flag=True,
        )
        
        segments = result.get("segments", [])
        stats = result.get("stats", {})
        
        update_job(job_id,
                   status="analyzed",
                   segments=segments,
                   analysis_stats=stats,
                   progress={"phase": "analyzed", "percent": 100, "message": f"Found {len(segments)} flagged segments"})
        
    except Exception as e:
        update_job(job_id, status="error", error=str(e),
                   progress={"phase": "error", "percent": 0, "message": str(e)})


def run_replacement(job_id: str, resolution: str = "720p", max_scenes: int | None = None):
    """Run replacement generation in background thread."""
    try:
        job = load_job(job_id)
        if not job:
            return
        
        segments = job.get("segments", [])
        if not segments:
            update_job(job_id, status="no_segments", 
                       progress={"phase": "complete", "percent": 100, "message": "No segments to replace"})
            return
        
        update_job(job_id,
                   status="generating",
                   progress={"phase": "generating", "percent": 10, "message": f"Generating {len(segments)} replacements..."})
        
        video_path = job["video_path"]
        job_dir = get_job_path(job_id)
        replacements_dir = job_dir / "replacements"
        
        # Generate replacements
        replacements = process_all_replacements(
            video_path=video_path,
            segments=segments,
            output_dir=str(replacements_dir),
            resolution=resolution,
            max_scenes=max_scenes,
        )
        
        successful = [r for r in replacements if r.get("replacement_path")]
        
        update_job(job_id,
                   status="generated",
                   replacements=replacements,
                   progress={"phase": "generated", "percent": 100, 
                            "message": f"Generated {len(successful)}/{len(segments)} replacements"})
        
    except Exception as e:
        update_job(job_id, status="error", error=str(e),
                   progress={"phase": "error", "percent": 0, "message": str(e)})


def run_stitching(job_id: str, keep_original_audio: bool = True):
    """Run video stitching in background thread."""
    try:
        job = load_job(job_id)
        if not job:
            return
        
        replacements = job.get("replacements", [])
        successful_replacements = [r for r in replacements if r.get("replacement_path")]
        
        if not successful_replacements:
            update_job(job_id, status="no_replacements",
                       progress={"phase": "complete", "percent": 100, "message": "No replacements to stitch"})
            return
        
        update_job(job_id,
                   status="stitching",
                   progress={"phase": "stitching", "percent": 10, "message": "Stitching final video..."})
        
        video_path = job["video_path"]
        job_dir = get_job_path(job_id)
        output_path = str(job_dir / "output_clean.mp4")
        
        # Stitch video
        result = stitch_movie_with_replacements(
            original_video=video_path,
            replacements=successful_replacements,
            output_path=output_path,
            work_dir=str(job_dir / "stitch_work"),
            keep_original_audio=keep_original_audio,
        )
        
        if result.get("success"):
            update_job(job_id,
                       status="complete",
                       output_path=output_path,
                       stitch_result=result,
                       progress={"phase": "complete", "percent": 100, 
                                "message": f"Video ready! {result.get('replacements_applied', 0)} scenes replaced"})
        else:
            update_job(job_id, status="error", error="Stitching failed",
                       progress={"phase": "error", "percent": 0, "message": "Stitching failed"})
        
    except Exception as e:
        update_job(job_id, status="error", error=str(e),
                   progress={"phase": "error", "percent": 0, "message": str(e)})


def run_full_pipeline(job_id: str, threshold: float = 0.4, resolution: str = "720p",
                      strict: bool = False, max_scenes: int | None = None,
                      keep_original_audio: bool = True):
    """Run the full pipeline in background thread."""
    try:
        # Phase 1: Analyze
        run_analysis(job_id, threshold=threshold, strict=strict)
        
        job = load_job(job_id)
        if job.get("status") == "error":
            return
        
        segments = job.get("segments", [])
        if not segments:
            update_job(job_id, status="complete",
                       progress={"phase": "complete", "percent": 100, 
                                "message": "No inappropriate content detected - video is clean!"})
            return
        
        # Phase 2: Generate replacements
        run_replacement(job_id, resolution=resolution, max_scenes=max_scenes)
        
        job = load_job(job_id)
        if job.get("status") == "error":
            return
        
        # Phase 3: Stitch
        run_stitching(job_id, keep_original_audio=keep_original_audio)
        
    except Exception as e:
        update_job(job_id, status="error", error=str(e),
                   progress={"phase": "error", "percent": 0, "message": str(e)})


# ============================================================================
# API Endpoints
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "openai_configured": bool(os.environ.get('OPENAI_API_KEY')),
        "fal_configured": bool(os.environ.get('FAL_KEY')),
    })


@app.route('/api/upload', methods=['POST'])
@require_api_key
def upload_video():
    """
    Upload a video file and create a processing job.
    
    Returns:
        Job object with job_id for subsequent operations
    """
    if 'video' not in request.files:
        return jsonify({"error": "No video file provided"}), 400
    
    file = request.files['video']
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": f"File type not allowed. Allowed: {app.config['ALLOWED_EXTENSIONS']}"}), 400
    
    # Save uploaded file temporarily
    filename = secure_filename(file.filename)
    temp_path = app.config['UPLOAD_FOLDER'] / filename
    file.save(temp_path)
    
    try:
        # Create job
        job = create_job(str(temp_path), filename)
        
        # Clean up temp file
        temp_path.unlink()
        
        return jsonify({
            "success": True,
            "job": job,
            "message": f"Video uploaded successfully. Job ID: {job['id']}"
        })
        
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        return jsonify({"error": str(e)}), 500


@app.route('/api/analyze/<job_id>', methods=['POST'])
@require_api_key
def analyze_video(job_id: str):
    """
    Analyze a video for inappropriate content.
    
    Body params:
        threshold (float): Detection sensitivity (0.0-1.0, default: 0.4)
        strict (bool): Use stricter detection (default: false)
    """
    job = load_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    data = request.get_json() or {}
    threshold = float(data.get('threshold', 0.4))
    strict = bool(data.get('strict', False))
    
    # Start analysis in background
    thread = threading.Thread(
        target=run_analysis,
        args=(job_id,),
        kwargs={'threshold': threshold, 'strict': strict}
    )
    thread.start()
    
    return jsonify({
        "success": True,
        "job_id": job_id,
        "message": "Analysis started",
        "status_url": f"/api/status/{job_id}"
    })


@app.route('/api/replace/<job_id>', methods=['POST'])
@require_api_key
def replace_segments(job_id: str):
    """
    Generate replacement clips for flagged segments.
    
    Body params:
        resolution (str): Video resolution - "720p", "1080p", "4k" (default: "720p")
        max_scenes (int): Maximum scenes to replace (optional, for testing)
    """
    job = load_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    if not job.get("segments"):
        return jsonify({"error": "No segments found. Run analysis first."}), 400
    
    data = request.get_json() or {}
    resolution = data.get('resolution', '720p')
    max_scenes = data.get('max_scenes')
    
    # Start replacement in background
    thread = threading.Thread(
        target=run_replacement,
        args=(job_id,),
        kwargs={'resolution': resolution, 'max_scenes': max_scenes}
    )
    thread.start()
    
    return jsonify({
        "success": True,
        "job_id": job_id,
        "message": "Replacement generation started",
        "status_url": f"/api/status/{job_id}"
    })


@app.route('/api/stitch/<job_id>', methods=['POST'])
@require_api_key
def stitch_video(job_id: str):
    """
    Stitch the final video with replacements.
    
    Body params:
        keep_original_audio (bool): Keep original audio during replacements (default: true)
    """
    job = load_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    if not job.get("replacements"):
        return jsonify({"error": "No replacements found. Run replacement first."}), 400
    
    data = request.get_json() or {}
    keep_original_audio = data.get('keep_original_audio', True)
    
    # Start stitching in background
    thread = threading.Thread(
        target=run_stitching,
        args=(job_id,),
        kwargs={'keep_original_audio': keep_original_audio}
    )
    thread.start()
    
    return jsonify({
        "success": True,
        "job_id": job_id,
        "message": "Stitching started",
        "status_url": f"/api/status/{job_id}"
    })


@app.route('/api/process/<job_id>', methods=['POST'])
@require_api_key
def process_full(job_id: str):
    """
    Run the full pipeline: analyze → replace → stitch.
    
    Body params:
        threshold (float): Detection sensitivity (default: 0.4)
        resolution (str): Video resolution (default: "720p")
        strict (bool): Stricter detection (default: false)
        max_scenes (int): Max scenes to replace (optional)
        keep_original_audio (bool): Keep original audio (default: true)
    """
    job = load_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    data = request.get_json() or {}
    
    # Start full pipeline in background
    thread = threading.Thread(
        target=run_full_pipeline,
        args=(job_id,),
        kwargs={
            'threshold': float(data.get('threshold', 0.4)),
            'resolution': data.get('resolution', '720p'),
            'strict': bool(data.get('strict', False)),
            'max_scenes': data.get('max_scenes'),
            'keep_original_audio': data.get('keep_original_audio', True),
        }
    )
    thread.start()
    
    return jsonify({
        "success": True,
        "job_id": job_id,
        "message": "Full processing started",
        "status_url": f"/api/status/{job_id}"
    })


@app.route('/api/status/<job_id>', methods=['GET'])
def get_status(job_id: str):
    """Get the current status of a job."""
    job = load_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    return jsonify({
        "id": job["id"],
        "status": job["status"],
        "progress": job.get("progress", {}),
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
        "segments_count": len(job.get("segments", [])),
        "replacements_count": len([r for r in job.get("replacements", []) if r.get("replacement_path")]),
        "has_output": job.get("output_path") is not None,
        "error": job.get("error"),
    })


@app.route('/api/segments/<job_id>', methods=['GET'])
def get_segments(job_id: str):
    """Get the detected segments for a job."""
    job = load_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    return jsonify({
        "job_id": job_id,
        "segments": job.get("segments", []),
        "analysis_stats": job.get("analysis_stats", {}),
    })


@app.route('/api/download/<job_id>', methods=['GET'])
def download_video(job_id: str):
    """Download the processed video."""
    job = load_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    output_path = job.get("output_path")
    if not output_path or not Path(output_path).exists():
        return jsonify({"error": "Output video not ready"}), 404
    
    # Generate download filename
    original_name = Path(job["original_filename"]).stem
    download_name = f"{original_name}_clean.mp4"
    
    return send_file(
        output_path,
        mimetype='video/mp4',
        as_attachment=True,
        download_name=download_name
    )


@app.route('/api/download/<job_id>/original', methods=['GET'])
def download_original(job_id: str):
    """Download the original uploaded video."""
    job = load_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    video_path = job.get("video_path")
    if not video_path or not Path(video_path).exists():
        return jsonify({"error": "Original video not found"}), 404
    
    return send_file(
        video_path,
        mimetype='video/mp4',
        as_attachment=True,
        download_name=job["original_filename"]
    )


@app.route('/api/job/<job_id>', methods=['GET'])
def get_job(job_id: str):
    """Get full job details."""
    job = load_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    return jsonify(job)


@app.route('/api/job/<job_id>', methods=['DELETE'])
@require_api_key
def delete_job(job_id: str):
    """Delete a job and all its files."""
    job = load_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    job_dir = get_job_path(job_id)
    
    try:
        if job_dir.exists():
            shutil.rmtree(job_dir)
        
        if job_id in jobs:
            del jobs[job_id]
        
        return jsonify({"success": True, "message": f"Job {job_id} deleted"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List all jobs."""
    job_dirs = list(app.config['JOBS_FOLDER'].iterdir())
    
    job_list = []
    for job_dir in job_dirs:
        if job_dir.is_dir():
            job = load_job(job_dir.name)
            if job:
                job_list.append({
                    "id": job["id"],
                    "status": job["status"],
                    "original_filename": job["original_filename"],
                    "created_at": job["created_at"],
                    "segments_count": len(job.get("segments", [])),
                    "has_output": job.get("output_path") is not None,
                })
    
    # Sort by creation time (newest first)
    job_list.sort(key=lambda x: x["created_at"], reverse=True)
    
    return jsonify({"jobs": job_list})


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
    # Check required API keys
    if not os.environ.get('OPENAI_API_KEY'):
        print("⚠️  Warning: OPENAI_API_KEY not set")
    if not os.environ.get('FAL_KEY'):
        print("⚠️  Warning: FAL_KEY not set")
    
    print("🎬 Movie Scene Replacer API")
    print("=" * 40)
    print("Endpoints:")
    print("  POST /api/upload          - Upload video")
    print("  POST /api/analyze/<id>    - Analyze for content")
    print("  POST /api/replace/<id>    - Generate replacements")
    print("  POST /api/stitch/<id>     - Stitch final video")
    print("  POST /api/process/<id>    - Full pipeline")
    print("  GET  /api/status/<id>     - Check status")
    print("  GET  /api/download/<id>   - Download result")
    print("=" * 40)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
