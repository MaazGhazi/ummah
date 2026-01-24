# Movie Content Filter (Sex & Nudity)

Automatically detect Sex & Nudity content in movies using GPT-4o vision analysis. Uses IMDB-style categories to identify content for filtering.

## What It Detects

**Sex** (any sexual nature):
- Kissing (passionate/romantic kissing, making out)
- Groping/touching (intimate touching, caressing)
- Sexual activity (intercourse, implied or explicit)
- Suggestive behavior (seductive poses, sensual dancing)

**Nudity**:
- Revealing clothing (low-cut tops, swimwear, lingerie)
- Partial nudity (exposed back, cleavage, shirtless in sexual context)
- Full nudity (breasts, buttocks, genitals)

## How It Works

1. **Scene Detection** - Uses PySceneDetect to find natural scene boundaries
2. **Frame Extraction** - Extracts 8 evenly-spaced frames from each scene
3. **Vision Analysis** - Sends frames to GPT-4o for NSFW content detection
4. **Segment Output** - Generates JSON with timestamps of flagged scenes

## Project Structure

```
ummah/
├── process_movie.py      # Main CLI entry point
├── src/
│   ├── __init__.py
│   ├── config.py         # Configuration and .env loading
│   ├── utils.py          # Time formatting helpers
│   ├── scene_detector.py # PySceneDetect wrapper
│   ├── frame_extractor.py# Video frame extraction
│   ├── vision_analyzer.py# GPT-4o vision API
│   └── aggregator.py     # Segment merging
├── requirements.txt
├── env_example.txt       # Example .env file
└── README.md
```

## Installation

```bash
cd ummah

# Install dependencies
pip install -r requirements.txt
```

## Setup

Create a `.env` file with your OpenAI API key:

```bash
# Copy the example file
cp env_example.txt .env

# Edit .env and add your key
OPENAI_API_KEY=your-api-key-here
```

Or set it as an environment variable:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Usage

### Basic Usage

```bash
python process_movie.py movie.mp4
```

Creates `segments.json` with detected NSFW segments.

### Custom Output File

```bash
python process_movie.py movie.mp4 -o my_segments.json
```

### Adjust Sensitivity

Lower threshold = more sensitive (catches more, may have false positives):

```bash
python process_movie.py movie.mp4 --threshold 0.4
```

Higher threshold = less sensitive (fewer false positives, may miss some):

```bash
python process_movie.py movie.mp4 --threshold 0.8
```

### All Options

```bash
python process_movie.py movie.mp4 \
    -o segments.json \
    --threshold 0.6 \
    --frames-per-scene 8 \
    --min-scene-length 2.0 \
    --max-workers 4 \
    --frame-width 512
```

| Option | Default | Description |
|--------|---------|-------------|
| `-o, --output` | segments.json | Output JSON file path |
| `--threshold` | 0.6 | NSFW score threshold (0.0-1.0) |
| `--frames-per-scene` | 8 | Frames to extract per scene |
| `--min-scene-length` | 2.0 | Minimum scene length in seconds |
| `--max-workers` | 4 | Parallel API requests |
| `--frame-width` | 512 | Resize frame width (pixels) |

## Output Format

```json
[
  {
    "start": "00:12:45",
    "end": "00:13:22",
    "severity": "moderate",
    "reason": "passionate kissing, revealing clothing",
    "confidence": 0.85
  }
]
```

### Severity Levels (IMDB-style)

| Severity | Score Range | Examples |
|----------|-------------|----------|
| **none** | 0.0-0.2 | Casual clothing, brief peck |
| **mild** | 0.3-0.5 | Passionate kissing, revealing clothing, shirtless scenes |
| **moderate** | 0.6-0.7 | Making out, lingerie/underwear, partial nudity |
| **severe** | 0.8-1.0 | Full nudity, sexual activity, explicit content |

## Cost Estimation

Approximate costs per movie (GPT-4o):
- **Short film (30 min)**: ~$0.15-0.25
- **Standard movie (2 hr)**: ~$0.35-0.60
- **Long movie (3 hr)**: ~$0.60-1.00

## Tips

**Reduce false positives**: Increase `--threshold` to 0.7-0.8

**Improve accuracy**: Use `--frames-per-scene 12` and `--threshold 0.5`

**Speed up processing**: Use `--max-workers 8` and `--frame-width 384`

## Requirements

- Python 3.10+
- OpenAI API key with GPT-4o access
- FFmpeg (for video processing via OpenCV)
