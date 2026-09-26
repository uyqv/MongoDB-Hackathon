# Huashu design review: Second Shift

Reviewed against the complete, unmodified Huashu rubric in `critique-guide.md`. Source: https://github.com/alchaincyf/huashu-design/blob/master/references/critique-guide.md

Overall slide-design assessment: **8.0/10, excellent band, provisional**. This is an editorial assessment, not a weighted formula. Final presentation acceptance remains pending the new narrated movie and a complete rehearsal. The rubric provides no numerical weights, and none were introduced. Concept is the first gate: a Concept score of 5 or lower caps the overall assessment at 6.0. That cap is not triggered here. For slides, Visual Hierarchy and Functionality take priority, followed by Craft Quality.

| Dimension | Score | Assessment |
|---|---:|---|
| Concept | 8/10 | Brain-signal research builds an evidence record that survives the researcher agent restarting. The opening electrode sculpture, real EEG trace, stable evidence bar, and closing glass layers express that progression. |
| Philosophy Alignment | 9/10 | The selected Sculptural Lab direction uses warm white, charcoal, restrained green, two type families, and ample negative space consistently. |
| Visual Hierarchy | 9/10 | Each slide has one headline and a focal composition. The scientific result dominates slide 5; separate reliability checks have their own clearly labeled column. |
| Craft Quality | 8/10 | Six browser compositions and six exported slide renders were inspected. Native text, diagram and chart objects remain editable; font and layout checks pass. Native desktop PowerPoint rendering remains unverified. |
| Functionality | 7/10 | Navigation, fullscreen, notes, reduced motion, and video lifecycle pass. The missing new movie prevents final validation of the main demonstration and end-to-end timing. |
| Originality | 8/10 | Custom electrode and evidence-layer sculptures support the EEG and durable-memory story. Familiar scientific motifs are used with a project-specific relationship rather than generic AI decoration. |

## Keep

- Introduce EEG and imagined fists versus feet before explaining the memory architecture. This gives the research loop a concrete purpose.
- Preserve the visual transition from electrodes on the opening brain to evidence layers under the closing brain.
- Keep the worker-reset animation local to the planner. The research record remains visible throughout the reset.
- Retain the real C3 waveform with its units, excerpt provenance, and editable numerical chart in PowerPoint.
- Keep 73.2% labeled as the 21-electrode reference campaign. Keep 8/8 and 5/5 visually and verbally separate from it and from the future video campaign.
- Keep the script to 229 live words and five seconds of reserve. The slides carry detail that need not be read aloud.

## Fix

1. **New narrated demo is not attached — important, pending user media.** Slide 4 currently contains a purpose-built title poster, not dashboard evidence. Attach the finished new movie, retain its existing voiceover, and check every described event against the footage. No previous dashboard recording, screenshot, or extracted frame is in the delivery. The separately prepared Eric track is only an optional alternate.
2. **End-to-end presentation timing is not yet demonstrated — important, depends on final media.** The schedule budgets 115 seconds of live speech plus 60 seconds of demo, for 2:55. Rehearse with the final movie and the presenter's actual speaking pace. The calculated word budget is not a performed rehearsal.
3. **Native PowerPoint application rendering — optimization, environment verification.** Package, font-family declarations, native chart/workbook data, import and rendered layouts pass. The desktop PowerPoint app was not opened. Install the supplied fonts and check on the actual presentation machine.

## Quick Wins

If only five minutes remain before presenting:

- [ ] Load the finished new movie through “Load new demo”, then check playback, audible narration, and the transition to slide 5.
- [ ] Run the full sequence once; shorten spoken transitions if the total exceeds 2:55.
- [ ] Enter fullscreen, close the notes overlay, and keep the PowerPoint and completed MP4 available as backups.

## Validation record

- Browser: all six slides inspected; no observed clipping or low-contrast body text. Keyboard navigation, number shortcuts, overview, notes, fullscreen, offline navigation after initial local load, and reduced motion checked.
- Worker-reset animation: planner elements dim during reset; the evidence bar remains fully visible at the same animation time.
- Video lifecycle: explicit start, active playback, audible/unmuted configuration, pause/reset on leaving, and explicit playback on re-entry passed using a newly generated three-second blank control probe. That probe contains no dashboard footage and is excluded from delivery. The browser was reloaded afterwards to clear it.
- Browser assets: fonts, illustrations and code are bundled locally; no external runtime library or network API is required. The repository hyperlink is optional external navigation.
- PowerPoint: six slides; no package integrity or geometry findings; first-party import passed; one editable native chart with 320 EEG points and 640 numeric workbook cells passed structural validation. Rendered slides inspected. Native desktop PowerPoint execution was not verified.
- Metrics and EEG provenance: checked against README, eval/checks.json, configuration definitions, evaluator and locally available PhysioNet recording. Campaign IDs are included in speaker notes.
- Alternate voice: 56.293 seconds; exact 60-second audio bed; speech transcription matched intended meaning; loudness and peak checks completed. A human listening review and final footage synchronization have not been performed. The intended final movie is being created separately with its own voiceover.
