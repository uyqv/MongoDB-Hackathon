# Second Shift: video scenes

3D framing scenes for the one-minute submission video. React Three Fiber, drei, and a CC0 animated robot. The **proof** in the video is the real dashboard footage cut between these scenes. The scenes only frame it, and every number they show comes from the real campaign.

## Run

```bash
cd deck
npm install
npm run dev            # http://localhost:5199
```

Scenes: `forget`, `packet`, `kill`, `constraint`, `numbers`, or `all` to play them back to back.

- `?scene=kill`: loads on the first frame, frozen. **Space** plays, **R** resets, **←/→** switch scenes, **H** hides the help line.
- `?scene=all&autoplay=1`: plays everything straight away.
- `?scene=kill&t=3.5`: freezes at 3.5 s (for stills).

## Data (real numbers only)

`src/snapshot/campaign.json` is a snapshot of campaign `camp_0f8981ee` from the real DB. Regenerate it with the API pointed at `second_shift`:

```bash
DB_NAME=second_shift .venv/bin/uvicorn api.main:app --port 8001   # from repo root
cd deck && API=http://localhost:8001 CAMPAIGN=camp_0f8981ee npm run snapshot
```

The script refuses a fake campaign or the dev DB. The scenes read every metric from this file: incumbent, sealed test, LLM usage, packet size, per-experiment scores and channel counts, and the EEG trace. Visual-only values that are not data: the `forget` scene's 8-slot context box is illustrative, and `NEW_MAX = 9` is the demo's constraint change.

## Record

1. Open Chrome full screen at 1920×1080, load `?scene=<name>`, press **H** to hide the help line.
2. Cmd+Shift+5 → record the screen. Press **Space**. Stop after the scene holds on its last frame.
3. Save the clips as `deck/clips/01_forget.mov` and so on, following the order in `clips/cut.txt`.

## Cut

```bash
scripts/cut.sh --template   # writes clips/cut.txt: file, start offset, duration per clip
# edit the start offsets to trim each clip's lead-in
scripts/cut.sh              # writes out/second-shift.mp4 (1080p30, fails if over 60 s)
```

Put the narration at `clips/narration.m4a` (script in `NARRATION.md`). Without it the output has a silent track, and the submission needs audio.

## Known issue

When `?scene=all` moves from `constraint` to `numbers`, the console logs one `removeChild` error from drei `<Html>` teardown. Playback continues. Recording scenes one at a time avoids it.
