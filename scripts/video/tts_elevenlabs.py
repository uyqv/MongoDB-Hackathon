"""Narrate the whole video in one ElevenLabs read, with character timestamps.

    python scripts/video/tts_elevenlabs.py [voice_id]

One continuous generation keeps the delivery natural. The character alignment
then gives each scene's exact start and end, which edit.py uses to time the
footage. Writes run/video/voice/narration.wav and timeline.json.
Key: ELEVENLABS_API_KEY in .env.
"""
import base64
import json
import subprocess
import sys
from pathlib import Path

import httpx
from dotenv import dotenv_values

KEY = dotenv_values(".env")["ELEVENLABS_API_KEY"]
VOICE = sys.argv[1] if len(sys.argv) > 1 else "cjVigY5qzO86Huf0OWal"   # Eric: smooth, trustworthy
MODEL = "eleven_v3"
OUT = Path("run/video/voice")
SCENES = json.loads(Path("scripts/video/narration.json").read_text())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sep = " "
    text = sep.join(s["text"] for s in SCENES)
    starts, pos = [], 0
    for s in SCENES:
        starts.append(pos)
        pos += len(s["text"]) + len(sep)

    r = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}/with-timestamps",
        params={"output_format": "mp3_44100_192"},
        headers={"xi-api-key": KEY},
        json={"text": text, "model_id": MODEL, "seed": 7,
              "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "use_speaker_boost": True}},
        timeout=180)
    if r.status_code != 200:
        raise SystemExit(f"{r.status_code} {r.text[:400]}")
    d = r.json()
    mp3 = OUT / "narration.mp3"
    mp3.write_bytes(base64.b64decode(d["audio_base64"]))
    al = d.get("normalized_alignment") or d["alignment"]
    chars, t0s, t1s = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    if "".join(chars) != text:
        al = d["alignment"]   # prefer the alignment that matches our text exactly
        chars, t0s, t1s = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    assert "".join(chars) == text, "alignment does not match the script"

    wav = OUT / "narration.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-ar", "48000", "-ac", "2", str(wav)], check=True)
    total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                  str(wav)], capture_output=True, text=True).stdout)

    scenes = {}
    for i, s in enumerate(SCENES):
        a = t0s[starts[i]]
        b = t0s[starts[i + 1]] if i + 1 < len(SCENES) else total
        scenes[s["id"]] = [round(a, 3), round(b, 3)]
        print(f"{s['id']:8s} {a:6.2f} - {b:6.2f}s  ({b - a:4.1f}s)")
    (OUT / "timeline.json").write_text(json.dumps({"audio": str(wav), "voice": VOICE, "model": MODEL,
                                                   "total": round(total, 3), "scenes": scenes}, indent=1))
    print(f"total {total:.1f}s, {len(text)} characters")


if __name__ == "__main__":
    main()
