# Second Shift: presentation script

Target: 2:55 including the complete 90-second narrated demo. Allow five seconds of reserve inside a three-minute slot. 168 live words in about 85 seconds. Timing follows the existing three-minute pitch plan.

| Slide | Topic | Pitch clock |
| --- | --- | --- |
| 1 | Second Shift | 0:00 to 0:12 |
| 2 | Finding patterns in brain signals | 0:12 to 0:27 |
| 3 | How Second Shift researches | 0:27 to 0:45 |
| 4 | The working system | 0:45 to 2:20 |
| 5 | Results and reliability | 2:20 to 2:42 |
| 6 | Research that keeps its progress | 2:42 to 2:55 |

## 1. Second Shift

**0:00 to 0:12**

We built Second Shift, a neuroscience harness that keeps EEG research moving when an agent crashes or loses its working context.

## 2. Finding patterns in brain signals

**0:12 to 0:27**

EEG records electrical activity from the scalp. Our task is to distinguish imagined fists from imagined feet. The agent searches 225 configurations, and each measured result helps guide its next experiment.

## 3. How Second Shift researches

**0:27 to 0:45**

Each decision starts with evidence from Atlas. Exact reads retrieve measured results. Vector search retrieves notes. Claude chooses the next experiment, and numerical code evaluates it. The result returns to Atlas for the next decision.

## 4. The working system

**0:45 to 2:20**

Watch the saved results survive a restart and a tighter electrode limit.

**Action:** At 0:50, press Enter. Let the 90-second narration play without speaking over it. Advance when the video ends at 2:20.

## 5. Results and reliability

**2:20 to 2:42**

The demo reaches seventy five point nine percent validation balanced accuracy using nine electrodes. Separately, our reference campaign scored seventy three point two percent on its sealed test using twenty one electrodes. These are small offline experiments, supported by separate reliability checks.

## 6. Research that keeps its progress

**2:42 to 2:55**

We tested memory with ten thousand distractor notes. Billions of tokens remains the goal. Second Shift keeps research moving, even when the agent starts over. Thank you.

## Sources and context

### Slide 1

- README.md: What it does
- Conceptual artwork generated with built-in image_gen. Electrode placement is illustrative, not a measured montage.

### Slide 2

- harness/contracts.py: 225 effective configurations
- harness/eeg.py: within-subject run 6 training, run 10 validation, run 14 sealed test
- PhysioNet EEG Motor Movement/Imagery v1.0.0: https://physionet.org/content/eegmmidb/1.0.0/
- Plot: S001R06.edf, channel C3, first T1 cue at 12.5 seconds, unfiltered 160 Hz samples. See source/eeg.json.

### Slide 3

- harness/worker.py
- harness/context.py: exact reads of best, leaders, laggards, recent results; semantic retrieval over notes
- harness/store.py: deduplication, protocol identity, lease-fenced commits
- harness/eeg.py: numerical evaluation

### Slide 4

- presentation/second-shift-neuroai-90s.mp4: 90 seconds, campaign camp_639cfbea, original narration preserved
- run/video-v6/export/edit-decisions.json and transcript-review.json
- run/video-v6/take-1/recovery-proof.json: interrupted experiment resumes as attempt 2

### Slide 5

- presentation/second-shift-neuroai-90s.mp4 at 1:26–1:29: 0.759 best eligible validation score with 9 electrodes
- run/video-v6/take-1/experiments.json: camp_639cfbea, central9, val_balanced_accuracy 0.7592, n_val 75
- README.md: camp_0f8981ee, 0.774 validation, 0.732 sealed test, 21 electrodes, 75 test trials, subjects 1–5
- eval/checks.json: camp_51b0f538 recovery 8/8; camp_66e4900c constraint 5/5
- Validation guides model selection. The 73.2% sealed test result and reliability checks come from separate campaigns, not the demo.

### Slide 6

- eval/stress.json: 10,000 synthetic distractor notes in a copied real campaign
- eval/stress_current_packet.json: 10,009 total memories, estimated 1,204 tokens within a 4,000 token budget
- README.md: billions of tokens is a target, not an achieved scale
- README.md: project scope and team
- Repository: https://github.com/uyqv/MongoDB-Hackathon
- Conceptual brain and evidence-layer artwork generated with built-in image_gen.
