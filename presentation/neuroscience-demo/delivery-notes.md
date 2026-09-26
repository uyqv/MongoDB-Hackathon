# Neuroscience revision: delivery notes

[Video](second-shift-neuroscience.mp4) · [Script](narration.md) · [Review](review.md) · [Continuous raw recording](../product-demo/raw-continuous.webm)

This revision replaces the narration and recuts the approved continuous recording of campaign `camp_614645d1`. It does not introduce a new backend run, model behavior, or dashboard design. The previous edition is preserved in `../product-demo/`.

## Neuroscience positioning

The opening identifies Second Shift as an agent built specifically for neuroscience. The narration explains the dedicated EEG pipeline and its electrode constraint, then closes with the value of preserving neuroscience research across agent restarts.

Those claims are supported by `harness/eeg.py`: recorded PhysioNet EEGMMIDB data, imagined both-fists versus both-feet classification, MNE filtering, electrode subsets, cue-aligned epochs, bandpower/log-variance or CSP features, and held-out model evaluation. “Dedicated EEG pipeline” describes implemented behavior; this demo makes no comparative speed, clinical validation, or proprietary optimization claim.

For the accompanying technical explanation: Claude plans experiments through OpenRouter; Jev classifies research notes; MNE-Python, NumPy, SciPy, and scikit-learn form the numerical EEG stack; MongoDB Atlas persists the campaign; Voyage AI embeds notes; Atlas Vector Search retrieves relevant notes. The spoken version keeps the EEG work, Claude, and MongoDB Atlas prominent so the one-minute demonstration has room to show recovery and adaptation.

## Recorded proof

The real stop kills a claimed experiment. After restart, the same experiment runs as attempt two and commits 0.6654. The earlier 0.6924 and 0.7454 results retain their values and attempt counts. The first packet after the nine-electrode goal has no eligible incumbent; the next eligible result is 0.7592.

The raw recording preserves ten experiments; this revision ends with six results and continuing research. The small EEG trace previews recorded data. The 64-position diagram represents the allowed electrode count, not anatomical positions or the actual channel count of every earlier experiment.

[Timestamped events](../product-demo/evidence/events.json), [recovery proof](../product-demo/evidence/recovery-proof.json), [decision packets](../product-demo/evidence/packets.json), [experiments](../product-demo/evidence/experiments.json), and [capture marks](../product-demo/evidence/marks.json) remain preserved with the shared raw take.

## Cuts and timing

Every included shot plays at its original speed. Clean cuts omit startup, a stopped-state hold, restart/lease waiting, planning waits, extra navigation holds, and the remainder of the campaign. The narration is not accelerated. Silence is inserted only at sentence boundaries. The UI retains its normal polling delay relative to backend event timestamps.

| Export interval | Raw interval | Visible action |
|---|---|---|
| 0.00–33.80s | 8.00–41.80s | EEG campaign introduction, measurements, evidence reuse, and real stop |
| 33.80–34.80s | 43.00–44.00s | Restart control |
| 34.80–39.92s | 53.00–58.12s | Interrupted experiment retries and saves its result |
| 39.92–46.12s | 64.60–70.80s | Context clear, 64 to nine electrodes, empty eligibility |
| 46.12–53.20s | 71.80–78.88s | New decision and measured nine-electrode result |
| 53.20–55.40s | 80.24–82.44s | Actual context-reconstruction code |
| 55.40–59.60s | 85.20–89.40s | Return to the EEG campaign and its next result |

[Exact edit decisions and voice placement](evidence/edit-decisions.json) accompany the export. No explanatory overlays were added to the video.

## Verification

The new final export passed dimensions, duration, stream, playback-speed, and recorded recovery checks. Independent transcription of the encoded MP4 audio recovers all 120 words; final speech ends at 57.44 seconds. All six cuts and all sixty one-second samples were visually inspected. Audio measures −16.01 LUFS and −2.01 dBTP. Direct listening remains unverified in this session.

The unchanged dashboard previously passed seven display-state tests, fourteen Python tests, and nine grouped browser checks covering real controls, deduplication, campaign switching, inspection, non-overlapping polling, disconnection/reconnection, reduced motion, and empty/failure states. The recorded run separately verifies actual worker controls and persisted recovery.

[Browser checks](../product-demo/evidence/browser-checks.json) · [New export verification](evidence/verification.json) · [Media metadata](evidence/media-probe.json) · [Audio levels](evidence/audio-levels.json) · [Encoded-audio transcription](evidence/transcript-review.json) · [File checksum](evidence/sha256.txt)
