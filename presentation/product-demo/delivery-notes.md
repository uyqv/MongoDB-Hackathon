# Delivery notes and recorded evidence

[Video](second-shift-demo.mp4) · [Scored review](review.md) · [Raw recording](raw-continuous.webm)

## Real-run evidence

Campaign: `camp_614645d1`, in the real `second_shift` database. Ten planner calls, zero planner fallbacks. No research algorithm or database migration was introduced.

- Attempt one claimed: 2026-09-26 19:35:35.863 UTC.
- Real SIGKILL through the dashboard: 19:35:36.038 UTC.
- New worker starts: 19:35:45.823 UTC, reporting two completed results and one interrupted job.
- Same experiment claimed as attempt two: 19:35:52.799 UTC; result committed at 19:35:53.611 UTC.
- Context reset: 19:36:04.534 UTC. Electrode limit changed from 64 to nine: 19:36:06.525 UTC.

The exported video ends with seven results and continuing research. The preserved raw recording continues through all ten experiments. The small EEG trace is a labeled preview of recorded data. The 64-position grid represents the allowed electrode count, not anatomical electrode locations or the channel count of every earlier experiment.

[Recovery proof](evidence/recovery-proof.json), [timestamped events](evidence/events.json), [capture marks](evidence/marks.json), [stored decision packets](evidence/packets.json), and [experiment documents](evidence/experiments.json) are preserved. The dashboard's new packet-by-ID endpoint returns only a packet belonging to the requested campaign and removes embeddings.

## Cut disclosure

Every included shot is continuous browser footage at its original speed. Startup, planner waits, part of the restart/lease wait, extra navigation holds, and the remainder of the campaign are omitted with clean cuts. Nothing is accelerated, restaged as a simulated live event, or replaced with screenshot animation. Source times refer to [the raw recording](raw-continuous.webm); event timestamps are UTC and the UI reflects the normal polling delay.

| Export interval | Raw interval | What is shown |
|---|---|---|
| 0.00–17.80s | 14.20–32.00s | Evidence, first measurement, commit, and another evidence packet |
| 17.80–29.40s | 32.32–43.92s | Third proposal, real stop during attempt one, surviving results, restart click |
| 29.40–35.52s | 52.20–58.32s | Lease recovery, same experiment on attempt two, measured result saved |
| 35.52–40.92s | 65.40–70.80s | Clear context, 64 to 9, no eligible incumbent, and the new evidence packet |
| 40.92–47.80s | 72.00–78.88s | New decision, nine-electrode result, and a readable hold on its value |
| 47.80–50.80s | 80.24–83.24s | Actual rehydrate function served from this repository |
| 50.80–54.16s | 85.20–88.56s | Return to the running campaign |
| 54.16–59.60s | 95.12–100.56s | Next evidence-driven experiment and a longer hold on its measured result |

The exact [edit decision list](evidence/edit-decisions.json) also preserves the narration placement. No cut disclosures were placed on the video itself, as requested.

## Verification

- Seven display-state tests passed.
- Fourteen Python tests passed, covering the packet endpoint, contracts, and worker guards.
- Nine browser checks passed: initial/empty state, event deduplication, overview/evidence/history inspection, waiting/failure, disconnect/reconnect, non-overlapping slow requests, campaign switching, reduced motion/context reset/nine-electrode eligibility, and no JavaScript errors.
- The actual recording exercised Start, Stop, restart, Clear context, and the electrode limit. Completed experiment values and attempts were verified against persisted documents.
- A real historical packet was opened through the browser inspector. The real API returned 200 for its owning campaign and 404 for a different campaign.
- The main server at port 8000 now serves the redesigned dashboard and the new endpoint.

[Browser checks](evidence/browser-checks.json) · [media verification](evidence/verification.json) · [file metadata](evidence/media-probe.json) · [transcribed narration](evidence/transcript-review.json)
