"""
SRT Subtitle Parser Module

Parses .srt subtitle files into structured data with timestamps.
"""

import re
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class SubtitleEntry:
    """Represents a single subtitle entry."""
    index: int
    start_time: str
    end_time: str
    start_ms: int
    end_ms: int
    text: str
    
    def to_dict(self) -> dict:
        return asdict(self)


def time_to_ms(time_str: str) -> int:
    """
    Convert SRT timestamp to milliseconds.
    
    Args:
        time_str: Time in format "HH:MM:SS,mmm" or "HH:MM:SS.mmm"
    
    Returns:
        Time in milliseconds
    """
    # Handle both comma and period as decimal separator
    time_str = time_str.replace(',', '.')
    
    # Parse components
    match = re.match(r'(\d{1,2}):(\d{2}):(\d{2})\.(\d{3})', time_str)
    if not match:
        raise ValueError(f"Invalid time format: {time_str}")
    
    hours, minutes, seconds, ms = map(int, match.groups())
    
    return (hours * 3600 + minutes * 60 + seconds) * 1000 + ms


def ms_to_time(ms: int) -> str:
    """
    Convert milliseconds to SRT timestamp format.
    
    Args:
        ms: Time in milliseconds
    
    Returns:
        Time in format "HH:MM:SS,mmm"
    """
    hours = ms // 3600000
    ms %= 3600000
    minutes = ms // 60000
    ms %= 60000
    seconds = ms // 1000
    milliseconds = ms % 1000
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def clean_subtitle_text(text: str) -> str:
    """
    Clean subtitle text by removing HTML tags and normalizing whitespace.
    
    Args:
        text: Raw subtitle text
    
    Returns:
        Cleaned text
    """
    # Remove HTML tags (e.g., <i>, </i>, <b>, </b>)
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove speaker indicators like "- " at start of lines
    text = re.sub(r'^- ', '', text, flags=re.MULTILINE)
    
    # Normalize whitespace (collapse multiple spaces/newlines)
    text = ' '.join(text.split())
    
    # Remove common subtitle artifacts
    text = re.sub(r'\[.*?\]', '', text)  # [music playing], [sighs], etc.
    text = re.sub(r'\(.*?\)', '', text)  # (laughs), (crying), etc.
    
    return text.strip()


def parse_srt(filepath: str | Path) -> list[SubtitleEntry]:
    """
    Parse an SRT subtitle file into a list of SubtitleEntry objects.
    
    Args:
        filepath: Path to the .srt file
    
    Returns:
        List of SubtitleEntry objects
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
    
    entries = []
    
    # SRT format: index, timestamp line, text (possibly multi-line), blank line
    # Split by double newlines (handling both \n\n and \r\n\r\n)
    blocks = re.split(r'\n\s*\n', content.strip())
    
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        
        lines = block.split('\n')
        if len(lines) < 2:
            continue
        
        # First line should be the index
        try:
            index = int(lines[0].strip())
        except ValueError:
            continue
        
        # Second line should be the timestamp
        timestamp_match = re.match(
            r'(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})',
            lines[1].strip()
        )
        
        if not timestamp_match:
            continue
        
        start_time = timestamp_match.group(1)
        end_time = timestamp_match.group(2)
        
        # Remaining lines are the subtitle text
        text = '\n'.join(lines[2:])
        
        # Skip metadata entries (like "Subtitles downloaded from...")
        if 'subtitle' in text.lower() and ('download' in text.lower() or 'http' in text.lower()):
            continue
        
        entry = SubtitleEntry(
            index=index,
            start_time=start_time.replace('.', ','),
            end_time=end_time.replace('.', ','),
            start_ms=time_to_ms(start_time),
            end_ms=time_to_ms(end_time),
            text=text.strip()
        )
        
        entries.append(entry)
    
    return entries


def get_cleaned_entries(filepath: str | Path) -> list[SubtitleEntry]:
    """
    Parse SRT and return entries with cleaned text.
    
    Args:
        filepath: Path to the .srt file
    
    Returns:
        List of SubtitleEntry objects with cleaned text
    """
    entries = parse_srt(filepath)
    
    cleaned = []
    for entry in entries:
        cleaned_text = clean_subtitle_text(entry.text)
        if cleaned_text:  # Only include non-empty entries
            cleaned.append(SubtitleEntry(
                index=entry.index,
                start_time=entry.start_time,
                end_time=entry.end_time,
                start_ms=entry.start_ms,
                end_ms=entry.end_ms,
                text=cleaned_text
            ))
    
    return cleaned
