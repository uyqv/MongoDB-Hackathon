# Second Shift presentation

Open **index.html** in Chrome, Edge, or Safari. Keep this folder together. Fonts, artwork, and the finished demo are local.

The pitch is timed for **2:55 within a three-minute slot**, including the complete **90-second demo**, with five seconds of reserve. Follow **presenter-script.md** for the spoken script, video cues and short answers. **presenter-notes.md** includes the same speech and source references.

## Presenting

- Left and right arrows change slides. Number keys 1 to 6 jump to a slide.
- F enters fullscreen. O shows all six slides. R resets the rehearsal timer.
- N opens notes on the same screen. Close them before projecting.
- Reach slide 4 at 0:45, say its introduction, then press Enter at 0:50.
- Let the full video play with its existing narration. Advance to slide 5 at 2:20.
- Leaving slide 4 stops and resets the movie.

## Included demo

**media/second-shift-neuroai-90s.mp4** is an unchanged copy of the exact movie requested for this presentation. It loads automatically and starts only when you press Enter or click slide 4. The Load demo control can reconnect the file if needed.

The video shows experiments accumulating, a worker stop and restart, context clearing, and the electrode limit changing from 64 to nine. It ends with a best eligible validation score of 0.759 using nine electrodes. Its narration remains intact. Do not play any separate voiceover on top of it.

The older `second-shift-voiceover` audio and `second-shift-demo-audio.wav` in this working folder were optional audio for the previous 60-second plan. The current presentation does not use them.

## PowerPoint backup

Use **Second-Shift-Neuro-AI-Aligned.pptx**. The six slides and speaker notes match the browser deck. The text, EEG chart and research-loop elements remain editable. This static backup does not embed the movie. Play the included MP4 in a separate player on slide 4, then return to slide 5.

Install Space Grotesk and Source Sans 3 from assets/fonts if needed. The browser loads them automatically. The deck was rendered and checked programmatically, not opened in desktop PowerPoint.

## Results and scope

Slide 5 separates the demo's **75.9% validation balanced accuracy with nine electrodes** from the reference campaign's **73.2% sealed test balanced accuracy with 21 electrodes**. The 8/8 recovery and 5/5 constraint checks are invariants from separate evaluations, not counts of independent trials. The memory stress check used 10,000 synthetic distractor notes. Billions of tokens remains a target.

The brain sculptures are conceptual illustrations. The waveform is a real PhysioNet EEG excerpt. See CREDITS.md for asset provenance.
