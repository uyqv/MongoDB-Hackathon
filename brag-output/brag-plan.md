# Brag Plan: Second Shift

## Step 1 rubric (answered before planning)

1. **What is the app?** A research agent whose whole campaign (goal, constraints, every experiment and result) lives in MongoDB Atlas, so you can SIGKILL the worker, wipe the model's context, or change the goal mid run and it rebuilds every decision from durable evidence instead of forgetting.
2. **Most impressive claim.** "Kill the worker with `SIGKILL`, start a new one, and it picks up where the last one died." Backed by the dashboard feed line: "New worker rebuilt the campaign from Atlas · 4 finished experiments reused, none recomputed."
3. **Visual hook.** The dark mission control dashboard in MongoDB green `#00ED64`: the accuracy chart with a red dashed "Killed · resumed" marker and an amber "Limit 64 → 9" marker, plus the red ✕ "Kill worker" button in the header.
4. **What to show from the UI.** The Live view: KPI row (Status, Best result, Experiments, Electrode limit, Model context, real EEG trace), the accuracy chart, the Live activity feed, the Experiments table.
5. **Shortest satisfying video.** About 22 s. Hook, the agent working, three attempts to break it, payoff.
6. **Tone.** Preset `cinematic`. Direction: *crash test trailer, three attempts to make an agent forget, all fail.*
7. **Audio.** Steady cinematic bed (vol-12) with restrained, motion matched UI clicks, one hard glitch hit on the kill, a warm resolve on the rebuild, and a bell on the logo.
8. **Share caption.** We tried to make our research agent forget, and it rebuilt itself from MongoDB Atlas every time.
9. **User flow.** Start worker → experiments stream in (Claude proposes, code measures) → press **Kill worker** (SIGKILL) → a new worker rebuilds the campaign from Atlas → press **Reset context** and cut **Electrodes** 64 → 9 → "Campaign complete · sealed test 0.719".

## What is this app?
Second Shift is a long running research agent that cannot lose its campaign: the memory lives in MongoDB Atlas, not in the model, so killing it, wiping its context, or changing its goal costs nothing it already learned.

## The angle
A crash test trailer. We say up front what we are trying to do ("We tried to make our agent forget."), then attack it three times with the dashboard's own buttons: SIGKILL mid experiment, wipe its context, change the goal. Each attack lands hard (red, glitch, amber) and each recovery is the real dashboard copy showing it rebuilt from Atlas with nothing recomputed. The joke is the premise; the proof is the product UI.

## Hook (first 2-3 seconds)
Near black frame, faint green glow and a live EEG trace drawing across the bottom. "We tried to make our agent forget." lands word by word in heavy Inter; the word *forget.* starts to ghost and blur as the scene holds, like it is being forgotten. Hard cut to the dashboard on the downbeat.

## Key moments (the middle)
- **The agent at work.** The full dashboard tilts in and flattens. Accuracy dots arrive one by one on the beat, the Experiments counter ticks 1/10 → 4/10, Best result climbs 0.692 → 0.745. Caption: "Claude proposes. Code measures."
- **Attempt 1, SIGKILL.** Camera punches into the header. A cursor clicks the red **Kill worker** button. Red flash, glitch, Status flips to "Worker down · campaign state is safe in Atlas". Camera whips to the feed: "Worker killed mid experiment" (red), then "New worker rebuilt the campaign from Atlas · 4 finished experiments reused, none recomputed" (green). The red "Killed · resumed" marker drops onto the chart.
- **Attempts 2 and 3, wipe + change the goal.** Cursor clicks **Reset context**: the Model context KPI drains to 0 tokens, then refills to 1,579 "rebuilt from Atlas every decision". Cursor clicks **9** in the Electrodes selector: Electrode limit turns amber 64 → 9, the amber "Limit 64 → 9" marker drops on the chart, over limit dots hollow out and the best line re-anchors to 0.759 "past results re-ranked, nothing rerun".

## Outro / punchline
The campaign finishes under the new goal: Status flips to "Complete" and Best result reads "sealed test 0.719 · 9 electrodes". The dashboard drops back and blurs out. "It didn't." slams in. Then the logo lockup: the green Second Shift mark, **Second Shift**, "Agents that never lose the plot.", and a small mono footer "Built in one day · MongoDB × Cerebral Valley hackathon".

## User flow worth showing
Start worker → experiments stream in → **Kill worker** → new worker rebuilds from Atlas → **Reset context** → **Electrodes 9** → campaign complete. The centerpiece (Scenes 2-4, about 13 s) is the working dashboard driven by a simulated cursor, not landing page material.

## Tone
- Preset: `cinematic`
- Creative direction: crash test trailer; three attempts to make an agent forget, all fail
- Interpretation: big confident type and trailer pacing for the hook and lockup, but the middle belongs to the real UI shown at readable scale through camera punches; every attack is a hard, colored hit and every recovery is calm and green, so the contrast carries the story.

## Format: landscape — 1920x1080
## Duration: 23.5 seconds
(First drafted at 22.0 s. Holding every line to its reading floor pushed the payoff later, so the final cut runs 23.5 s, still inside the 15-25 s window.)

## Visual identity (from the project)
- Background: `#07090d` with the dashboard's radial green glow `rgba(0, 237, 100, 0.06)` from top right
- Panels: `#0e1117`, `#121620`; lines `#1e2430`, `#2a3140`
- Accent: `#00ed64` (MongoDB green)
- Text: `#eef1f6`; muted `#8c95a8`; faint `#5b6476`
- State colors: red `#ff5d5d` (kill), amber `#ffb547` (goal change), violet `#b692ff` (context / Jev), indigo `#8b9bff` (chart dots), blue `#5cc8ff` (context bar)
- Display font: Inter (800/900 in the product; 900 in video)
- Body / data font: JetBrains Mono
- Strongest visual element: the accuracy chart with the red and amber event markers, and the Live activity feed rows with colored icon tiles

## Share copy (draft)
We tried to make our research agent forget. We killed it mid experiment, wiped its context, and changed its goal, and it rebuilt itself from MongoDB Atlas every time. Second Shift, built in one day at the MongoDB x Cerebral Valley hackathon.

## Audio direction
- Role: cinematic support; a steady bed under the story with a few hard, motion matched accents
- Music: `happy-beats-business-moves-vol-12-by-ende-dot-app.mp3` (steady and clean, 110 BPM)
- Music treatment: starts at 0, quick fade in over 0.4 s, sits at about 0.34, fades out over the last 1.4 s under the lockup so the logo bell rings clean
- Music cue guidance: bundled preset read (`assets/music/cues/happy-beats-business-moves-vol-12-by-ende-dot-app.music-cues.json`, 109.96 BPM). Strong cue locks used: **8.74 s** kill click, **10.93 s** "rebuilt from Atlas". The logo lockup lands on the **20.19 s** beat (the 18.56 s strong cue fell inside the reading hold for "Complete"). Beat grid used: 4.39 / 4.91 / 5.34 / 6.00 for the four chart dots; 3.27 dashboard reveal; 13.64 Reset click; 14.20 context refill; 15.29 electrode 9 click; 16.38 amber marker; 19.10 "It didn't."
- Audio-reactive treatment: subtle; music RMS and bass make the background green glow and the logo mark's glow breathe. No waveform or equalizer visuals.
- SFX posture: moderate but restrained; clicks only where the cursor clicks, one glitch/impact for the kill, one warm resolve for the rebuild, one bell for the logo
- Audio-coupled moments: cursor clicks (Kill worker, Reset context, 9), chart dots landing, context bar drain and refill, "It didn't." slam, logo lockup
- Restraint rule: no sound on every text entrance; nothing louder than the kill hit; no bright high frequency SFX repeated

## Storyboard

### Scene 1 — Hook — 3.27s (0.00-3.27)
Near black `#07090d`, green radial glow top right, a live EEG trace (the dashboard's "Input · real EEG" motif) drawing across the lower third. Small mono kicker top left: "SECOND SHIFT · CRASH TEST". Headline, heavy Inter, anchored left: "We tried to make our agent forget." Words arrive 0.3-1.0 s, then hold. From about 1.9 s the word *forget.* ghosts: letters lose opacity and pick up blur and slight drift, like a memory fading.
Sequential/interaction: yes, headline words arrive one by one (fast in, then a 2.2 s hold, above the 7 word reading floor of 2.1 s)
Audio intent: set a serious, slightly ominous opening under a clean bed
Audio-coupled idea: none on the words; let the music's first beats carry it
Music: bed fades in
Transition mood: hard cut on the 3.27 downbeat → Scene 2

### Scene 2 — The agent at work — 3.82s (3.27-7.09)
The recreated dashboard (header with Start/Kill/Reset buttons and Electrodes 64/21/9 selector, KPI row, accuracy chart, Live activity, Experiments table) tilts in from a 3D angle and flattens to full frame by about 4.4 s, then the camera pushes in slowly. Status: "Running · measuring on real EEG". Four accuracy dots land one by one (0.692, 0.745, 0.641, 0.665) as matching rows fill the Experiments table; Experiments ticks 1/10 → 4/10; Best result 0.692 → 0.745. Feed shows "Claude proposed CSP · 13–30 Hz · 21 electrodes" and "Experiment #2 measured 0.745". Caption panel lower left: "Claude proposes. Code measures." (4 words, held ≥ 1.5 s).
Sequential/interaction: yes, 4 chart dots and table rows arrive one by one on beats (~0.5 s apart; these are dots, not text, so every beat is fine; the table rows are secondary)
Audio intent: the product comes alive; confident, steady
Audio-coupled idea: soft reveal hit on the dashboard landing; quiet drops on the first and last dot
Music: steady bed
Transition mood: camera move (punch in), no cut → Scene 3

### Scene 3 — Attempt 1: SIGKILL — 5.76s (7.09-12.85)
Chapter panel (lower left, dashboard card style): "ATTEMPT 1 OF 3" + "Kill it mid experiment." Camera punches into the header, Status KPI and chart. A cursor glides to the red ✕ **Kill worker** button and clicks on 8.74 s. Red flash, short glitch shake, Status KPI flips to "Worker down · campaign state is safe in Atlas" (red). Camera whips to the Live activity feed: red row "Worker killed mid experiment · SIGKILL while running #5" slides in. On 10.93 s the green row lands on top: "New worker rebuilt the campaign from Atlas · 4 finished experiments reused, none recomputed". The red dashed "Killed · resumed" marker is on the chart when the camera next pulls back. The camera holds on the feed until 12.85 s so both rows get about 2 s of reading time.
Sequential/interaction: yes, simulated cursor click on Kill worker; two feed rows arrive in order (red at 9.83 s, green at 10.93 s, both held to 12.85 s)
Audio intent: the hit should feel like breaking something; the recovery should feel calm and certain
Audio-coupled idea: mouse click at the press, glitch + heavy soft impact on the kill, warm resolve on the rebuild row
Music: bed continues underneath
Transition mood: camera whip (dramatic) → Scene 4

### Scene 4 — Attempts 2 and 3: wipe it, change the goal — 4.45s (12.85-17.30)
Camera frames the header right plus the Electrode limit, Model context and EEG KPIs and the feed. Chapter panel: "ATTEMPT 2 OF 3" + "Wipe its context." Cursor clicks **Reset context** on 13.64 s: Model context drains 1,512 → 0 tokens, sub label "Context wiped", feed logs "Context wiped · the next decision is rebuilt from Atlas alone"; on 14.20 s it refills to 1,579 "rebuilt from Atlas every decision". Chapter panel swaps: "ATTEMPT 3 OF 3" + "Change the goal." Cursor clicks **9** on 15.29 s. Cursor clicks **9** in the Electrodes selector (turns amber). Electrode limit KPI 64 → 9 in amber, sub "cut from 64 · goal v2". Camera eases back to the chart: the amber dashed "Limit 64 → 9" marker drops, dots measured over the new limit hollow out, the green best line re-anchors to the 0.759 nine electrode result. Caption: "Past results re-ranked. Nothing rerun."
Sequential/interaction: yes, two simulated clicks; context bar drain then refill; marker drop
Audio intent: two quick, clean interventions; the goal change lands with weight
Audio-coupled idea: click on Reset, soft switch on refill, click on 9, soft impact when the amber marker lands
Music: bed continues
Transition mood: pull back, then dramatic dim → Scene 5

### Scene 5 — Payoff and lockup — 6.20s (17.30-23.50)
Camera settles on Status, Best result, Experiments, Electrode limit and the chart. The last three nine electrode results land (17.47-17.83 s), the best line stretches across them, and on 18.02 s Status flips to "Complete · sealed test set scored once" while Best result reads "0.759 · sealed test 0.719 · 9 electrodes" (the feed logs "Campaign complete · sealed test 0.719" off camera). On 18.98 s the dashboard drops back and blurs out; on 19.10 s "It didn't." slams in, big. On 20.19 s the lockup: green Second Shift logo mark (breathing glow with the music), **Second Shift**, then "Agents that never lose the plot." and a small mono footer "Built in one day · MongoDB × Cerebral Valley hackathon". Hold to the end, no fade to black.
Sequential/interaction: yes, "It didn't." then logo, name, tagline, footer in order (tagline and footer each held ≥ 2 s)
Audio intent: release; a clean bell on the lockup and the bed fading underneath
Audio-coupled idea: soft impact on "It didn't.", bell on the logo
Music: bed fades out under the lockup
Transition mood: final hold

**Scene durations:** 3.27 + 3.82 + 5.76 + 4.45 + 6.20 = **23.50 s**

**Poster frame:** 11.8 s (the killed and rebuilt feed rows beside "ATTEMPT 1 OF 3 · Kill it mid experiment."), baked in as frame 0.

**Music mood for this video:** cinematic, steady
**Audio summary:** a clean bed under a serious hook, UI clicks as the cursor attacks the dashboard, one hard glitch hit on the kill answered by a warm resolve, and a bell on the logo as the music fades.
