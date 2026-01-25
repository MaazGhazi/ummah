import whisper
import os
import sys


def format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(segments: list) -> str:
    """Convert whisper segments to SRT format"""
    srt_content = []
    for i, segment in enumerate(segments, start=1):
        start_time = format_timestamp(segment['start'])
        end_time = format_timestamp(segment['end'])
        text = segment['text'].strip()
        srt_content.append(f"{i}\n{start_time} --> {end_time}\n{text}\n")
    return "\n".join(srt_content)


def transcribe_audio(audio_path: str, model_name: str = "base") -> str:
    """
    Transcribe an audio file and return SRT content.
    
    Args:
        audio_path: Path to the MP3 audio file
        model_name: Whisper model to use (tiny, base, small, medium, large)
    
    Returns:
        SRT formatted string
    """
    print(f"Loading Whisper model: {model_name}")
    model = whisper.load_model(model_name)
    
    print(f"Transcribing: {audio_path}")
    result = model.transcribe(audio_path)
    
    return generate_srt(result['segments'])


def save_srt(srt_content: str, output_path: str) -> None:
    """Save SRT content to a file"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(srt_content)
    print(f"SRT file saved to: {output_path}")


def main(audio_path: str, output_path: str = None, model_name: str = "base"):
    """
    Main function to generate subtitles from an audio file.
    
    Args:
        audio_path: Path to the input MP3 file
        output_path: Path for the output SRT file (optional)
        model_name: Whisper model to use
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    if output_path is None:
        output_path = os.path.splitext(audio_path)[0] + ".srt"
    
    srt_content = transcribe_audio(audio_path, model_name)
    save_srt(srt_content, output_path)
    
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generating_subtitles.py <audio_file> [output_file.srt] [model_name]")
        print("Models: tiny, base, small, medium, large")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    model = sys.argv[3] if len(sys.argv) > 3 else "base"
    
    main(audio_file, output_file, model)
