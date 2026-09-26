"""Prepare the new narration and an exact 60-second audio bed. No video input."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "presentation/.build/voice"
OUT = ROOT / "presentation/delivery/media"
SCENES = json.loads((ROOT / "presentation/source/narration.json").read_text())
TARGET, LEAD = 56.3, 0.6

def duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]))

def run(*args):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *map(str, args)], check=True)

raw = BUILD / "narration.wav"
tempo = duration(raw) / TARGET
run("-i",raw,"-af",f"atempo={tempo:.12f},loudnorm=I=-16:TP=-1.5:LRA=11","-ar","48000","-ac","2",OUT / "second-shift-voiceover.wav")
run("-i",OUT / "second-shift-voiceover.wav","-c:a","libmp3lame","-b:a","192k",OUT / "second-shift-voiceover.mp3")
run("-i",OUT / "second-shift-voiceover.wav","-af",f"adelay={int(LEAD*1000)}|{int(LEAD*1000)},apad","-t","60",OUT / "second-shift-demo-audio.wav")
tl = json.loads((BUILD / "timeline.json").read_text())
new = {"duration_seconds":60,"spoken_audio_seconds":duration(OUT / "second-shift-voiceover.wav"),"lead_seconds":LEAD,"voice":"Eric","provider":"ElevenLabs","model":tl["model"],"tempo_factor":tempo,"new_recording_required":True,"scenes":[]}
for scene in SCENES:
    a,b = tl["scenes"][scene["id"]]
    new["scenes"].append({**scene,"start":round(a/tempo+LEAD,3),"end":round(b/tempo+LEAD,3)})
(OUT / "narration-cues.json").write_text(json.dumps(new,indent=2))
(ROOT / "presentation/delivery/demo-narration.md").write_text("# Optional alternate demo narration\n\nThe final user-created movie will include its own voiceover. Preserve that soundtrack; do not add this alternate narration over it.\n\nElevenLabs Eric. No music. Narration is timed inside a 60-second audio bed. These are editorial cues for the NEW recording, not claims that new footage has been supplied or reviewed.\n\n"+"\n\n".join(f"## {s['start']:.1f}–{s['end']:.1f} seconds: {s['id']}\n\n{s['text']}" for s in new["scenes"])+"\n\nKeep the final frame on screen until 60 seconds. Show code during the results segment. Label time compression. Completed experiments are reused; interrupted attempts can rerun. Separate reliability checks are not events from the demo campaign.\n")
print(json.dumps(new,indent=2))
