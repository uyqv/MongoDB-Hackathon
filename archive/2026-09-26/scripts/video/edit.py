"""Cut the recorded frames and the narration into a one minute video.

    python scripts/video/edit.py [out.mp4]

Inputs: run/video/frames.json and marks.json (from record_demo.py) and
run/video/voice/timeline.json (from tts_elevenlabs.py). The narration is one
continuous track; each part of the footage is timed to its scene's span in
that track. Parts shown faster than real time carry a "sped up Nx" caption.
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

V = Path("run/video")
CAP = V / "captioned"
LEAD, TAIL = 0.3, 0.4           # silence before and after the narration
FONT = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 34)
SMALL = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 24)

frames = json.loads((V / "frames.json").read_text())
m = json.loads((V / "marks.json").read_text())["marks"]
timeline = json.loads((V / "voice" / "timeline.json").read_text())

# (scene id, [(video start, video end, share of the scene's narration time, caption)])
PLAN = [
    ("intro", [(0.0, m["run"], 1.0, "Real EEG from PhysioNet eegmmidb · all campaign state lives in MongoDB Atlas")]),
    ("run", [(m["run"], m["crash"], 1.0, "Live run · Claude Sonnet 5 picks the experiment, code computes every metric")]),
    ("crash", [(m["crash"], m["restart"], 0.5, "Worker SIGKILLed mid job (fault injection)"),
               (m["restart"], m["goal"], 0.5, "Start worker · campaign rebuilt from Atlas · orphaned job reruns as attempt 2")]),
    ("goal", [(m["goal"], m["goal"] + 6.0, 0.45, "Reset context · electrode budget 64 to 9"),
              (m["goal"] + 6.0, m["packet"], 0.55, "Every later proposal uses 9 channels")]),
    ("packet", [(m["packet"], m["numbers"], 1.0, "What the model saw: exact reads plus Vector Search over Jev routed notes")]),
    ("numbers", [(m["numbers"], m["outro"], 1.0, "Measured today · README and code on GitHub")]),
    ("outro", [(m["outro"] + 1.0, m["end"], 1.0, "Second Shift · github.com/uyqv/MongoDB-Hackathon")]),
]


def caption(src: str, text: str, speed: float) -> Path:
    label = text + (f"  ·  sped up {speed:.1f}x" if 1.3 <= speed < 3 else
                    f"  ·  sped up {speed:.0f}x" if speed >= 3 else "")
    out = CAP / f"{Path(src).stem}_{abs(hash(label)) % 10**10}.jpg"
    if out.exists():
        return out
    im = Image.open(V / "frames" / src).convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    w = d.textlength(label, font=FONT)
    x, y = (im.width - w) / 2, im.height - 92
    d.rounded_rectangle([x - 22, y - 14, x + w + 22, y + 50], radius=14, fill=(0, 0, 0, 200))
    d.text((x, y), label, font=FONT, fill=(255, 255, 255))
    d.text((24, im.height - 38), "Recorded live on site, Sept 26 2026 · real data, real API calls", font=SMALL,
           fill=(200, 200, 200))
    im.save(out, quality=92)
    return out


def main(out_path: str) -> None:
    CAP.mkdir(exist_ok=True)
    scenes = timeline["scenes"]
    last = PLAN[-1][0]
    concat, total = [], 0.0
    for sid, parts in PLAN:
        a0, b0 = scenes[sid]
        seg_len = (b0 - a0) + (LEAD if sid == PLAN[0][0] else 0) + (TAIL if sid == last else 0)
        for a, b, share, text in parts:
            target = seg_len * share
            speed = (b - a) / target
            src = [f for f in frames if a <= f[0] < b] or [min(frames, key=lambda f: abs(f[0] - a))]
            for i, (t, name) in enumerate(src):
                nxt = src[i + 1][0] if i + 1 < len(src) else b
                concat.append((caption(name, text, speed), max((nxt - t) / speed, 0.001)))
            total += target
            print(f"{sid:8s} {a:6.1f}-{b:6.1f}s  real {b - a:5.1f}s  shown {target:4.1f}s  speed {speed:4.1f}x")

    lst = V / "concat.txt"
    lines = []
    for path, dur in concat:
        lines += [f"file '{path.resolve()}'", f"duration {dur:.4f}"]
    lines.append(f"file '{concat[-1][0].resolve()}'")
    lst.write_text("\n".join(lines) + "\n")

    delay = int(LEAD * 1000)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-i", timeline["audio"],
                    "-filter_complex", f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,adelay={delay}|{delay},apad[a]",
                    "-map", "0:v", "-map", "[a]", "-t", f"{total:.3f}",
                    "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_path], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                out_path], capture_output=True, text=True).stdout)
    print(f"planned {total:.1f}s, file {dur:.1f}s -> {out_path}  (voice {timeline['voice']}, {timeline['model']})")
    assert dur <= 60.0, "over one minute"


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(V / "second_shift_demo.mp4"))
