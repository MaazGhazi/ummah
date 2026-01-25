"""Configuration and environment loading."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def get_openai_key() -> str:
    """Get OpenAI API key from environment."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError(
            "OPENAI_API_KEY not set. "
            "Either set it as an environment variable or create a .env file."
        )
    return key


def get_fal_key() -> str:
    """Get fal.ai API key from environment."""
    key = os.environ.get("FAL_KEY")
    if not key:
        raise ValueError(
            "FAL_KEY not set. "
            "Either set it as an environment variable or create a .env file."
        )
    return key


# Vision analysis prompt - Halal content detection for Islamic viewing
VISION_PROMPT = """Analyze these frames from a movie scene for sexual activity, nudity, or intimate behavior that should be flagged for families.

You are helping identify sexual or nude content that needs reviewing so it can be cut, blurred, or replaced.

## CONTENT TO DETECT (in order of severity):

**SEVERE (must block or remove):**
- Explicit nudity (full or partial exposure of genitals, buttocks, or bare breasts)
- Graphic sexual activity (intercourse, simulated sex, oral/anal)
- Full-body contact with clear sexual intent (couples in bed, sexual positions)

**MODERATE (blur, audio-only, or cut):**
- Kissing or embracing that is prolonged or part of a romantic bedroom-type scene
- Bodies touching with clear erotic intent (heavy petting, suggestive touching)
- Revealing clothing that exposes intimate areas (lingerie, swimwear, see-through fabric)
- Sensual dancing or seductive movement

**MILD (warning-level scrutiny):**
- Brief kisses or romantic holding without explicit sexual intent
- Close physical proximity with suggestive body language
- Suggestive poses or implied intimacy (e.g., undressing but not nude)

## SCORING (haram_score):
- 0.0-0.2: Clean - No sexual activity or nudity detected
- 0.3-0.4: Mild - Brief romantic cues, suggestive posture, or partially covered skin
- 0.5-0.6: Moderate - Overt romantic contact, revealing clothing, implied sensuality
- 0.7-0.8: Heavy - Prolonged kissing, petting, sensual movement, or revealing bodies
- 0.9-1.0: Severe - Nudity, explicit sex, or graphic erotic content

## SCENE DESCRIPTION:
Describe exactly what is happening: who is present, what they are doing, how they are dressed, and anything that signals sexual intent or nudity. Be specific so the requester can preview the risk.

Respond with ONLY a JSON object (no markdown):
{
    "haram_score": 0.0,
    "severity": "clean|mild|moderate|heavy|severe",
    "scene_description": "Detailed description of the activity, clothing, and proximity.",
    "issues_detected": ["kissing", "nudity", "sexual_activity"],
    "replacement_suggestion": "skip|blur_scene|audio_only|cut_segment",
    "confidence": 0.0
}

ISSUES CATEGORIES: kissing, embracing, sexual_activity, nudity, partial_nudity, revealing_clothing, swimwear, bikini, shirtless, suggestive_dancing, intimate_touching, explicit_language, bed_scene, lingerie, bathing

REPLACEMENT SUGGESTIONS:
- "skip": Remove the scene entirely (explicit content)
- "blur_scene": Keep audio but blur the video (moderate content)
- "audio_only": Show black or neutral visuals while preserving audio (visual only issues)
- "cut_segment": Remove both audio and visual (strong explicit content)

Be precise—if it looks sexual or exposes nudity, flag it. Better to over-report than to miss a risky moment.
"""


# Detailed analysis prompt for second-pass timing refinement
DETAILED_TIMING_PROMPT = """You are analyzing individual frames to find the EXACT moments where haram content starts and ends.

For each frame, report:
1. Frame number (provided)
2. Is there haram content visible? (yes/no)
3. What specific issue is visible?

This helps identify precise timestamps for editing.

Respond with ONLY a JSON array:
[
    {"frame": 1, "has_issue": true, "issue": "couple embracing"},
    {"frame": 2, "has_issue": true, "issue": "kissing"},
    {"frame": 3, "has_issue": false, "issue": null}
]
"""
