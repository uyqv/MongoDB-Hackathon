# Narration: one-minute video

Record this on site, in your own voice, over the finished cut (`clips/narration.m4a`). It comes to about 130 words, a comfortable pace for 60 seconds. The timings match `clips/cut.txt` from `scripts/cut.sh --template`.

| Time | On screen | Say |
|---|---|---|
| 0–7 | 3D `forget` | Long-running agents forget. Their context fills up, and the oldest decisions fall out: what they tried, and why. |
| 7–13 | 3D `packet` | Second Shift keeps the whole campaign in MongoDB Atlas and builds each decision from a small briefing: the goal, the best result, recent runs, and retrieved evidence. |
| 13–27 | Dashboard, real campaign | Here it is tuning a real EEG classifier on PhysioNet data. The model only proposes the next experiment. Code runs it and writes the score to Atlas. |
| 27–33 | 3D `kill` | Now we kill the worker. |
| 33–41 | Dashboard, kill and restart | A new worker starts, reads the campaign back from Atlas, and carries on without redoing finished work. |
| 41–46 | 3D `constraint` | Then we change the rules: nine electrodes instead of sixty-four. |
| 46–53 | Dashboard, 64 → 9 | It re-checks every result against the new goal, and the incumbent moves to the best one that still qualifies. |
| 53–60 | Flat `numbers` | A log records what was true. Second Shift knows what is still true. |

Only say what the dashboard footage actually shows. If the restart clip shows a running job re-leased as attempt 2, say "re-runs only the job that was interrupted" rather than "without redoing".
