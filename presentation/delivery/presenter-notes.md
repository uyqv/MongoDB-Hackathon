# Second Shift: presenter notes

Target: 2:55, including a 60-second narrated demo. Five seconds remain for transitions. 229 live words; allow 115 seconds for live delivery.

## 1. Second Shift (0:00–0:15)

We built Second Shift, an autonomous research assistant for brain signals. It runs EEG experiments and keeps the research moving, even when its agent crashes, loses context, or receives a new constraint.

Sources: README.md: What it does; Conceptual artwork generated with built-in image_gen. Electrode placement is illustrative, not a measured montage.

## 2. Finding patterns in brain signals (0:15–0:35)

EEG records electrical activity from the scalp. Our task is concrete: distinguish imagined fists from imagined feet. Second Shift searches 225 configurations of electrodes, frequency bands, time windows, and classifiers. Every experiment produces a measured result that the next decision can use.

Sources: harness/contracts.py: 225 effective configurations; harness/eeg.py: within-subject run 6 training, run 10 validation, run 14 sealed test; PhysioNet EEG Motor Movement/Imagery v1.0.0: https://physionet.org/content/eegmmidb/1.0.0/; Plot: S001R06.edf, channel C3, first T1 cue at 12.5 seconds, unfiltered 160 Hz samples. See source/eeg.json.

## 3. How Second Shift researches (0:35–1:00)

The planner chooses the next configuration using recorded evidence. Numerical code trains and evaluates it. MongoDB Atlas stores the goal, experiments, and results. Each decision starts with a fresh evidence packet. Exact database reads supply measured results. Vector search retrieves research notes. A replacement worker can continue the same campaign.

Sources: harness/worker.py; harness/context.py: exact reads of best, leaders, laggards, recent results; semantic retrieval over notes; harness/store.py: deduplication, protocol identity, lease-fenced commits; harness/eeg.py: numerical evaluation

## 4. The working system (1:00–2:00)

Play the new, narrated 60-second dashboard demo. Do not speak over the recorded voiceover. At the end, advance to the measured-results slide. This slot intentionally contains no previous recording. The final demo must show the actual newly recorded actions.

Sources: New recording required. Previous recordings and raw frames are excluded at the user’s request.; Use the voiceover embedded in the user’s new finished demo. The separately generated Eric narration is an optional alternate and must not be layered over that soundtrack.

## 5. Measured on real EEG (2:00–2:30)

Our reference campaign reached seventy-three point two percent balanced accuracy on a held-out test scored once. That used twenty-one electrodes across five participants and seventy-five test trials. Separately, all eight recovery checks and all five constraint-change checks passed. These are small, offline experiments. They demonstrate the research loop, not clinical performance or a real-time decoder.

Sources: README.md: camp_0f8981ee, 0.774 validation, 0.732 sealed test, 21 electrodes, 75 test trials, subjects 1–5; eval/checks.json: camp_51b0f538 recovery 8/8; camp_66e4900c constraint 5/5; Reference campaign and reliability checks are separate from the new demo campaign.

## 6. Research that keeps its progress (2:30–2:55)

The Neuro AI value is a research assistant that can test ideas on real brain signals and preserve what it learns. Researchers can inspect the evidence, change an electrode budget, and continue from completed work. We built Second Shift to give the next experiment a reliable starting point. Thank you.

Sources: README.md: project scope and team; Repository: https://github.com/uyqv/MongoDB-Hackathon; Conceptual brain and evidence-layer artwork generated with built-in image_gen.
