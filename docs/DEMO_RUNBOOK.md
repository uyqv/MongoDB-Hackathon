# Demo runbook and one minute video

Record on site. Record the real run at normal speed, then cut it down to 60 seconds. If a cut skips time, put a small "cut" or "sped up" caption on it. Never show a replay as if it were live.

## Setup (3:30 PM, about 5 minutes)

Terminal A, the dashboard:
```bash
cd MongoDB-Hackathon && git checkout main && git pull
DB_NAME=second_shift .venv/bin/uvicorn api.main:app --port 8000
```
Open http://localhost:8000 in a clean browser window at 1440 px wide or more.

Terminal B, a fresh campaign that is created but not started:
```bash
DB_NAME=second_shift .venv/bin/python -m harness.worker --new --mode demo --max-channels 64 --budget 10 --create-only
# prints camp_xxxxxxxx; select it in the dashboard dropdown
```

Check: `.venv/bin/python -m pytest -q` is green, and the dashboard shows the new campaign with 0 experiments and the real EEG panel.

## The run (about 3 minutes real time)

1. **Start.** Terminal B runs the worker with fault injection, so the crash lands mid job:
   ```bash
   DB_NAME=second_shift .venv/bin/python -m harness.worker --campaign camp_xxxxxxxx --crash-after-claim 4
   ```
   Experiments stream into the table and the chart. The context packet panel shows the retrieved evidence IDs.
2. **Crash.** On the 4th job the worker logs `fault_injection` and SIGKILLs itself. The dashboard shows a job stuck in `running`.
3. **Recover.** Press **Start worker** in the dashboard. The timeline shows `worker_start` with "resuming: 3 done experiments will be reused, not recomputed". Then `WAITING` while the dead lease runs out, then `lease_expired`, and the job reruns as attempt 2.
4. **Change the goal.** After about 6 experiments, press **Reset context**, then set the channel budget to **9** with reason "new headset has 9 electrodes". The incumbent switches to the best 9 channel result already measured, with no new job. Every later proposal uses 9 channels, and the packet panel shows goal version 2.
5. **Finish.** The worker finalizes and scores the sealed test set once. The goal panel shows the final validation and test numbers.

Backup, if a live step misbehaves: `python -m eval.demo_checks all` reproduces the recovery and constraint proofs end to end. Record its PASS output instead.

## Dry run notes (1:42 PM, `camp_9099ead8`, every beat worked)

- The whole run took about 2 minutes: crash on the 4th job at 0:41, restart plus lease wait about 5 s, 6 done at 1:10, finished at 2:00. 10 planner calls, 0 fallbacks, $0.10. Jev routed 10 of 10.
- Press **Start worker only after the terminal worker has crashed.** An earlier run had two workers overlap. Nothing broke (the lease serialized them), but it muddies the story.
- After 64 to 9, the incumbent can be empty if no 9 channel experiment ran yet. Then the right line is "nothing measured qualifies, so it keeps searching under the new goal", and the next proposals are all 9 channel. Don't promise a switch on camera unless the table already shows a central9 row.
- The timeline panel fills with `llm_call` lines, so by the end the crash and restart events have scrolled off. Film them when they happen, or scroll the timeline.
- 9 channel results are weaker: the sealed test for the 9 channel pick was 0.547. Don't narrate it as an improvement.

## Storyboard (60 s)

| Time | Show | Say |
|---|---|---|
| 0 to 8 s | Goal panel and the real EEG panel | "Long running agents lose the reasoning behind old experiments. Second Shift rebuilds every decision from durable evidence in MongoDB." |
| 8 to 20 s | Experiments streaming, one packet with evidence IDs | "Claude picks the next EEG experiment from a fixed menu and cites evidence. Code computes every number." |
| 20 to 33 s | Fault injection, stuck job, Start worker, timeline | "We kill the worker mid job. A new process rebuilds the campaign from Atlas. Finished work is reused, and the orphaned job reruns as attempt 2." |
| 33 to 47 s | Reset context, channel budget 64 to 9, incumbent switch, packet with goal v2 | "We wipe the context and cut the electrode budget to 9. It re-ranks what it already measured and keeps going under the new goal." |
| 47 to 56 s | README results: checks, comparison table, tokens, cost | Only measured numbers: checks passed, comparison result, tokens, cost. |
| 56 to 60 s | Code and the Atlas collections | "One persistent mission, bounded context, decisions grounded in measured results." |

## Submission (4:25 PM)

- The repo is public at github.com/uyqv/MongoDB-Hackathon. Open it logged out and confirm the README renders.
- Video link: open it logged out and confirm audio plays.
- Cerebral Valley: description from the README's first paragraph plus measured results. Both teammates added.
