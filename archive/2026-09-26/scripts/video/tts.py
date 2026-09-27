"""Generate one narration clip per scene with Gemini TTS. Key from GEMINI_API_KEY in .env.

    python scripts/video/tts.py            # all scenes
    python scripts/video/tts.py numbers outro
"""
import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()
MODEL = os.environ.get("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
VOICE = os.environ.get("GEMINI_TTS_VOICE", "Charon")
OUT = Path("run/video/voice")


def _post(text: str) -> httpx.Response:
    return httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
        json={"contents": [{"parts": [{"text": text}]}],
              "generationConfig": {"responseModalities": ["AUDIO"],
                                   "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}}}},
        timeout=90)


def synth(text: str, path: Path) -> float:
    for _ in range(6):
        r = _post(text)
        if r.status_code != 429:
            break
        print("  rate limited, waiting 20s", flush=True)
        time.sleep(20)
    r.raise_for_status()
    raw = path.with_suffix(".raw.wav")
    raw.write_bytes(base64.b64decode(r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]))
    # trim leading and trailing silence, normalize to 48 kHz stereo
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-af",
                    "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                    "silenceremove=start_periods=1:start_threshold=-45dB,areverse",
                    "-ar", "48000", "-ac", "2", str(path)], check=True)
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True)
    return float(out.stdout)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[1:])
    path = OUT / "durations.json"
    durations = json.loads(path.read_text()) if path.exists() else {}
    for seg in json.loads(Path("scripts/video/narration.json").read_text()):
        if only and seg["id"] not in only:
            continue
        durations[seg["id"]] = round(synth(seg["text"], OUT / f"{seg['id']}.wav"), 2)
        print(seg["id"], durations[seg["id"]], "s", flush=True)
        path.write_text(json.dumps(durations, indent=1))
    print("total", round(sum(durations.values()), 2), "s")
