# Hyperframes Composition Brief: Second Shift

## Objective
Create a short launch style brag video for Second Shift, a research agent whose memory lives in MongoDB Atlas so it survives SIGKILL, context wipes, and goal changes.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080, 30 fps
- Duration: 23.5 seconds (drafted at 22.0; reading-time holds pushed the payoff later)

## Source Material
- Project root: repository root (this worktree)
- Primary files read: `web/index.html`, `web/styles.css`, `web/app.js` (feed copy and status strings), `README.md`, `docs/dashboard.png`, `docs/DEMO_RUNBOOK.md`, `scripts/video/narration.json`
- Product name: Second Shift
- Tagline / strongest claim: "Agents that never lose the plot" · "Kill the worker with SIGKILL, start a new one, and it picks up where the last one died."
- Key UI moment to recreate: the dashboard Live view (header buttons, KPI row, accuracy chart with red "Killed · resumed" and amber "Limit 64 → 9" markers, Live activity feed, Experiments table), driven by a simulated cursor
- Copy that must appear verbatim (from `web/app.js` / `web/index.html`):
  - Kill worker · Reset context · Start worker · Electrodes 64 21 9
  - Worker killed mid experiment · SIGKILL while running #5
  - New worker rebuilt the campaign from Atlas · 4 finished experiments reused, none recomputed
  - Worker down · campaign state is safe in Atlas
  - Context wiped · rebuilt from Atlas every decision
  - Electrode limit 64 → 9 · past results re-ranked, nothing rerun
  - Killed · resumed · Limit 64 → 9
  - Campaign complete · sealed test 0.719
  - Claude proposes · code measures
  - Agents that never lose the plot

## Creative Direction
- Tone preset: `cinematic`
- Creative direction: crash test trailer; three attempts to make an agent forget, all fail
- Interpretation: trailer scale type for hook and lockup; the middle is the real UI at readable scale through camera punches; attacks are hard colored hits, recoveries are calm and green
- Angle: we state the goal ("We tried to make our agent forget."), attack the agent three times with the dashboard's own buttons, and let the real feed copy prove it rebuilt from Atlas each time
- Hook: "We tried to make our agent forget." with the word *forget.* ghosting away as it holds
- Outro / punchline: "It didn't." → Second Shift lockup, "Agents that never lose the plot."
- Avoid:
  - Generic SaaS language
  - Abstract filler visuals
  - Redesigning the dashboard; recreate it faithfully and scale it with camera moves
  - Claims beyond the README's measured results

## Visual Identity
- Background: `#07090d` with radial `rgba(0,237,100,.06)` glow top right
- Panels: `#0e1117` / `#121620`; lines `#1e2430` / `#2a3140`
- Text: `#eef1f6`; muted `#8c95a8`; faint `#5b6476`
- Accent: `#00ed64`; state colors red `#ff5d5d`, amber `#ffb547`, violet `#b692ff`, indigo `#8b9bff`, blue `#5cc8ff`
- Display font: Inter (bundled; 900 for video headlines, the product uses 800)
- Body font: Inter 400/700; data and labels JetBrains Mono (bundled)
- Visual references from the project: logo mark (rounded green square with a single wave stroke), KPI cards, feed rows with colored icon tiles, dashed chart markers, amber segmented Electrodes control

## Storyboard
Use the storyboard in `brag-output/brag-plan.md` as the creative contract.

Scene summary:
1. Hook — 3.27s — "We tried to make our agent forget." over glow and a drawing EEG trace; *forget.* ghosts
2. The agent at work — 3.82s — dashboard tilts in, 4 dots land on the beat, Experiments 1 → 4, caption "Claude proposes. Code measures."
3. Attempt 1: SIGKILL — 5.76s — cursor clicks Kill worker (8.74 s), red glitch, Worker down, feed rows killed (9.83 s) → rebuilt (10.93 s)
4. Attempts 2 and 3 — 4.45s — Reset context (13.64 s) drains/refills tokens, Electrodes → 9 (15.29 s), amber marker (16.38 s), dots re-ranked
5. Payoff and lockup — 6.20s — Complete · sealed test 0.719, "It didn't." (19.10 s), logo lockup (20.19 s)

Implementation notes: one monolithic `index.html` (lint suggests sub-compositions; kept as one file because the dashboard is a single camera world). All changing dashboard text is a pure function of time driven from one `onUpdate`. The raw music file is not committed to the repo (license unverified); copy it from the brag skill's `assets/music/` before re-rendering.

## Audio
- Audio role: cinematic support
- Audio arc: bed in under the hook, UI clicks with the cursor, one hard hit on the kill, warm resolve on the rebuild, bell on the lockup as the bed fades
- Music: `assets/music/happy-beats-business-moves-vol-12-by-ende-dot-app.mp3`
- Music treatment: 0.4 s fade in, bed around 0.34, fade out over the last 1.4 s
- Music cue guidance: bundled preset `~/.claude/skills/brag/assets/music/cues/happy-beats-business-moves-vol-12-by-ende-dot-app.music-cues.json` (109.96 BPM). Strong cues to lock: 8.74 (kill click), 10.93 (rebuilt row), 18.56 (logo). Beat grid for Scene 2 dots: 4.39, 4.91, 5.34, 6.00.
- Audio-reactive treatment: subtle; RMS/bass drive the background glow and the logo mark glow. No visualizer graphics.
- Audio-coupled moments:
  - Scene 2 dashboard landing — soft reveal hit
  - Scene 2 dots — quiet drop on first and last
  - Scene 3 Kill worker — mouse click + glitch + heavy soft impact
  - Scene 3 rebuilt row — warm resolve
  - Scene 4 Reset context / 9 — clicks; refill — switch; amber marker — soft impact
  - Scene 5 "It didn't." — soft impact; logo — bell
- SFX selection guidance: low HF risk files for clicks and repeated moments (`interface/click_00x`, `impactSoft_medium_00x`), medium for the isolated kill and bell
- SFX analysis guidance: `~/.claude/skills/brag/assets/sfx/sfx-analysis.md`
- Exact SFX choice: chosen during composition to match the implemented animation
- Audio files: copied into `brag-output/composition/assets/`

## Hyperframes Instructions
Built with the `hyperframes-core`, `hyperframes-animation`, `hyperframes-creative`, `hyperframes-keyframes`, and `hyperframes-cli` skills (read from the upstream `heygen-com/hyperframes` repo), without the `hyperframes` entry-point interview.

Requirements:
- Show real UI, copy, and visuals from the source project.
- Keep all text readable in the final render.
- Keep the video within 15-25 seconds.
- Include the planned music and SFX layer.
- Treat music cues as optional timing hints; readability first.
- Use local assets for audio.
- `hyperframes check` is the single gate before render.
