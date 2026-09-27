"""Cut the v2 recording and the ElevenLabs narration into the one minute video.

    python scripts/video/edit_v2.py [out.mp4]

No subtitles. The opening is a slow push-in on the idle dashboard, every part
is timed to its line of narration, sped-up parts carry a small fast-forward
chip in the corner (so the video never passes a replay off as real time), and
the close crossfades into an end card.
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

V = Path("run/video")
OUT = V / "v2"
FPS = 30
LEAD, TAIL = 0.35, 1.1
W, H = 1920, 1080
F = "/System/Library/Fonts/Supplemental/"
CHIP = ImageFont.truetype(F + "Arial Bold.ttf", 26)
MUSIC = "--no-music" not in sys.argv

frames = json.loads((V / "frames.json").read_text())
m = json.loads((V / "marks.json").read_text())["marks"]
tl = json.loads((V / "voice" / "timeline.json").read_text())
S = tl["scenes"]

# scene -> [(video start, video end, share of the scene's narration)]
PLAN = [
    ("run", [(m["start"] - 0.6, m["kill"] - 0.9, 1.0)]),
    ("crash", [(m["kill"] - 0.9, m["restart"] + 2.0, 0.55), (m["restart"] + 2.0, m["goal"] - 0.6, 0.45)]),
    ("goal", [(m["goal"] - 0.6, m["goal"] + 3.8, 0.4), (m["goal"] + 3.8, m["done"] + 1.0, 0.6)]),
    ("results", [(m["results"] - 0.3, m["code"] - 0.3, 0.55), (m["code"] - 0.3, m["end"], 0.45)]),
]


def frame(name: str) -> Image.Image:
    return Image.open(V / "frames" / name).convert("RGB")


def chip(im: Image.Image, speed: float) -> Image.Image:
    """Small fast-forward indicator (two drawn triangles + the speed), top right."""
    im = im.copy()
    d = ImageDraw.Draw(im, "RGBA")
    label = f"{speed:.0f}×" if speed >= 3 else f"{speed:.1f}×"
    tw = d.textlength(label, font=CHIP)
    icon = 34
    w = icon + 10 + tw
    x, y = W - w - 60, 106
    d.rounded_rectangle([x - 16, y - 10, x + w + 16, y + 38], radius=12, fill=(0, 0, 0, 150))
    col = (255, 255, 255, 215)
    for dx in (0, 16):
        d.polygon([(x + dx, y + 4), (x + dx + 16, y + 14), (x + dx, y + 24)], fill=col)
    d.text((x + icon + 10, y - 1), label, font=CHIP, fill=col)
    return im


def end_card() -> Image.Image:
    im = Image.new("RGB", (W, H), (7, 9, 13))
    d = ImageDraw.Draw(im)
    for r in range(900, 0, -12):   # soft green glow
        a = int(18 * (1 - r / 900))
        d.ellipse([W / 2 - r * 1.6, 260 - r * 0.7, W / 2 + r * 1.6, 260 + r * 0.7], fill=(7 + a // 3, 9 + a, 13 + a // 2))
    s = 132
    x0, y0 = W / 2 - s / 2, 300
    d.rounded_rectangle([x0, y0, x0 + s, y0 + s], radius=36, fill=(0, 237, 100))
    d.line([(x0 + 33, y0 + 83), (x0 + 50, y0 + 83)], fill=(5, 46, 26), width=12)
    pts = [(x0 + 33 + i * 1.3, y0 + 83 - 34 * __import__("math").sin(i / 50 * 3.14159)) for i in range(0, 51)]
    d.line(pts, fill=(5, 46, 26), width=12, joint="curve")
    title = ImageFont.truetype(F + "Arial Bold.ttf", 108)
    sub = ImageFont.truetype(F + "Arial.ttf", 40)
    mono = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 30)
    small = ImageFont.truetype(F + "Arial.ttf", 26)
    for text, font, y, col in (("Second Shift", title, 480, (238, 241, 246)),
                               ("Agents that never lose the plot.", sub, 615, (160, 168, 184)),
                               ("github.com/uyqv/MongoDB-Hackathon", mono, 730, (0, 237, 100)),
                               ("MongoDB Atlas  ·  Claude  ·  Jev  ·  Voyage  ·  real PhysioNet EEG", small, 800, (110, 118, 134))):
        w = d.textlength(text, font=font)
        d.text(((W - w) / 2, y), text, font=font, fill=col)
    return im


def main(out_path: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    seq: list[tuple[Path, float]] = []
    n = 0

    def put(im: Image.Image, dur: float) -> None:
        nonlocal n
        p = OUT / f"s{n:05d}.jpg"
        im.save(p, quality=93)
        seq.append((p, dur))
        n += 1

    # opening: slow push-in on the idle dashboard while the problem is stated
    idle = frame(min(frames, key=lambda f: abs(f[0] - 2.0))[1])
    intro_len = (S["intro"][1] - S["intro"][0]) + LEAD
    k = int(intro_len * FPS)
    black = Image.new("RGB", (W, H), (0, 0, 0))
    for i in range(k):
        z = 1.0 + 0.045 * (i / max(1, k - 1))
        cw, ch = W / z, H / z
        x0, y0 = (W - cw) / 2, (H - ch) * 0.35
        im = idle.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.LANCZOS)
        if i < 18:   # fade in from black
            im = Image.blend(black, im, (i + 1) / 18)
        put(im, 1 / FPS)
    print(f"intro    push-in {intro_len:4.1f}s")

    total = intro_len
    for sid, parts in PLAN:
        seg = S[sid][1] - S[sid][0]
        for a, b, share in parts:
            target = seg * share
            speed = (b - a) / target
            src = [f for f in frames if a <= f[0] < b]
            for i, (t, name) in enumerate(src):
                nxt = src[i + 1][0] if i + 1 < len(src) else b
                im = frame(name)
                put(chip(im, speed) if speed >= 1.5 else im, max((nxt - t) / speed, 0.001))
            total += target
            print(f"{sid:8s} {a:6.1f}-{b:6.1f}s real {b - a:5.1f}s shown {target:4.1f}s speed {speed:4.1f}x")

    # close: crossfade from the code view into the end card
    last = frame(frames[-1][1])
    card = end_card()
    fade = int(0.5 * FPS)
    for i in range(fade):
        put(Image.blend(last, card, (i + 1) / fade), 1 / FPS)
    close_len = (S["close"][1] - S["close"][0]) + TAIL - 0.5
    put(card, close_len)
    total += 0.5 + close_len
    print(f"close    end card {0.5 + close_len:4.1f}s")

    lst = OUT / "concat.txt"
    body = []
    for p, dur in seq:
        body += [f"file '{p.resolve()}'", f"duration {dur:.4f}"]
    body.append(f"file '{seq[-1][0].resolve()}'")
    lst.write_text("\n".join(body) + "\n")
    delay = int(LEAD * 1000)
    voice = f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,adelay={delay}|{delay},apad"
    music = V / "voice" / "music.mp3"
    if MUSIC and music.exists():
        audio_in = ["-i", tl["audio"], "-i", str(music)]
        graph = (f"{voice},asplit=2[v1][vsc];"
                 f"[2:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=0.18,"
                 f"afade=t=in:st=0:d=1.5,afade=t=out:st={total - 2.5:.2f}:d=2.5,apad[mus];"
                 f"[mus][vsc]sidechaincompress=threshold=0.02:ratio=5:attack=15:release=450[duck];"
                 f"[v1][duck]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.9[a]")
    else:
        audio_in = ["-i", tl["audio"]]
        graph = f"{voice}[a]"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), *audio_in,
                    "-filter_complex", graph, "-map", "0:v", "-map", "[a]", "-t", f"{total:.3f}",
                    "-vf", f"fps={FPS},format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_path], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out_path],
                               capture_output=True, text=True).stdout)
    print(f"planned {total:.1f}s, file {dur:.1f}s -> {out_path}")
    assert dur <= 60.0, "over one minute"


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(args[0] if args else str(V / "second_shift_demo_v2.mp4"))
