"""Utilities to extract audio from video files.

This module provides a single high-level function `extract_audio_from_mp4` which
prefers to use MoviePy (which downloads/uses ffmpeg binaries via imageio-ffmpeg)
and falls back to calling the `ffmpeg` executable if MoviePy isn't available.

The function returns the path to the written audio file.

Usage (programmatic):
    from extract_audio import extract_audio_from_mp4
    out = extract_audio_from_mp4("input.mp4")

Usage (CLI):
    python extract_audio.py input.mp4 --output audio.wav

Notes:
 - Default output format is .wav (uncompressed PCM 16-bit, 44.1kHz, stereo).
 - If you want MP3 or another format, provide an output filename with that
   extension (e.g. .mp3). MoviePy/ffmpeg will try to encode accordingly.
 - If MoviePy is not installed, this library requires the `ffmpeg` binary to be
   available on PATH.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _ensure_output_path(input_path: Path, output_path: Optional[Path]) -> Path:
    if output_path is None:
        return input_path.with_suffix(".wav")
    return output_path


def extract_audio_from_mp4(
    input_mp4: str | Path,
    output_audio: Optional[str | Path] = None,
    *,
    wav_rate: int = 44100,
    channels: int = 2,
) -> Path:
    """Extract audio from an MP4 file and write an audio file.

    The function tries MoviePy first (recommended). If MoviePy is not
    available it will fall back to invoking the `ffmpeg` binary.

    Args:
        input_mp4: Path to the input MP4 file.
        output_audio: Optional path for the resulting audio file. If omitted
                      the same filename with a .wav extension is used.
        wav_rate: Sample rate to use for WAV output (used by fallback ffmpeg
                  and by MoviePy parameters when writing WAV).
        channels: Number of audio channels (1 = mono, 2 = stereo).

    Returns:
        Path to the written audio file.

    Raises:
        FileNotFoundError: if the input file doesn't exist.
        RuntimeError: if extraction fails or ffmpeg is not available.
    """
    input_path = Path(input_mp4)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_path = _ensure_output_path(input_path, Path(output_audio) if output_audio else None)

    # Try MoviePy first (it manages ffmpeg binary via imageio-ffmpeg)
    try:
        # Import the concrete VideoFileClip implementation directly. Newer
        # moviepy packages expose VideoFileClip under moviepy.video.io.VideoFileClip
        # and some installs may not provide the legacy `moviepy.editor` package
        # symbol, so import explicitly to be robust.
        from moviepy.video.io.VideoFileClip import VideoFileClip

        logger.info("Using MoviePy to extract audio from %s", input_path)
        with VideoFileClip(str(input_path)) as clip:
            if clip.audio is None:
                raise RuntimeError("No audio track found in the input video")
            # moviepy autodetects format from extension. For WAV we can force fps and
            # buffersize via write_audiofile parameters.
            clip.audio.write_audiofile(
                str(output_path), fps=wav_rate, nbytes=2, ffmpeg_params=["-ac", str(channels)]
            )

        logger.info("Audio written to %s", output_path)
        return output_path
    except Exception as e:  # pylint: disable=broad-except
        # If MoviePy isn't present or failed, fallback to ffmpeg binary
        logger.debug("MoviePy extraction failed: %s", e)

    # Fallback: call ffmpeg executable
    ffmpeg_cmd = shutil.which("ffmpeg")
    if not ffmpeg_cmd:
        raise RuntimeError("MoviePy not available and ffmpeg executable not found on PATH")

    # Construct ffmpeg arguments
    # -y overwrite, -i input, -vn no video, -ac channels, -ar sample rate, -f format auto
    args = [
        ffmpeg_cmd,
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-ac",
        str(channels),
        "-ar",
        str(wav_rate),
    ]

    # If output extension is .wav, explicitly request pcm_s16le
    if output_path.suffix.lower() == ".wav":
        args += ["-acodec", "pcm_s16le", str(output_path)]
    else:
        # Let ffmpeg choose codec for other extensions (mp3, m4a, etc.)
        args += [str(output_path)]

    logger.info("Running ffmpeg fallback: %s", " ".join(args))
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.error("ffmpeg failed: %s", proc.stderr)
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.strip()}")

    logger.info("Audio written to %s (ffmpeg)", output_path)
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract audio from an MP4 file")
    parser.add_argument("input", help="Input MP4 file")
    parser.add_argument("-o", "--output", help="Output audio file (optional)")
    parser.add_argument("--rate", type=int, default=44100, help="Sample rate for WAV output")
    parser.add_argument("--channels", type=int, default=2, help="Number of channels (1 or 2)")
    args = parser.parse_args()

    out = extract_audio_from_mp4(args.input, args.output, wav_rate=args.rate, channels=args.channels)
    print(out)
