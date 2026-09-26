# Sources and artwork

- Product, campaign results, and team: repository README, https://github.com/uyqv/MongoDB-Hackathon
- Recovery and constraint checks: `eval/checks.json`, campaigns `camp_51b0f538` and `camp_66e4900c`.
- Reference accuracy: `camp_0f8981ee`, 0.732 held-out balanced accuracy, 21 electrodes, 5 subjects, 75 test trials. Validation 0.774 is a different metric and is not used as test accuracy.
- EEG excerpt: PhysioNet EEG Motor Movement/Imagery v1.0.0, S001R06.edf, C3, first T1 cue at 12.5 seconds, unfiltered 160 Hz samples. https://physionet.org/content/eegmmidb/1.0.0/ . DOI: 10.13026/C28G6P. Schalk et al. (2004), BCI2000. Distributed under the Open Data Commons Attribution License. The exact extracted values and file hash are in `presentation/source/eeg.json` in the project.
- Brain artwork: generated specifically for this presentation with the built-in Imagegen tool, then edited by the same tool to remove backgrounds. Conceptual imagery only. Final files: `assets/brain-hero-alpha.png` and `assets/brain-memory-alpha.png`. Prompts are in `presentation/source/image-prompts.json` and `presentation/source/image-edit-prompts.json`.
- Fonts: Space Grotesk and Source Sans 3, distributed with their SIL Open Font Licenses in `assets/fonts`.
- Second Shift mark: existing project wave logo, unchanged.
- Design review framework: Huashu Design, https://github.com/alchaincyf/huashu-design/blob/master/references/critique-guide.md . An unmodified copy and its MIT license are saved in `presentation/review` in the project.
- Optional alternate narration: newly generated through ElevenLabs, Eric voice, `eleven_v3`. Script in `demo-narration.md`.

The intended final demo is being created by the user with its own voiceover. It has not yet been included or reviewed.
