# Movie Scene Replacer - Backend

AI-powered movie content filtering system that detects and replaces inappropriate scenes with family-friendly alternatives using OpenAI GPT-4o Vision and Google Veo 3.1.

## 🏗️ Project Structure

```
ummah/
├── src/
│   ├── api/                      # Flask REST API
│   │   ├── __init__.py
│   │   └── app.py               # Main Flask application
│   │
│   └── core/                     # Core business logic
│       ├── __init__.py
│       ├── analysis.py           # Movie analysis pipeline
│       ├── scene_detector.py     # Scene boundary detection
│       ├── vision_analyzer.py    # GPT-4o content analysis
│       ├── scene_replacer.py     # Veo 3.1 replacement generation
│       ├── video_stitcher.py     # Video reassembly with FFmpeg
│       ├── frame_extractor.py    # Video frame extraction
│       ├── aggregator.py         # Segment merging logic
│       ├── usage_tracker.py      # API usage tracking
│       ├── config.py             # Configuration & prompts
│       └── utils.py              # Utility functions
│
├── run_api.py                    # Start API server
├── cli.py                        # Command-line interface
├── replace_scenes.py             # Legacy CLI (kept for compatibility)
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables (API keys)
│
├── uploads/                      # Temporary upload directory
├── jobs/                         # Job processing directories
└── myenv/                        # Python virtual environment
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
python3 -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file:

```env
OPENAI_API_KEY=sk-...
FAL_KEY=...
API_KEY=your-api-secret  # Optional: for API authentication
```

### 3. Start the API Server

```bash
python run_api.py
```

Server starts at `http://localhost:5000`

---

## 📡 API Endpoints

### Health Check
```bash
GET /api/health
```

### Upload Video
```bash
POST /api/upload
Content-Type: multipart/form-data

Form Data:
  video: <file>
```

### Full Processing Pipeline
```bash
POST /api/process/<job_id>
Content-Type: application/json

{
  "threshold": 0.4,
  "resolution": "720p",
  "strict": false,
  "max_scenes": null,
  "keep_original_audio": true
}
```

### Check Status
```bash
GET /api/status/<job_id>
```

### Download Result
```bash
GET /api/download/<job_id>
```

---

## 🔧 Core Components

### 1. **Content Analysis** (`src/core/analysis.py`)
- Uses PySceneDetect to find scene boundaries
- Extracts frames from each scene
- Analyzes frames with GPT-4o Vision API
- Detects: kissing, nudity, revealing clothing, intimate scenes

### 2. **Scene Replacement** (`src/core/scene_replacer.py`)
- Extracts clean boundary frames (before/after the scene)
- Generates replacement clips with Veo 3.1:
  - **Kissing → Fist bump**
  - **Revealing clothing → Fully clothed**
- Automatically trims long scenes to fit Veo's 8s limit

### 3. **Video Stitching** (`src/core/video_stitcher.py`)
- Uses FFmpeg to reassemble the movie
- Preserves original audio
- Handles duration mismatches intelligently
- Outputs clean MP4 file

---

## 📝 Example Usage

### Python API Client

```python
import requests

# 1. Upload video
with open('movie.mp4', 'rb') as f:
    response = requests.post('http://localhost:5000/api/upload', 
                           files={'video': f})
job_id = response.json()['job']['id']

# 2. Process full pipeline
requests.post(f'http://localhost:5000/api/process/{job_id}', 
             json={'threshold': 0.4, 'resolution': '720p'})

# 3. Check status
status = requests.get(f'http://localhost:5000/api/status/{job_id}').json()
print(f"Status: {status['status']} - {status['progress']['message']}")

# 4. Download when complete
if status['status'] == 'complete':
    video = requests.get(f'http://localhost:5000/api/download/{job_id}')
    with open('movie_clean.mp4', 'wb') as f:
        f.write(video.content)
```

### Command Line

```bash
# Analyze a video
python cli.py movie.mp4 -o segments.json --threshold 0.4

# Full replacement pipeline
python replace_scenes.py movie.mp4 -o movie_clean.mp4
```

---

## 🎛️ Configuration

### Detection Thresholds

| Threshold | Content Caught |
|-----------|----------------|
| 0.2 | Strict - catches subtle content |
| 0.4 | **Default** - moderate+ scenes |
| 0.6 | Relaxed - only heavy scenes |

### Resolution Options

- `720p` - Fast, good quality (default)
- `1080p` - Higher quality
- `4k` - Maximum quality (slower)

### Issues Detected

- `kissing` - Any kissing or lip contact
- `embracing` - Prolonged hugging
- `intimate_touching` - Romantic touching
- `nudity` / `partial_nudity` - Exposed skin
- `revealing_clothing` - Bikinis, lingerie
- `swimwear` / `shirtless` - Bathing suits
- `sexual_activity` - Any sexual content
- `bed_scene` - Bedroom scenes

---

## 🔐 Security

### API Key Authentication (Optional)

Set `API_KEY` in `.env` to require authentication:

```bash
curl -H "X-API-Key: your-api-secret" http://localhost:5000/api/upload
```

### File Upload Limits

- Maximum file size: 2GB
- Allowed formats: MP4, MKV, AVI, MOV, WEBM

---

## 📊 Job Status Flow

```
created → analyzing → analyzed → generating → generated → stitching → complete
                                                                    ↓
                                                                  error
```

---

## 🛠️ Development

### Running Tests

```bash
python -m pytest tests/
```

### Linting

```bash
flake8 src/
black src/
```

---

## 📦 Dependencies

- **OpenAI** - GPT-4o Vision for content analysis
- **fal.ai** - Veo 3.1 video generation
- **PySceneDetect** - Scene boundary detection
- **OpenCV** - Video frame extraction
- **FFmpeg** - Video processing
- **Flask** - REST API server

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

MIT License - see LICENSE file for details
