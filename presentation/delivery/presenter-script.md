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

## Demo cues for rehearsal

These times are relative to the video, not the presentation clock. Let the recorded voice carry this section.

| Video time | What the audience sees | What to remember |
| --- | --- | --- |
| 0:00 to 0:53 | Remember, Decide, Experiment repeats while results accumulate in Atlas | Claude plans. Numerical code measures. The narration explains Jev, Voyage, and memory retrieval. |
| About 0:55 | The worker stops and the working layer fades | Six saved results remain visible in durable memory. |
| About 1:00 to 1:08 | A replacement worker rebuilds context and the interrupted experiment finishes as attempt 2 | Finished work stays saved. The interrupted experiment runs again. |
| About 1:08 to 1:13 | Context clears and the electrode limit changes from 64 to nine | The old results remain, but their eligibility changes. |
| About 1:16 to 1:21 | A new nine-electrode result appears | The search continues under the tighter constraint. |
| 1:22 to 1:25 | The video briefly shows the context reconstruction code | The replacement worker reads campaign state from Atlas. |
| About 1:26 to 1:30 | The best eligible validation result is 0.759 with nine electrodes | This is the 75.9% result on slide 5. Advance when playback ends. |

## Short answers for questions

**What did the crash prove?** Completed results survived the process stopping. The replacement worker rebuilt context and reran the interrupted experiment as attempt two. A separate recovery evaluation passed eight invariants in one scenario. That is not eight independent crash trials.

**Does 64 to nine mean the model originally used all 64 electrodes?** The limit started at 64. The saved results visible before the change used 21 electrodes. Nine is the new maximum, and the later eligible results use nine.

**Why show both 75.9% and 73.2%?** The demo's 75.9% is validation balanced accuracy with nine electrodes. The 73.2% comes from a separate reference campaign's sealed test with 21 electrodes, five participants and 75 test trials. These are different campaigns and splits, so they do not measure an improvement over each other. Balanced accuracy averages recall across the two classes.

**What does MongoDB do?** Atlas stores campaign goals and experimental evidence. Exact reads supply numerical results, including the best eligible result. Voyage embeds research notes, and Atlas Vector Search retrieves relevant notes. Jev routes notes into categories through OpenRouter. Notes remain unverified context.

**Have we tested billions of tokens?** No. That is the long term target. The measured stress check added 10,000 synthetic distractor notes to a real campaign. The current packet used an estimated 1,204 tokens within its 4,000 token budget. This is a bounded context check, not proof of billion-token operation.

**Is this a clinical system or a live brain decoder?** It is an offline research prototype using recorded PhysioNet EEG. The experiments train and validate within each participant. They do not establish performance on new participants or clinical use.

## Before presenting

1. Open `index.html` from this delivery folder in a browser. Keep the assets and media folders beside it.
2. Confirm the speakers work. On slide 4, press Enter and check the movie's existing narration, then leave and return to reset playback.
3. Return to slide 1 and press R to reset the rehearsal timer. Press F for fullscreen.
4. Keep these notes on a second device or printed page. The browser's N shortcut shows notes on the projected screen.
5. Start the movie at 0:50. Stay silent during its narration. At 2:20, move to slide 5 and finish by 2:55.

If playback fails, open `media/second-shift-neuroai-90s-zoom-music.mp4` directly. The PowerPoint backup uses the same script and requires the accompanying MP4 in a separate player.
