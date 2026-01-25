# Ethical Movie Filter - Requirements Document

## Table of Contents

1. [Overview](#overview)
2. [High-Level Requirements](#high-level-requirements)
3. [Pipeline Stages](#pipeline-stages)
4. [Data Collection & Processing Layer (Detailed)](#data-collection--processing-layer-detailed)
5. [Technical Stack](#technical-stack)
6. [Data Structures](#data-structures)

---

## Overview

The **Ethical Movie Filter** is an application that allows users to transform any movie into an ethically filtered version. The system identifies and replaces violent, sexual, vulgar, and other objectionable content with AI-generated alternatives that preserve the narrative while presenting it in an ethical manner.

### Core Value Proposition

- Accept any movie in video format
- Automatically detect and classify unethical scenes/dialogue
- Replace unethical content with AI-generated ethical alternatives
- Silence or replace inappropriate dialogue
- Output a seamless, watchable ethical version of the movie

---

## High-Level Requirements

### 1. User Input & Configuration

- **FR-1.1**: Accept video files in common formats (MP4, MKV, AVI, MOV)
- **FR-1.2**: Accept optional subtitle files (.srt, .vtt)
- **FR-1.3**: Accept optional movie script files (.txt, .pdf)
- **FR-1.4**: Allow users to select filtering modes:
  - Vulgar Language Filter
  - Sexual Content Filter
  - Violence Filter
  - Gore/Graphic Content Filter
  - **Halal Mode** (comprehensive filter encompassing all categories)
- **FR-1.5**: Allow users to configure filter intensity levels (Low, Medium, High)

### 2. Data Collection & Processing

- **FR-2.1**: Extract and process subtitles from video or external file
- **FR-2.2**: Fetch supplementary data from external sources (IMDB Parent Guide, Kids-In-Mind)
- **FR-2.3**: Parse and analyze movie scripts when available
- **FR-2.4**: Detect scene boundaries from video using computer vision
- **FR-2.5**: Align all data sources into a unified scene-by-scene dataset

### 3. Content Analysis & Classification

- **FR-3.1**: Analyze each scene for unethical content using LLM
- **FR-3.2**: Classify content by category (violence, sexual, vulgar, etc.)
- **FR-3.3**: Assign severity scores to flagged content
- **FR-3.4**: Generate detailed descriptions of why content was flagged

### 4. Content Generation

- **FR-4.1**: Generate ethical replacement scenes using image/video generation AI
- **FR-4.2**: Maintain narrative continuity in generated content
- **FR-4.3**: Match visual style and tone of original movie
- **FR-4.4**: Handle dialogue replacement (silence or generate clean alternatives)

### 5. Video Construction

- **FR-5.1**: Seamlessly splice generated content with original video
- **FR-5.2**: Maintain audio synchronization
- **FR-5.3**: Preserve video quality
- **FR-5.4**: Output in standard video formats

### 6. Playback & Storage

- **FR-6.1**: Provide in-app video player for filtered content
- **FR-6.2**: Allow users to save filtered versions to their account
- **FR-6.3**: Support streaming playback for large files

---

## Pipeline Stages

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ETHICAL MOVIE FILTER PIPELINE                     │
└─────────────────────────────────────────────────────────────────────────────┘

Stage 1: USER INPUT
    │
    ▼
┌─────────────────┐
│  movie.mp4      │──────────────────────────────────────┐
│  movie.srt      │                                      │
│  script.txt     │                                      │
│  filter config  │                                      │
└─────────────────┘                                      │
    │                                                    │
    ▼                                                    │
Stage 2: DATA COLLECTION & PROCESSING                    │
    │                                                    │
    ▼                                                    │
┌─────────────────┐                                      │
│  segments.json  │ ◄── Unified scene dataset            │
└─────────────────┘                                      │
    │                                                    │
    ▼                                                    │
Stage 3: CONTENT ANALYSIS (LLM)                          │
    │                                                    │
    ▼                                                    │
┌─────────────────┐                                      │
│  flagged.json   │ ◄── Scenes requiring edits           │
└─────────────────┘                                      │
    │                                                    │
    ▼                                                    │
Stage 4: CONTENT GENERATION (AI)                         │
    │                                                    │
    ▼                                                    │
┌─────────────────┐                                      │
│  replacements/  │ ◄── Generated ethical scenes         │
└─────────────────┘                                      │
    │                                                    │
    ▼                                                    │
Stage 5: VIDEO CONSTRUCTION ◄────────────────────────────┘
    │                        (original video)
    ▼
┌─────────────────┐
│  ethical.mp4    │ ◄── Final output
└─────────────────┘
    │
    ▼
Stage 6: PLAYBACK & STORAGE
```

---

## Data Collection & Processing Layer (Detailed)

This section provides the detailed implementation requirements for **Stage 2: Data Collection & Processing**, which is critical for building an accurate dataset for content analysis.

### Architecture Overview

```
                              INPUTS
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
   ┌─────────┐           ┌─────────┐            ┌─────────┐
   │movie.srt│           │movie.mp4│            │script.txt│
   └────┬────┘           └────┬────┘            └────┬────┘
        │                     │                      │
        │                     │                      │
        ▼                     │                      ▼
┌───────────────────┐         │         ┌───────────────────────┐
│  PRE-SCREENING    │         │         │    PRE-SCREENING      │
│                   │         │         │                       │
│  • Parse SRT      │         │         │  • Parse Script       │
│  • Extract timed  │         │         │  • GPT-4o Script      │
│    dialogue       │         │         │    Analysis           │
│  • Fetch IMDB     │         │         │  • Scene breakdown    │
│    Parent Guide   │         │         │  • Character/action   │
│  • Fetch Kids-In- │         │         │    extraction         │
│    Mind data      │         │         │                       │
└────────┬──────────┘         │         └───────────┬───────────┘
         │                    │                     │
         │                    ▼                     │
         │         ┌───────────────────┐            │
         │         │  SCENE DETECTION  │            │
         │         │                   │            │
         │         │  • PySceneDetect  │            │
         │         │  • Frame analysis │            │
         │         │  • Scene          │            │
         │         │    boundaries     │            │
         │         └────────┬──────────┘            │
         │                  │                       │
         │                  ▼                       │
         │    ┌─────────────────────────────┐       │
         └───►│  ALIGN SCRIPT TO VIDEO      │◄──────┘
              │         SCENES              │
              │                             │
              │  • Match dialogue to scenes │
              │  • Timestamp alignment      │
              │  • Merge metadata           │
              └──────────────┬──────────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │   VISUAL VERIFICATION       │
              │                             │
              │  • Extract keyframes        │
              │  • GPT-4o Vision analysis   │
              │  • Validate scene content   │
              │  • Enrich descriptions      │
              └──────────────┬──────────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │      MERGE + SCORE          │
              │                             │
              │  • Combine all data sources │
              │  • Calculate confidence     │
              │  • Generate final segments  │
              └──────────────┬──────────────┘
                             │
                             ▼
                      ┌─────────────┐
                      │segments.json│
                      └─────────────┘
```

---

### Component Specifications

#### 2.1 Pre-Screening Module

##### 2.1.1 Subtitle Parser

**Purpose**: Extract timed dialogue from subtitle files

**Requirements**:

- **FR-2.1.1.1**: Parse .srt and .vtt subtitle formats
- **FR-2.1.1.2**: Extract start time, end time, and text for each subtitle entry
- **FR-2.1.1.3**: Handle multi-line subtitles
- **FR-2.1.1.4**: Clean HTML tags and formatting codes
- **FR-2.1.1.5**: Support multiple character encodings (UTF-8, Latin-1, etc.)

**Input**: `movie.srt` or `movie.vtt`

**Output**:

```json
{
  "subtitles": [
    {
      "index": 1,
      "start_time": "00:01:23,456",
      "end_time": "00:01:26,789",
      "start_ms": 83456,
      "end_ms": 86789,
      "text": "What are you doing here?"
    }
  ]
}
```

##### 2.1.2 Script Parser

**Purpose**: Parse movie scripts into structured scene and dialogue data

**Requirements**:

- **FR-2.1.2.1**: Parse common script formats (Final Draft, plain text)
- **FR-2.1.2.2**: Identify scene headings (INT./EXT. locations)
- **FR-2.1.2.3**: Extract character names and their dialogue
- **FR-2.1.2.4**: Capture action/description lines
- **FR-2.1.2.5**: Preserve scene order and structure

**Input**: `script.txt` or `script.pdf`

**Output**:

```json
{
  "scenes": [
    {
      "scene_number": 1,
      "heading": "INT. COFFEE SHOP - DAY",
      "location": "COFFEE SHOP",
      "time_of_day": "DAY",
      "interior": true,
      "elements": [
        {
          "type": "action",
          "text": "JOHN enters the crowded coffee shop, scanning the room."
        },
        {
          "type": "dialogue",
          "character": "JOHN",
          "text": "Have you seen Sarah?",
          "parenthetical": null
        }
      ]
    }
  ]
}
```

##### 2.1.3 GPT-4o Script Analysis

**Purpose**: Use LLM to enrich script data with semantic understanding

**Requirements**:

- **FR-2.1.3.1**: Analyze each script scene for narrative summary
- **FR-2.1.3.2**: Identify key plot points and character actions
- **FR-2.1.3.3**: Flag potentially sensitive content descriptions
- **FR-2.1.3.4**: Estimate scene duration based on content
- **FR-2.1.3.5**: Extract emotional tone and intensity

**Prompt Template**:

```
Analyze the following movie script scene and provide:
1. A brief narrative summary (2-3 sentences)
2. Key characters involved
3. Main actions/events
4. Emotional tone (e.g., tense, romantic, violent)
5. Any potentially sensitive content (violence, profanity, sexual content)
6. Estimated scene duration in seconds

Scene:
{scene_content}
```

**Output**:

```json
{
  "scene_number": 1,
  "summary": "John enters a coffee shop looking for Sarah, appearing anxious.",
  "characters": ["JOHN"],
  "key_actions": ["enters", "scans room", "asks about Sarah"],
  "emotional_tone": "anxious",
  "sensitive_content": [],
  "estimated_duration_sec": 15
}
```

##### 2.1.4 External Data Fetcher

**Purpose**: Retrieve content advisories from external databases

**Requirements**:

- **FR-2.1.4.1**: Query IMDB Parent Guide API/scraper for content warnings
- **FR-2.1.4.2**: Query Kids-In-Mind for detailed content ratings
- **FR-2.1.4.3**: Cache responses to avoid repeated requests
- **FR-2.1.4.4**: Handle rate limiting gracefully
- **FR-2.1.4.5**: Map external categories to internal classification system

**Data Sources**:
| Source | Data Provided | Timestamped |
|--------|---------------|-------------|
| IMDB Parent Guide | Violence, Sex, Profanity, Substances, Frightening scenes | No |
| Kids-In-Mind | Detailed scene descriptions with severity ratings | No |

**Output**:

```json
{
  "imdb_parent_guide": {
    "violence": ["A character is shot in the chest", "Fistfight in bar"],
    "sex_nudity": ["Brief kissing scene"],
    "profanity": ["Multiple uses of strong language"],
    "substances": ["Characters drink alcohol"],
    "frightening": ["Jump scare in basement"]
  },
  "kids_in_mind": {
    "sex_nudity_score": 4,
    "violence_gore_score": 7,
    "profanity_score": 6,
    "detailed_scenes": [
      {
        "category": "violence",
        "description": "A man punches another man repeatedly",
        "severity": "moderate"
      }
    ]
  }
}
```

---

#### 2.2 Scene Detection Module

##### 2.2.1 PySceneDetect Integration

**Purpose**: Detect scene boundaries in video file using computer vision

**Requirements**:

- **FR-2.2.1.1**: Process video files using PySceneDetect library
- **FR-2.2.1.2**: Support ContentDetector for gradual transitions
- **FR-2.2.1.3**: Support ThresholdDetector for hard cuts
- **FR-2.2.1.4**: Configure detection sensitivity thresholds
- **FR-2.2.1.5**: Handle various video codecs and resolutions
- **FR-2.2.1.6**: Output scene list with start/end timestamps

**Configuration Parameters**:

```python
{
    "detector": "ContentDetector",  # or "ThresholdDetector"
    "threshold": 30.0,              # sensitivity (lower = more scenes)
    "min_scene_len": 15,            # minimum frames per scene
    "show_progress": True
}
```

**Output**:

```json
{
  "video_info": {
    "filename": "movie.mp4",
    "duration_sec": 7200,
    "fps": 24,
    "resolution": "1920x1080"
  },
  "scenes": [
    {
      "scene_id": 1,
      "start_time": "00:00:00.000",
      "end_time": "00:01:23.456",
      "start_frame": 0,
      "end_frame": 1995,
      "duration_sec": 83.456
    }
  ]
}
```

---

#### 2.3 Scene Alignment Module

##### 2.3.1 Script-to-Video Alignment

**Purpose**: Map script scenes to detected video scenes using dialogue matching

**Requirements**:

- **FR-2.3.1.1**: Use subtitle timestamps as anchor points
- **FR-2.3.1.2**: Match script dialogue to subtitle text using fuzzy matching
- **FR-2.3.1.3**: Align script scene boundaries with video scene boundaries
- **FR-2.3.1.4**: Handle scenes that span multiple video cuts
- **FR-2.3.1.5**: Handle merged/split scenes between script and final cut
- **FR-2.3.1.6**: Calculate confidence scores for each alignment

**Alignment Algorithm**:

1. Extract all dialogue from script scenes
2. Extract all text from subtitles with timestamps
3. Use fuzzy string matching (Levenshtein distance) to match dialogue
4. For each match, associate script scene with video timestamp
5. Interpolate boundaries for scenes without dialogue
6. Merge overlapping script scenes into single video segments

**Output**:

```json
{
  "alignments": [
    {
      "script_scene": 1,
      "video_scenes": [1, 2],
      "start_time": "00:00:00.000",
      "end_time": "00:02:45.123",
      "confidence": 0.92,
      "matched_dialogues": [
        {
          "script_text": "Have you seen Sarah?",
          "subtitle_text": "Have you seen Sarah?",
          "similarity": 1.0,
          "timestamp": "00:01:23.456"
        }
      ]
    }
  ]
}
```

---

#### 2.4 Visual Verification Module

##### 2.4.1 Frame Extraction

**Purpose**: Extract representative frames from each scene for visual analysis

**Requirements**:

- **FR-2.4.1.1**: Extract keyframes at scene boundaries
- **FR-2.4.1.2**: Extract additional frames at regular intervals within scenes
- **FR-2.4.1.3**: Avoid extracting black/transition frames
- **FR-2.4.1.4**: Compress frames for efficient API transmission
- **FR-2.4.1.5**: Support configurable extraction rate

**Configuration**:

```python
{
    "frames_per_scene": 3,          # keyframes per scene
    "interval_frames": 5,           # additional frames per N seconds
    "output_format": "jpeg",
    "quality": 85,
    "max_dimension": 1024
}
```

##### 2.4.2 GPT-4o Vision Analysis

**Purpose**: Analyze extracted frames to verify and enrich scene content

**Requirements**:

- **FR-2.4.2.1**: Send frames to GPT-4o Vision API
- **FR-2.4.2.2**: Describe visual content of each scene
- **FR-2.4.2.3**: Identify characters, actions, and settings
- **FR-2.4.2.4**: Flag potentially sensitive visual content
- **FR-2.4.2.5**: Cross-reference with script descriptions
- **FR-2.4.2.6**: Generate confidence adjustment scores

**Prompt Template**:

```
Analyze these frames from a movie scene and provide:
1. Visual description of what's happening
2. Characters visible (describe if names unknown)
3. Setting/location
4. Any potentially sensitive content (violence, nudity, gore, etc.)
5. Emotional tone conveyed visually

Expected scene description from script: {script_summary}

Rate how well the visual content matches the script description (0-1).
```

**Output**:

```json
{
  "scene_id": 1,
  "visual_description": "A man in a suit enters a busy coffee shop...",
  "characters_visible": ["man in suit", "barista", "customers"],
  "setting": "modern coffee shop interior",
  "sensitive_content": {
    "violence": false,
    "nudity": false,
    "gore": false,
    "substances": true,
    "details": "Alcohol bottles visible in background"
  },
  "emotional_tone": "casual, slightly anxious",
  "script_match_score": 0.88
}
```

---

#### 2.5 Merge & Score Module

##### 2.5.1 Data Merger

**Purpose**: Combine all data sources into unified segment records

**Requirements**:

- **FR-2.5.1.1**: Merge aligned script data with video scene data
- **FR-2.5.1.2**: Incorporate visual analysis results
- **FR-2.5.1.3**: Include external content advisory data
- **FR-2.5.1.4**: Resolve conflicts between data sources
- **FR-2.5.1.5**: Preserve all source attributions

##### 2.5.2 Confidence Scorer

**Purpose**: Calculate overall confidence scores for segment data quality

**Requirements**:

- **FR-2.5.2.1**: Weight confidence based on data source reliability
- **FR-2.5.2.2**: Factor in alignment match quality
- **FR-2.5.2.3**: Consider visual verification scores
- **FR-2.5.2.4**: Flag low-confidence segments for manual review
- **FR-2.5.2.5**: Generate data quality report

**Confidence Calculation**:

```
confidence = (
    subtitle_match_weight * subtitle_confidence +
    script_match_weight * script_alignment_confidence +
    visual_match_weight * visual_verification_score +
    external_data_weight * external_data_confidence
) / total_weight
```

---

### Final Output Schema

#### segments.json

```json
{
  "movie_info": {
    "title": "Example Movie",
    "duration_sec": 7200,
    "total_segments": 145,
    "processing_timestamp": "2026-01-24T10:30:00Z"
  },
  "segments": [
    {
      "segment_id": 1,
      "video_data": {
        "start_time": "00:00:00.000",
        "end_time": "00:01:23.456",
        "start_ms": 0,
        "end_ms": 83456,
        "duration_sec": 83.456
      },
      "script_data": {
        "scene_numbers": [1],
        "heading": "INT. COFFEE SHOP - DAY",
        "summary": "John enters a coffee shop looking for Sarah.",
        "characters": ["JOHN"],
        "dialogue": [
          {
            "character": "JOHN",
            "text": "Have you seen Sarah?",
            "timestamp": "00:01:23.456"
          }
        ],
        "actions": ["enters", "scans room"]
      },
      "visual_analysis": {
        "description": "A man in a suit enters a busy coffee shop...",
        "setting": "modern coffee shop interior",
        "characters_visible": ["man in suit", "barista"],
        "emotional_tone": "anxious"
      },
      "content_flags": {
        "violence": {
          "detected": false,
          "severity": null,
          "description": null
        },
        "sexual_content": {
          "detected": false,
          "severity": null,
          "description": null
        },
        "profanity": {
          "detected": false,
          "severity": null,
          "description": null,
          "instances": []
        },
        "substances": {
          "detected": true,
          "severity": "low",
          "description": "Alcohol bottles visible in background"
        },
        "frightening": {
          "detected": false,
          "severity": null,
          "description": null
        }
      },
      "confidence": {
        "overall": 0.91,
        "subtitle_alignment": 0.95,
        "script_alignment": 0.88,
        "visual_verification": 0.9
      },
      "sources": {
        "subtitles": true,
        "script": true,
        "imdb_parent_guide": true,
        "kids_in_mind": true,
        "visual_analysis": true
      }
    }
  ],
  "metadata": {
    "external_data": {
      "imdb_id": "tt1234567",
      "imdb_parent_guide_fetched": true,
      "kids_in_mind_fetched": true
    },
    "processing_stats": {
      "total_video_scenes_detected": 156,
      "total_script_scenes": 142,
      "successful_alignments": 139,
      "low_confidence_segments": 6,
      "processing_time_sec": 1847
    }
  }
}
```

---

## Technical Stack

### Recommended Technologies

| Component        | Technology              | Purpose                              |
| ---------------- | ----------------------- | ------------------------------------ |
| Scene Detection  | PySceneDetect           | Video scene boundary detection       |
| Video Processing | FFmpeg, OpenCV          | Frame extraction, video manipulation |
| LLM Integration  | OpenAI GPT-4o           | Script analysis, visual verification |
| Subtitle Parsing | pysrt, webvtt-py        | Parse subtitle formats               |
| Text Matching    | rapidfuzz, difflib      | Fuzzy string matching for alignment  |
| Web Scraping     | BeautifulSoup, requests | Fetch external data                  |
| Data Storage     | JSON, SQLite            | Segment data persistence             |
| API Framework    | FastAPI                 | Backend API services                 |
| Video Generation | Runway, Pika Labs       | AI scene generation (Stage 4)        |

### Python Dependencies

```
# Core Processing
pyscenedetect>=0.6
opencv-python>=4.8
ffmpeg-python>=0.2

# Subtitle Processing
pysrt>=1.1
webvtt-py>=0.4

# Text Processing
rapidfuzz>=3.0
spacy>=3.7

# LLM Integration
openai>=1.0

# Web Scraping
beautifulsoup4>=4.12
requests>=2.31

# API
fastapi>=0.100
uvicorn>=0.23

# Utilities
pydantic>=2.0
python-dotenv>=1.0
```

---

## Non-Functional Requirements

### Performance

- **NFR-1**: Process a 2-hour movie within 30 minutes
- **NFR-2**: Support videos up to 4K resolution
- **NFR-3**: Handle files up to 50GB in size

### Scalability

- **NFR-4**: Support concurrent processing of multiple movies
- **NFR-5**: Horizontal scaling for processing workers

### Reliability

- **NFR-6**: Resume processing from checkpoints on failure
- **NFR-7**: 99.5% uptime for API services

### Security

- **NFR-8**: Encrypt user uploaded content at rest
- **NFR-9**: Secure API authentication
- **NFR-10**: GDPR compliance for user data

---

## Future Considerations

1. **Real-time Processing**: Stream-based filtering for live content
2. **Custom Training**: Allow users to train personal filtering preferences
3. **Multi-language Support**: Support subtitles and scripts in multiple languages
4. **Mobile Apps**: iOS and Android applications for on-the-go viewing
5. **Browser Extension**: Filter streaming content in real-time
6. **Community Ratings**: Crowdsourced content flagging and verification

---

## Revision History

| Version | Date       | Author | Changes                       |
| ------- | ---------- | ------ | ----------------------------- |
| 1.0     | 2026-01-24 | -      | Initial requirements document |
