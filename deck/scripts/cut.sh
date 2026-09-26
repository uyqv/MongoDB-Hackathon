#!/usr/bin/env bash
# Stitch the one-minute video from screen recordings.
#
# Put recordings in deck/clips/ and describe the cut in deck/clips/cut.txt, one clip per line:
#   <file> <start-seconds> <duration-seconds>
# Lines are played in order. Start trims the lead-in (e.g. the moment before you pressed space).
# Optional: deck/clips/narration.m4a (or .wav/.mp3) is laid over the whole video.
#
# Usage: scripts/cut.sh            -> writes deck/out/second-shift.mp4
#        scripts/cut.sh --template -> writes a starter cut.txt with the planned segment lengths
set -euo pipefail
cd "$(dirname "$0")/.."
CLIPS=clips
OUT=out
LIMIT=60

if [[ "${1:-}" == "--template" ]]; then
  mkdir -p "$CLIPS"
  cat > "$CLIPS/cut.txt" <<'T'
# file                 start  duration
01_forget.mov          0      7
02_packet.mov          0      6
03_dash_campaign.mov   0      14
04_kill.mov            0      6
05_dash_kill.mov       0      8
06_constraint.mov      0      5
07_dash_constraint.mov 0      7
08_numbers.mov         0      7
T
  echo "wrote $CLIPS/cut.txt"; exit 0
fi

[[ -f "$CLIPS/cut.txt" ]] || { echo "missing $CLIPS/cut.txt (run with --template)"; exit 1; }
mkdir -p "$OUT/parts"
rm -f "$OUT"/parts/*.mp4 "$OUT/list.txt"

total=0
i=0
while read -r file start dur; do
  [[ -z "${file:-}" || "$file" == \#* ]] && continue
  [[ -f "$CLIPS/$file" ]] || { echo "missing clip $CLIPS/$file"; exit 1; }
  i=$((i + 1))
  part=$(printf "%s/parts/%02d.mp4" "$OUT" "$i")
  # Normalize: 1920x1080 letterboxed, 30 fps, H.264, no audio (narration is added at the end).
  ffmpeg -nostdin -loglevel error -y -ss "$start" -t "$dur" -i "$CLIPS/$file" \
    -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0b0e12,fps=30,format=yuv420p" \
    -an -c:v libx264 -preset veryfast -crf 18 "$part"
  echo "file '$(basename "$part")'" >> "$OUT/parts/list.txt"
  total=$(echo "$total + $dur" | bc)
  echo "  $i. $file  ${start}s +${dur}s"
done < "$CLIPS/cut.txt"

if (( $(echo "$total > $LIMIT" | bc) )); then
  echo "total ${total}s is over the ${LIMIT}s limit; shorten cut.txt"; exit 1
fi

ffmpeg -loglevel error -y -f concat -safe 0 -i "$OUT/parts/list.txt" -c copy "$OUT/video_only.mp4"

narr=$(ls "$CLIPS"/narration.* 2>/dev/null | head -1 || true)
if [[ -n "$narr" ]]; then
  ffmpeg -loglevel error -y -i "$OUT/video_only.mp4" -i "$narr" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest "$OUT/second-shift.mp4"
else
  echo "no narration file: output has a silent audio track. Submission needs audio."
  ffmpeg -loglevel error -y -i "$OUT/video_only.mp4" -f lavfi -i anullsrc=r=48000:cl=stereo -map 0:v -map 1:a -c:v copy -c:a aac -shortest "$OUT/second-shift.mp4"
fi

len=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/second-shift.mp4")
echo "wrote $OUT/second-shift.mp4 (${len}s)"
