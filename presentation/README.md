# Second Shift presentation source

The shareable presentation lives in `delivery/`. Open `delivery/index.html`. Read `delivery/START-HERE.md` for presentation controls and the current new-recording dependency.

## Rebuild

From the repository root:

```sh
node presentation/source/build_browser.mjs
```

For PowerPoint, the Codex bundled runtime is required. Link its supplied node_modules directory at `presentation/.build/node_modules`, then run `source/build_pptx.mjs` using the bundled Node executable with `RUNTIME_NODE_MODULES` set. Pass a fresh PPTX filename as the first argument because finalization never overwrites an existing output or receipt.

The shared content and positions are in `source/content.mjs`. `source/eeg.json` contains the chart values and provenance. `source/extract_eeg.py` regenerates that excerpt from the existing local PhysioNet training recording without downloading data or running the research worker.

The approved direction and storyboard came from the user's implementation request. This explicit selection superseded Huashu's exploratory direction-selection workflow. Its exact critique rubric is retained in `review/critique-guide.md`; no numerical weights were invented.

## Voice generation

From the repository root, run `.venv/bin/python presentation/source/generate_voice.py`, then `.venv/bin/python presentation/source/prepare_audio.py`. Generation uses the existing ElevenLabs adapter and configured key without changing the original adapter, narration script, or recordings. Do not print the key. A new API generation is billable; do not rerun it just to rebuild slides.

Only new footage may be attached. No old recording is used as a fallback. The current deliverable intentionally has no completed MP4 until the new recording arrives.

The user clarified that the new demo is being created with voiceover. Preserve that soundtrack. The separately generated Eric audio is optional and must not be added over the movie’s narration. The Desktop instruction was corrected and is not an output-location request.
