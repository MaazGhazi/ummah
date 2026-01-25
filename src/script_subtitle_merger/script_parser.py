"""
Screenplay Script Parser Module

Parses movie scripts in standard screenplay format to extract:
- Scene headings (INT./EXT. locations)
- Character names and dialogue
- Action/description lines
"""

import re
from dataclasses import dataclass, asdict, field
from pathlib import Path
from enum import Enum


class ElementType(Enum):
    """Types of screenplay elements."""
    SCENE_HEADING = "scene_heading"
    CHARACTER = "character"
    DIALOGUE = "dialogue"
    PARENTHETICAL = "parenthetical"
    ACTION = "action"
    TRANSITION = "transition"


@dataclass
class ScriptElement:
    """Represents a single element from the screenplay."""
    element_type: str
    text: str
    scene_number: int
    character: str | None = None
    raw_text: str = ""
    
    def to_dict(self) -> dict:
        return {
            "element_type": self.element_type,
            "text": self.text,
            "scene_number": self.scene_number,
            "character": self.character,
        }


@dataclass
class ScriptScene:
    """Represents a complete scene with all its elements."""
    scene_number: int
    heading: str
    location: str
    time_of_day: str
    interior: bool
    elements: list[ScriptElement] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "scene_number": self.scene_number,
            "heading": self.heading,
            "location": self.location,
            "time_of_day": self.time_of_day,
            "interior": self.interior,
            "elements": [e.to_dict() for e in self.elements],
        }
    
    def get_dialogue(self) -> list[dict]:
        """Get all dialogue in this scene."""
        return [
            {"character": e.character, "text": e.text}
            for e in self.elements
            if e.element_type == ElementType.DIALOGUE.value
        ]
    
    def get_action_summary(self) -> str:
        """Get combined action/description text."""
        actions = [
            e.text for e in self.elements
            if e.element_type == ElementType.ACTION.value
        ]
        return " ".join(actions)


def clean_html_tags(text: str) -> str:
    """Remove HTML formatting tags from text."""
    # Remove <b>, </b>, <pre>, </pre>, etc.
    text = re.sub(r'</?[a-zA-Z]+[^>]*>', '', text)
    return text


def is_scene_heading(line: str) -> bool:
    """
    Check if a line is a scene heading.
    
    Scene headings typically start with INT., EXT., INT./EXT., etc.
    """
    line = line.strip()
    # Common scene heading patterns
    patterns = [
        r'^(INT\.|EXT\.|INT/EXT\.|INT\./EXT\.|I/E\.)',  # Standard
        r'^\d+\s+(INT\.|EXT\.)',  # With scene number prefix
    ]
    return any(re.match(p, line, re.IGNORECASE) for p in patterns)


def is_character_name(line: str, next_line: str | None = None) -> bool:
    """
    Check if a line is a character name (speaker cue).
    
    Character names are typically:
    - ALL CAPS
    - Centered or indented
    - May have (V.O.), (O.S.), (CONT'D), etc.
    """
    line = line.strip()
    
    # Skip empty lines
    if not line:
        return False
    
    # Remove parentheticals for checking
    name_part = re.sub(r'\(.*?\)', '', line).strip()
    
    # Skip if too long (character names are short)
    if len(name_part) > 40:
        return False
    
    # Skip common non-character patterns
    skip_patterns = [
        r'^(INT\.|EXT\.|CUT TO|FADE|DISSOLVE|THE END)',
        r'^\d+\s*$',  # Just numbers
        r'^(CONTINUED|CONT\'D)$',
    ]
    if any(re.match(p, line, re.IGNORECASE) for p in skip_patterns):
        return False
    
    # Character name should be mostly uppercase
    if name_part and name_part.isupper():
        # Additional check: next line should look like dialogue (if provided)
        if next_line:
            next_stripped = next_line.strip()
            # Dialogue is usually not all caps and not a scene heading
            if next_stripped and not next_stripped.isupper() and not is_scene_heading(next_stripped):
                return True
        else:
            return True
    
    return False


def is_parenthetical(line: str) -> bool:
    """Check if line is a parenthetical direction."""
    line = line.strip()
    return bool(re.match(r'^\(.*\)$', line))


def is_transition(line: str) -> bool:
    """Check if line is a transition."""
    line = line.strip().upper()
    transitions = [
        'CUT TO:', 'FADE TO:', 'FADE IN:', 'FADE OUT.', 'FADE OUT:',
        'DISSOLVE TO:', 'SMASH CUT:', 'MATCH CUT:', 'JUMP CUT:',
        'TIME CUT:', 'FADE TO BLACK.', 'THE END'
    ]
    return any(line.startswith(t) or line == t.rstrip(':') for t in transitions)


def parse_scene_heading(line: str) -> tuple[str, str, bool]:
    """
    Parse a scene heading into location and time of day.
    
    Returns:
        (location, time_of_day, is_interior)
    """
    line = clean_html_tags(line).strip()
    
    # Remove scene numbers if present (e.g., "1   INT. ROOM - DAY   1")
    line = re.sub(r'^\d+\s+', '', line)
    line = re.sub(r'\s+\d+$', '', line)
    
    # Determine interior/exterior
    is_interior = line.upper().startswith('INT')
    
    # Extract location and time
    # Format: INT./EXT. LOCATION - TIME OF DAY
    match = re.match(
        r'^(?:INT\.?/?|EXT\.?/?|INT\.?/EXT\.?|I/E\.?)\s*(.+?)(?:\s*-\s*(.+))?$',
        line,
        re.IGNORECASE
    )
    
    if match:
        location = match.group(1).strip()
        time_of_day = match.group(2).strip() if match.group(2) else "UNKNOWN"
    else:
        location = line
        time_of_day = "UNKNOWN"
    
    return location, time_of_day, is_interior


def parse_script(filepath: str | Path) -> list[ScriptScene]:
    """
    Parse a screenplay file into structured scenes.
    
    Args:
        filepath: Path to the script file
    
    Returns:
        List of ScriptScene objects
    """
    filepath = Path(filepath)
    
    # Try different encodings
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
    content = None
    
    for encoding in encodings:
        try:
            content = filepath.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    
    if content is None:
        raise ValueError(f"Could not decode file with any of: {encodings}")
    
    # Clean HTML tags from the entire content first
    content = clean_html_tags(content)
    
    # Split into lines
    lines = content.split('\n')
    
    scenes = []
    current_scene: ScriptScene | None = None
    current_character: str | None = None
    current_scene_num = 0
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            current_character = None  # Reset character on blank line
            i += 1
            continue
        
        # Skip page numbers and headers (e.g., "Pink (9/10/2013)   5")
        if re.match(r'^(Pink|Blue|Yellow|White|Green)\s*\(\d+/\d+/\d+\)\s*\d*$', stripped, re.IGNORECASE):
            i += 1
            continue
        
        # Check for scene heading
        if is_scene_heading(stripped):
            current_scene_num += 1
            location, time_of_day, is_interior = parse_scene_heading(stripped)
            
            current_scene = ScriptScene(
                scene_number=current_scene_num,
                heading=stripped,
                location=location,
                time_of_day=time_of_day,
                interior=is_interior,
                elements=[]
            )
            scenes.append(current_scene)
            current_character = None
            i += 1
            continue
        
        # Check for transition
        if is_transition(stripped):
            i += 1
            continue
        
        # Get next non-empty line for context
        next_line = None
        for j in range(i + 1, min(i + 5, len(lines))):
            if lines[j].strip():
                next_line = lines[j]
                break
        
        # Check for character name
        if is_character_name(stripped, next_line):
            # Extract character name (remove parentheticals like (V.O.), (CONT'D))
            char_name = re.sub(r'\s*\(.*?\)\s*', '', stripped).strip()
            current_character = char_name
            i += 1
            continue
        
        # Check for parenthetical
        if is_parenthetical(stripped):
            if current_scene:
                current_scene.elements.append(ScriptElement(
                    element_type=ElementType.PARENTHETICAL.value,
                    text=stripped,
                    scene_number=current_scene_num,
                    character=current_character,
                    raw_text=line
                ))
            i += 1
            continue
        
        # If we have a current character, this is dialogue
        if current_character:
            if current_scene:
                current_scene.elements.append(ScriptElement(
                    element_type=ElementType.DIALOGUE.value,
                    text=stripped,
                    scene_number=current_scene_num,
                    character=current_character,
                    raw_text=line
                ))
            i += 1
            continue
        
        # Otherwise, it's action/description
        if current_scene and stripped:
            # Check if it's not just whitespace or formatting
            if not re.match(r'^[\s\*\-\_]+$', stripped):
                current_scene.elements.append(ScriptElement(
                    element_type=ElementType.ACTION.value,
                    text=stripped,
                    scene_number=current_scene_num,
                    character=None,
                    raw_text=line
                ))
        
        i += 1
    
    return scenes


def get_all_dialogue(scenes: list[ScriptScene]) -> list[dict]:
    """
    Extract all dialogue from parsed scenes.
    
    Returns:
        List of {scene_number, character, text, scene_heading}
    """
    dialogue_list = []
    
    for scene in scenes:
        for element in scene.elements:
            if element.element_type == ElementType.DIALOGUE.value:
                dialogue_list.append({
                    "scene_number": scene.scene_number,
                    "scene_heading": scene.heading,
                    "character": element.character,
                    "text": element.text,
                })
    
    return dialogue_list


def get_scene_by_number(scenes: list[ScriptScene], scene_num: int) -> ScriptScene | None:
    """Get a scene by its number."""
    for scene in scenes:
        if scene.scene_number == scene_num:
            return scene
    return None
