from typing import List, Tuple, Optional, Callable, Union
from pydub import AudioSegment, effects

def _load_audio(audio_input: Union[str, AudioSegment]) -> AudioSegment:
    """Load audio from a path or return the provided AudioSegment.

    Args:
        audio_input: Path to an audio file or an AudioSegment instance.

    Returns:
        AudioSegment: the loaded audio.
    """
    if isinstance(audio_input, AudioSegment):
        return audio_input
    if isinstance(audio_input, str):
        return AudioSegment.from_file(audio_input)
    raise TypeError("audio_input must be a file path or pydub.AudioSegment")


def _timestamps_from_profanity_timestamps(profanity_timestamps: List[Tuple[float, float]]) -> List[Tuple[int, int]]:
    return [(int(s * 1000), int(e * 1000)) for s, e in profanity_timestamps]


def _timestamps_from_transcript(transcript_fn: Callable[[str], List[Tuple[str, float, float]]], audio_path: str, profanity_words: List[str]) -> List[Tuple[int, int]]:
    intervals_ms: List[Tuple[int, int]] = []
    transcripts = transcript_fn(audio_path)
    for word, start_s, end_s in transcripts:
        if word.lower() in profanity_words:
            intervals_ms.append((int(start_s * 1000), int(end_s * 1000)))
    return intervals_ms


def _merge_intervals_ms(intervals_ms: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if not intervals_ms:
        return []
    intervals_ms.sort()
    merged: List[Tuple[int, int]] = []
    cur_s, cur_e = intervals_ms[0]
    for s, e in intervals_ms[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e)
        else:
            merged.append((cur_s, cur_e))
            cur_s, cur_e = s, e
    merged.append((cur_s, cur_e))
    return merged


def silence_profanity(
    audio_input: Union[str, AudioSegment],
    profanity_timestamps: Optional[List[Tuple[float, float]]] = None,
    profanity_words: Optional[List[str]] = None,
    transcript_fn: Optional[Callable[[str], List[Tuple[str, float, float]]]] = None,
    export_path: Optional[str] = None,
) -> AudioSegment:
    """Silence portions of the audio that contain profanity.

    This function does NOT perform automatic speech-to-text by itself. You can either
    supply profanity_timestamps (list of (start_sec, end_sec)) or provide a
    transcript_fn that, given a file path, returns a list of tuples (word, start_sec, end_sec).

    Args:
        audio_input: path to audio file or AudioSegment.
        profanity_timestamps: explicit list of (start_sec, end_sec) intervals to silence.
        profanity_words: optional list of lowercase words to treat as profanity if transcript_fn is used.
        transcript_fn: optional callback: (audio_path) -> list of (word, start_sec, end_sec).
        export_path: if provided, exports the cleaned audio to this path.

    Returns:
        AudioSegment: cleaned audio with silence inserted over profanity intervals.

    Notes:
        - If both profanity_timestamps and transcript_fn are provided, profanity_timestamps takes precedence.
        - Default profanity_words list is small and should be customized for your application and locale.
    """
    audio = _load_audio(audio_input)

    # Default short profanity list - replace with a more comprehensive list as needed
    default_profanity = [
        "fuck",
        "shit",
        "bitch",
        "asshole",
        "damn",
        "bastard",
        "crap",
    ]
    profanity_words = profanity_words or default_profanity

    intervals_ms: List[Tuple[int, int]] = []
    if profanity_timestamps:
        intervals_ms = _timestamps_from_profanity_timestamps(profanity_timestamps)
    elif transcript_fn and isinstance(audio_input, str):
        intervals_ms = _timestamps_from_transcript(transcript_fn, audio_input, profanity_words)
    else:
        return audio

    if not intervals_ms:
        return audio

    merged = _merge_intervals_ms(intervals_ms)

    out = AudioSegment.empty()
    last_pos = 0
    for s_ms, e_ms in merged:
        if s_ms > last_pos:
            out += audio[last_pos:s_ms]
        duration_ms = max(0, e_ms - s_ms)
        out += AudioSegment.silent(duration=duration_ms, frame_rate=audio.frame_rate)
        last_pos = e_ms
    if last_pos < len(audio):
        out += audio[last_pos:]

    out = effects.normalize(out)

    if export_path:
        out.export(export_path, format=export_path.split('.')[-1])
    return out


def remove_music(
    audio_input: Union[str, AudioSegment],
    method: str = "bandpass",
    voice_band: Tuple[int, int] = (300, 3000),
    export_path: Optional[str] = None,
) -> AudioSegment:
    """Attempt to remove or attenuate background music from an audio track.

    This is a heuristic implementation. True music/voice separation generally requires
    a source-separation model (spleeter, Demucs, or an ML model). This function uses
    a simple band-pass approach to preserve typical human voice frequencies and attenuate
    others, which often reduces music but is not perfect.

    Args:
        audio_input: path or AudioSegment.
        method: currently only 'bandpass' is implemented.
        voice_band: (low_hz, high_hz) band to preserve (defaults to typical speech band).
        export_path: optional path to export result.

    Returns:
        AudioSegment: processed audio with reduced out-of-band content.
    """
    audio = _load_audio(audio_input)

    if method != "bandpass":
        raise ValueError("Unsupported method. Only 'bandpass' is implemented.")

    low_hz, high_hz = voice_band
    # pydub provides simple filters
    processed = audio.high_pass_filter(low_hz).low_pass_filter(high_hz)

    # Optionally mix the processed (voice-focused) audio with a reduced-volume original
    # so voice remains prominent while keeping some naturalness. Here we return the
    # isolated bandpass result to make 'music' quieter.
    out = effects.normalize(processed)

    if export_path:
        out.export(export_path, format=export_path.split('.')[-1])
    return out