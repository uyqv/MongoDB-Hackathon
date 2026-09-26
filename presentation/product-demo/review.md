# Second Shift: delivered demo and review

[Play the 59.6-second MP4](second-shift-demo.mp4) · [Open the dashboard](http://localhost:8000/?campaign=camp_614645d1) · [Continuous raw recording](raw-continuous.webm)

**Provisional self-review: 8.7/10.** This evaluates the rendered dashboard and exported video. The visual, factual, and automated media checks passed. Direct listening is unavailable in this reviewing session, so the voice-expression judgment remains provisional. The requested listening-based acceptance step is not certified as complete.

| Criterion | Weight | Score | Evidence from the delivered artifact |
|---|---:|---:|---|
| Demonstration accuracy | 25% | 9.2 | The actual Stop control kills a claimed experiment. The same experiment commits on attempt two at 0.6654. Two earlier results, 0.6924 and 0.7454, retain their original values and attempt counts. The new nine-electrode goal initially has no eligible incumbent, then produces 0.7592. Every new-goal proposal uses central9. |
| Visual explanation | 20% | 8.6 | The full loop stays visible. Evidence tokens enter the packet, decisions and experiments activate, measured values join persistent memory and the chart. At 24–29 seconds the temporary workspace fades while saved results remain. The grid visibly reduces from 64 to nine. Details stay in the inspector. |
| Design and originality | 20% | 8.7 | A consistent monochrome composition uses a paper stack, decision orbit, electrode matrix, and a solid memory foundation. The 1080p composition and fixed controls fit without clipping. Typography is served locally. |
| Narration | 15% | 8.0 provisional | Speech-to-text independently recovers all 130 approved words from the edited audio. Complete sentences are retained, speech runs from 0.56 to 55.34 seconds, and pauses are added without changing voice speed. Expressiveness and naturalness still need direct listening. |
| Pacing and synchronization | 10% | 8.6 | Stop, restart, and the new constraint land with the relevant spoken sections. The second edit removes excess planning waits and holds the new nine-electrode result for roughly two seconds before the code view. The final measured result remains visible through the close. All seven cuts were inspected on both sides. |
| Technical polish | 10% | 8.8 | Verified 1920 × 1080, 25 fps, 1,490 frames, H.264/AAC, 59.6 seconds. Audio measures −16.47 LUFS and −1.78 dBTP. There are no subtitle streams, burned-in captions, lower thirds, speed labels, music, or sound effects. Real controls and inspection paths passed checks. |

## Review and iteration

The complete export was inspected muted at one-second intervals, with full-size checks of important states and adjacent frames at every cut. The first edit gave the new result too little screen time, so planning waits were shortened and the result holds were extended. The affected sequence and cuts were inspected again. Spoken-word timestamps were compared with the displayed actions after the change.

Audio-only checks used independent transcription, word timing, loudness, and peak measurement. No words were lost, no unexpected audio events were detected, and the final spoken word ends more than four seconds before the file ends. These checks do not substitute for listening to tone and expression. The narration file is available separately as [narration.wav](narration.wav).

The live UI was also refined after browser checks: interrupted attempts remain identifiable, ineligible results retain readable contrast, duplicate events do not repeat animations, disconnection stops activity, inactive campaigns cannot appear to run, and an inspector opened during initial loading updates when its data arrives.


[Delivery notes, cut disclosures, raw footage, and verification evidence](delivery-notes.md). A two-second animation sample contains 50 distinct decoded frames at the native 25 fps.
