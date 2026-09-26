# Second Shift presentation source

The current presentation lives in `delivery/`. Open `delivery/index.html` and follow `delivery/presenter-script.md`. It is timed for three minutes, including the finished 90-second movie at `second-shift-neuroai-90s.mp4`. `delivery/START-HERE.md` explains playback and the PowerPoint backup.

The current shareable package is `Second-Shift-Presentation-Aligned.zip`. The earlier ZIP and `delivery/Second-Shift-Neuro-AI.pptx` remain as previous versions. The revised PowerPoint is `delivery/Second-Shift-Neuro-AI-Aligned.pptx`.

## Rebuild

From the repository root:

```sh
node presentation/source/build_browser.mjs
```

The shared slide content, positions, speaking script, and timing live in `source/content.mjs`. Rehearsal cues and short answers live in `source/presenter-cues.md`. The browser build regenerates `delivery/index.html`, `delivery/presenter-script.md`, `delivery/presenter-notes.md`, and `source/content.json`.

For PowerPoint, use the Codex bundled runtime. Link its node_modules at `presentation/.build/node_modules`, then run `source/build_pptx.mjs` with the bundled Node executable and `RUNTIME_NODE_MODULES` set. Pass a fresh PPTX filename because finalization never overwrites an existing output or receipt. Temporary exports and rendered checks live under `presentation/.build/alignment/`.

`source/eeg.json` contains the real waveform values and provenance. `source/extract_eeg.py` regenerates the excerpt from the existing local PhysioNet training recording.

## Demo and narration

The delivery copy at `delivery/media/second-shift-neuroai-90s.mp4` must remain byte-identical to `second-shift-neuroai-90s.mp4`. The browser plays its embedded narration and never mixes in alternate audio. The video was reviewed against its frames, the matching export transcript, experiment records, and recovery evidence under `run/video-v6/`.

`delivery/demo-narration.md` and `delivery/media/narration-cues.json` describe this finished 90-second movie. The old `source/narration.json`, `generate_voice.py`, and `prepare_audio.py` are recipes for the previous optional 60-second voiceover. They are not part of the current presentation build. Do not regenerate or layer that audio onto this movie.
