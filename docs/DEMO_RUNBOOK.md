# Second Shift product demonstration

The current delivery is `presentation/neuroscience-demo/second-shift-neuroscience.mp4`. It is a 59.6 second, 1920 × 1080 recording of the working interface with neuroscience-focused narration only. The script, evidence, and scored review are in the same directory. The previous edition remains in `presentation/product-demo/`.

Use the monochrome dashboard at http://localhost:8000. The working context, decision, experiment, and durable memory form one live diagram. Click a node or **Inspect** for evidence, **Activity** for historical decisions, or **Under the hood** for actual repository code. **Follow activity** switches to a fixed overview when disabled.

## Run the dashboard

```bash
DB_NAME=second_shift .venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000
```

To create a campaign for a manual demo:

```bash
DB_NAME=second_shift .venv/bin/python -m harness.worker --new --mode demo --max-channels 64 --budget 10 --create-only
```

Select that campaign and press **Start worker**. Press **Stop worker** while an experiment is claimed to demonstrate a real SIGKILL. Completed results remain. Press **Start worker** again, allow the previous lease to expire, and inspect attempt two. Use **Clear context**, then the **9** electrode limit. If no existing result qualifies, the incumbent must remain empty until an eligible result is measured.

## Record a new take

```bash
DEMO_API=http://localhost:8000 VIDEO_CAPTURE_DIR=run/video-v3/new-take DB_NAME=second_shift .venv/bin/python -m scripts.video.record_demo_v3
```

The recorder creates a fresh real campaign. It drives the dashboard controls, captures a continuous 1080p browser video, and preserves timestamps, events, packets, and experiment documents. It asserts that the interrupted experiment retries as attempt two and that earlier results are unchanged. It will fail rather than claim a missed stop as recovery. Do not run another worker concurrently.

Narration comes from the revised 120-word neuroscience script in `scripts/video/narration.json`. The previous 130-word script is preserved in `scripts/video/narration_v3.json`:

```bash
VIDEO_VOICE_DIR=run/video-v4/voice .venv/bin/python scripts/video/tts_elevenlabs.py
```

Listen to the voice before choosing cuts. Do not mechanically accelerate the voice. The delivered edit preserves its original speed and inserts silence between complete sentences.

## Reproduce the reviewed edit

```bash
.venv/bin/python scripts/video/edit_demo_v4.py
VIDEO_REVIEW_ROOT=run/video-v4 VIDEO_EVIDENCE_DIR=run/video-v3/take-2 .venv/bin/python scripts/video/review_demo_v3.py
```

The neuroscience revision uses new narration and new cuts of the approved continuous take. The editor's shot list is deliberately tied to `run/video-v3/take-2`, campaign `camp_614645d1`. A new campaign has different timings, so build a new edit decision list from its marks and events. Do not reuse these cut times blindly.

All included footage plays at normal speed. Clean cuts omit waiting periods; list those omissions in delivery notes. The video contains no captions, subtitles, lower thirds, speed badges, marketing overlays, music, or sound effects. The cursor and labels are part of the recorded interface. No historical events are replayed as a live campaign.

## Verify

```bash
node --test tests/test_live_state.mjs
.venv/bin/python -m pytest -q tests/test_packet_endpoint.py tests/test_contracts.py tests/test_worker.py
DEMO_API=http://localhost:8000 .venv/bin/python scripts/video/check_dashboard.py
```

The browser checks isolate their data with HTTP fixtures and make no database writes. The packet endpoint test uses a mocked database. The real recording verifies the actual worker controls and persisted recovery evidence. The existing integration API tests require the separate `second_shift_david` test database; do not point seed tests at the real demo database.

Review the exported video muted, the audio alone, and the combined timing. Direct listening remains a required human check when the reviewing environment cannot hear audio playback. The accompanying review explicitly distinguishes measured audio checks from that listening check.
