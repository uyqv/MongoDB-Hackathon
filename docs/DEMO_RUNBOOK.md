# Second Shift product demonstration

The current delivery is the single file `presentation/second-shift-neuroai-90s.mp4`. It is exactly 90 seconds at 1920 × 1080, narrated with the requested ElevenLabs voice `ypfAZhVeE0hhj0A5eGdR`. It covers NeuroAI and EEG, coherent memory as the billion-token design target, long-term goals, hard metric feedback, and the MongoDB Atlas/OpenRouter/Voyage AI integrations. The raw footage, voice, edit decisions, and verification remain in `run/video-v6/`. Previous shorter editions are preserved.

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
DEMO_API=http://localhost:8000 VIDEO_CAPTURE_DIR=run/video-v6/new-take DB_NAME=second_shift .venv/bin/python -m scripts.video.record_demo_v6
```

The recorder creates a fresh real campaign with a 14-experiment budget and allows the EEG search to run for at least 65 seconds before the interruption. It drives the dashboard controls, captures a continuous 1080p browser video, and preserves timestamps, events, packets, and experiment documents. It asserts that the interrupted experiment retries as attempt two and that earlier results are unchanged. It will fail rather than claim a missed stop as recovery. Do not run another worker concurrently.

Narration comes from the revised 148-word NeuroAI script in `scripts/video/narration.json`. Prior scripts are preserved as `narration_v3.json`, `narration_v4.json`, and `narration_v5.json`:

```bash
VIDEO_VOICE_DIR=run/video-v6/voice-final .venv/bin/python scripts/video/tts_elevenlabs.py ypfAZhVeE0hhj0A5eGdR
.venv/bin/python scripts/video/transcribe_audio.py run/video-v6/voice-final/narration.mp3 run/video-v6/voice-final/transcript-review.json
```

Listen to the voice before choosing cuts. Do not mechanically accelerate the voice. The delivered edit preserves its original speed and inserts silence between complete sentences.

## Reproduce the reviewed edit

```bash
.venv/bin/python scripts/video/edit_demo_v6.py
VIDEO_REVIEW_ROOT=run/video-v6 VIDEO_EVIDENCE_DIR=run/video-v6/take-1 VIDEO_MAX_SECONDS=90 VIDEO_TARGET_SECONDS=90 .venv/bin/python scripts/video/review_demo_v3.py
```

The 90-second revision uses a fresh continuous take with the corrected connector arrow and harness label. Its shot list is tied to `run/video-v6/take-1`, campaign `camp_639cfbea`. A new campaign has different timings, so build a new edit decision list from its marks and events. Do not reuse these cut times blindly. The generated narration lasts 84.32 seconds. Sentence boundaries are located from independent transcription so inserted pauses do not split words. Speech and footage retain their original speed.

All included footage plays at normal speed. Clean cuts omit waiting periods; list those omissions in delivery notes. The video contains no captions, subtitles, lower thirds, speed badges, marketing overlays, music, or sound effects. The cursor and labels are part of the recorded interface. No historical events are replayed as a live campaign.

## Verify

```bash
node --test tests/test_live_state.mjs
.venv/bin/python -m pytest -q tests/test_packet_endpoint.py tests/test_contracts.py tests/test_worker.py
DEMO_API=http://localhost:8000 .venv/bin/python scripts/video/check_dashboard.py
```

The browser checks isolate their data with HTTP fixtures and make no database writes. The packet endpoint test uses a mocked database. The real recording verifies the actual worker controls and persisted recovery evidence. The existing integration API tests require the separate `second_shift_david` test database; do not point seed tests at the real demo database.

Review the exported video muted, the audio alone, and the combined timing. Direct listening remains a required human check when the reviewing environment cannot hear audio playback. The accompanying review explicitly distinguishes measured audio checks from that listening check.
