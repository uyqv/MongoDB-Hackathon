# Work plan — Sat Sept 26, submission due 5:00 PM

Source plan: `Second_Shift_Build_Plan.md`. Contracts: `docs/CONTRACTS.md`. This file says who does what, and when.

## Decisions already made (don't reopen them)

- **Workload:** PhysioNet eegmmidb, runs 6/10/14, imagined both fists (T1) vs both feet (T2).
- **Protocol (fixed before seeing any numbers):** within-subject. Each subject gets its own model, trained on run 6, validated on run 10, with run 14 sealed as test. Val and test predictions are pooled across subjects 1–5. Smoke mode is subject 1 only. Why: CSP is normally subject-specific, and cross-subject training on 3 people is known to sit near chance. Subjects 6+ stay unexamined.
- **Surface:** 225 allowed configs (`contracts.all_configs()`). **Budget: 10 experiments.** The original 18-config surface was small enough to brute-force, so no agent was needed.
- **Constraint change for the demo:** `max_channels` 64 → 9. The 21 option exists so eligibility is a real filter.
- **Planner:** `anthropic/claude-sonnet-5` via OpenRouter, tool calling, code validation, deterministic fallback.
- **Dashboard:** static HTML + vanilla JS + Chart.js, served by FastAPI, polling every 2 s. No Next.js build step.
- **Comparison test:** 2 arms (`recent_window` vs `evidence`) × 5 scenarios. The rolling-summary arm is cut for time.
- **Jev is required** (Andrew's call, 1:05 PM): David builds `harness/jev.py` (D9), and Andrew wires it into the worker to route planner rationales and notes.

## Timeline

| Time | Andrew (`Andrew`) | David (`david`, agent) |
|---|---|---|
| 12:40–1:15 | **A1** EEG runner on real data. Subject 1 smoke, then subjects 1–5. `tests/test_eeg.py` | **D1** setup, `eval/seed_fake.py` · **D2** `planner.py` + tests |
| 1:15–1:45 | **A2** `store.py`: create campaign, indexes, enqueue/dedupe/reuse, atomic leased claim, fenced commit, lease reclaim | **D3** `memory.py` + vector index + tests |
| 1:45–2:15 | **A3** `worker.py` state machine with a stub planner. Real jobs end to end, verified_result memories written | **D4** API read endpoints + dashboard v1 against fake seed |
| **2:15** | **MERGE 1** (Andrew): `david` → `main`, then `Andrew` → `main`, run tests, push | David's agent pauses and waits for prompt 2 |
| 2:15–2:45 | **A4** `context.py` (both strategies), wire in the real planner and memory. First real LLM-driven campaign, ~10 experiments | **D5** `control.py` + control endpoints + buttons. Dashboard on the real `second_shift` DB |
| 2:45–3:05 | **A5** Recovery proof: SIGKILL mid-queue, restart, done keys reused, running job re-leased as attempt 2. Constraint 64 → 9 re-ranks the incumbent and the campaign continues | **D6** `eval/fixtures.py` (5 scenarios off the real campaign) · **D7** EEG preview panel |
| 3:05–3:25 | **A6** `run_ablation.py`: 2 arms × 5 scenarios, writes `eval/results.json` · wire Jev into the worker | **D8** `docs/ATTRIBUTION.md` · **D9** Jev (required) |
| **3:25** | **MERGE 2 + FEATURE FREEZE at 3:30** | David's agent stops |
| 3:30–3:50 | Clean demo run on a fresh campaign. Both of you watch the dashboard | |
| 3:50–4:25 | README + results table; repo public | Record the one-minute video **on site**; check audio |
| 4:25–4:45 | Submit on Cerebral Valley with **both teammates added**. Check the video link and repo access from a logged-out browser | |
| 4:45–5:00 | Buffer. No code | |

## If you're behind at a checkpoint, cut in this order

1. EEG panel polish (D7): a static PNG of the real trace is fine
2. Comparison test drops to 1 scenario per arm, or the README says "not run"
3. Constraint change button: run it from a Python one-liner instead

**Never cut:** Jev, real-data loop, Atlas as the only state, one visible context rebuild, one kill/restart proof, the video, the Sandbox cluster, dataset attribution.

## Merge mechanics (Andrew only)

```bash
git checkout main && git pull
git merge --no-ff origin/david -m "Merge david: <summary>"   # owner rule means no conflicts expected
git merge --no-ff Andrew -m "Merge Andrew: <summary>"
.venv/bin/python -m pytest -q
git push origin main
git checkout Andrew && git merge main                         # keep your branch current
```
David's agent starts prompt 2 with `git fetch origin && git merge origin/main`.

## Honesty rules (both of you)

- No metric appears anywhere unless the runner computed it. Fake seed data carries `fake: true` and only lives in `second_shift_david`.
- Token counts from the provider are labeled "provider". Everything else is labeled "estimate".
- Report the comparison test result whichever arm wins.
- Don't claim billions of tokens, clinical use, or mid-training checkpointing.
