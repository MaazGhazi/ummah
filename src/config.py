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


# Vision analysis prompt - Halal content detection for Islamic viewing
VISION_PROMPT = """Analyze these frames from a movie scene for content that violates Islamic (halal) viewing guidelines.

You are helping Muslims identify scenes to skip or replace to make movies family-appropriate according to Islamic principles.

## CONTENT TO DETECT (in order of severity):

**HARAM (Must Skip/Replace):**
- Any kissing between a man and woman (including brief pecks)
- Hugging or embracing between non-mahram (unmarried/unrelated) couples
- Physical touching with romantic/intimate intent
- Couples lying together or in bed
- Nudity of any kind (exposed awrah)
- Revealing clothing: low-cut tops, short skirts, tight clothing emphasizing body
- Swimwear, lingerie, or underwear scenes
- Sensual dancing or suggestive movements
- Seductive poses or behavior

**ALSO FLAG:**
- Romantic hand-holding or close physical proximity with romantic undertones
- Women without proper hijab in intimate/romantic contexts
- Scenes implying intimacy (before/after bedroom scenes)

## SCORING (haram_score):
- 0.0-0.2: Halal - No issues (modest clothing, no physical contact between genders)
- 0.3-0.4: Questionable - Brief hand-holding, standing close, romantic gazes
- 0.5-0.6: Mild haram - Kissing, embracing, revealing clothing
- 0.7-0.8: Moderate haram - Extended kissing, bed scenes (clothed), immodest dress
- 0.9-1.0: Severe haram - Nudity, sexual content, explicit scenes

## SCENE DESCRIPTION:
Describe EXACTLY what is happening: Who is present? What are they doing? What are they wearing? Where are they? Be specific so the user knows exactly what to expect.

Respond with ONLY a JSON object (no markdown):
{
    "haram_score": 0.0,
    "severity": "halal|questionable|mild|moderate|severe",
    "scene_description": "Detailed description: A man and woman are standing at the bow of a ship. She wears a low-cut dress. He stands behind her with his arms around her waist. They appear to be a romantic couple.",
    "issues_detected": ["embracing", "romantic_contact", "revealing_clothing"],
    "replacement_suggestion": "skip|blur_scene|audio_only|cut_segment",
    "confidence": 0.0
}

ISSUES CATEGORIES: kissing, embracing, hand_holding, romantic_contact, bed_scene, nudity, partial_nudity, revealing_clothing, suggestive_dancing, suggestive_pose, intimate_proximity

REPLACEMENT SUGGESTIONS:
- "skip": Completely skip this segment (severe content)
- "blur_scene": Blur the video but keep audio (moderate content)  
- "audio_only": Black screen with audio (visual issues only)
- "cut_segment": Remove entirely including audio (explicit content)

Be STRICT - when in doubt, flag it. It's better to flag something questionable than to miss haram content.
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
