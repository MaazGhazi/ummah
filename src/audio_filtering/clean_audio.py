import subprocess
import whisper
from pydub import AudioSegment
from pathlib import Path


# =========================================================
# 1️⃣ Extract audio from mp4 using ffmpeg
# =========================================================
def extract_audio_from_mp4(mp4_path: str, wav_path: str):
    """
    Extracts mono wav audio from an mp4 file.
    Improves separation accuracy by converting to mono.
    """
    subprocess.run([
        "ffmpeg",
        "-y",                 # overwrite
        "-i", mp4_path,
        "-vn",                # no video
        "-ac", "1",           # mono
        "-ar", "16000",       # whisper friendly
        wav_path
    ], check=True)

    print(f"✅ Audio extracted → {wav_path}")


# =========================================================
# 2️⃣ Remove music using Demucs (keeps dialogue + SFX)
# =========================================================
def remove_music(input_wav: str, output_wav: str):
    """
    Uses Demucs 2-stem separation to keep vocals (speech/SFX)
    and remove instruments/music.
    """
    subprocess.run([
        "demucs",
        "--two-stems=vocals",
        "-n", "htdemucs",
        input_wav
    ], check=True)

    name = Path(input_wav).stem
    separated_path = Path("separated/htdemucs") / name / "vocals.wav"

    AudioSegment.from_file(separated_path).export(output_wav, format="wav")

    print(f"✅ Music removed → {output_wav}")


# =========================================================
# 3️⃣ Censor profanity using Whisper timestamps
# =========================================================
def censor_profanity(input_wav: str, output_wav: str, bad_words=None):
    """
    Silences profane words using Whisper word timestamps.
    """

    if bad_words is None:
        bad_words = {"damn", "shit", "fuck"}

    print("🧠 Transcribing with Whisper...")

    model = whisper.load_model("medium", device="mps")  # fast on Apple Silicon
    result = model.transcribe(input_wav, word_timestamps=True)

    audio = AudioSegment.from_file(input_wav)

    for segment in result["segments"]:
        for word in segment["words"]:
            text = word["word"].strip().lower()

            if any(bad in text for bad in bad_words):
                start = int(word["start"] * 1000)
                end = int(word["end"] * 1000)

                silence = AudioSegment.silent(duration=end - start).fade_in(5).fade_out(5)
                audio = audio[:start] + silence + audio[end:]

    audio.export(output_wav, format="wav")

    print(f"✅ Profanity censored → {output_wav}")

    return result  # return transcript for subtitles


# =========================================================
# 4️⃣ Optional helper: export subtitles
# =========================================================
def export_srt(result, srt_path: str):

    def fmt(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int((t - int(t)) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    with open(srt_path, "w") as f:
        for i, seg in enumerate(result["segments"], 1):
            f.write(f"{i}\n")
            f.write(f"{fmt(seg['start'])} --> {fmt(seg['end'])}\n")
            f.write(seg["text"].strip() + "\n\n")

    print(f"✅ Subtitles exported → {srt_path}")


# =========================================================
# 5️⃣ Example pipeline
# =========================================================
def process_movie(mp4_file: str):
    print(f"🎬 Processing movie: {mp4_file}\n")
    base = Path(mp4_file).stem

    raw_audio = f"{base}_raw.wav"
    vocals_audio = f"{base}_nomusic.wav"
    clean_audio = f"{base}_clean.wav"
    srt_file = f"{base}.srt"
    final_video = f"{base}_clean.mp4"

    extract_audio_from_mp4(mp4_file, raw_audio)
    remove_music(raw_audio, vocals_audio)
    result = censor_profanity(vocals_audio, clean_audio)
    export_srt(result, srt_file)

    # mux audio back into video
    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", mp4_file,
        "-i", clean_audio,
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-shortest",
        final_video
    ], check=True)

    print(f"\n🎉 Done → {final_video}")


# =========================================================
# Run from terminal
# =========================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python clean_audio.py movie.mp4")
    else:
        process_movie(sys.argv[1])