# Harness demo: delivery notes

[Video](second-shift-harness.mp4) · [Script](narration.md) · [Voice track](narration.wav) · [Raw recording](raw-continuous.webm) · [Review](review.md)

## Changes

Second Shift is described as a neuroscience harness throughout the new narration. Claude is the experiment planner inside that harness. The brain-data task is imagined hand versus foot movement classification from recorded EEG. Numerical code measures results; MongoDB Atlas preserves the campaign's evidence. No comparative performance or clinical claims were added.

The narration uses voice `ypfAZhVeE0hhj0A5eGdR` with ElevenLabs `eleven_v3`. The 110-word script was regenerated after a longer reading exceeded one minute. Its final natural duration is 58.24 seconds; 300 ms of opening silence and a closing hold bring the export to 59.6 seconds. There is no voice acceleration.

The Decide-to-Experiment connector previously ended under the electrode grid. Its endpoint now stops before the grid with a visible arrowhead. Clearance is 26.9 px at 1920, 23.2 px at 1440, 26.4 px at 1024, and 82.5 px at 800. The live dashboard eyebrow and README introduction now call Second Shift a neuroscience harness.

## Fresh campaign evidence

This is a new continuous capture of real campaign `camp_b502457a`, not reused footage of the previous dashboard. All actual interactions occur at normal speed. The complete run and event timestamps are preserved.

- Two completed results, 0.6259 and 0.6924, survive the interruption with their original attempt counts.
- Experiment `camp_b502457a:x_630f7073b4bccb50` is claimed as attempt one, interrupted by SIGKILL, then claimed as attempt two and committed at 0.5843.
- Clearing context increments the context epoch. The 64-to-nine electrode change increments the goal version and invalidates all existing 21-channel results as candidates under the new limit.
- The first packet under the new goal has no eligible incumbent. Its next experiment uses nine electrodes and measures 0.6529.
- The exported video ends with six saved results, including the later 0.7055 result. The raw run continues through all ten experiments.

The electrode grid represents the allowed count; it is not a map of anatomical electrode positions. The trace is a preview of recorded EEG. This is offline signal classification, not a live brain recording.

[Events](evidence/events.json) · [Recovery proof](evidence/recovery-proof.json) · [Packets](evidence/packets.json) · [Experiments](evidence/experiments.json) · [Capture marks](evidence/marks.json)

## Cut disclosure

Startup, portions of worker/lease waiting, planning waits, navigation holds, and the remainder of the campaign are omitted with clean cuts. No visual or audio material is sped up. No subtitles, captions, lower thirds, music, sound effects, or marketing overlays are present.

| Export interval | Raw interval | Action |
|---|---|---|
| 0.00–34.88s | 9.60–44.48s | EEG research loop, real measurements, worker interruption, surviving results, restart |
| 34.88–41.00s | 47.96–54.08s | Lease recovery and attempt-two result |
| 41.00–47.00s | 61.80–67.80s | Clear context, change electrode limit, recompute eligibility |
| 47.00–52.72s | 68.20–73.92s | Next nine-electrode experiment and measured result |
| 52.72–55.60s | 75.44–78.32s | Actual repository code for rebuilding context |
| 55.60–59.60s | 81.28–85.28s | Return directly to the running campaign and its saved results |

The UI follows backend events with normal polling latency. The exact [edit decision list](evidence/edit-decisions.json) includes narration placement.

## Verification

Nine grouped browser checks passed after the arrow and label edits: initial/empty state, event deduplication, overview and evidence/history inspection, waiting/failure states, disconnect/reconnect, non-overlapping polling, campaign switching, reduced motion and nine-electrode eligibility, and absence of JavaScript errors. The fresh capture separately exercised the real worker controls and checked persisted results. Arrow clearance was measured across four viewport widths and visually inspected.

The final export passed media and recovery checks. Independent transcription recovered the full narration from the encoded audio, and all cuts were visually inspected. Direct listening is unavailable in this session; vocal expression and fidelity are not certified by transcription or metering.

[Browser checks](evidence/browser-checks.json) · [Arrow measurements](evidence/arrow-measurements.json) · [Media verification](evidence/verification.json) · [Audio levels](evidence/audio-levels.json) · [Voice metadata](evidence/voice-timeline.json) · [Final transcription](evidence/transcript-review.json)
