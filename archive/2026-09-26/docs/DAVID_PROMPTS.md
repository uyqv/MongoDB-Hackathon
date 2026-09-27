# David's prompts

## Before pasting anything (5 minutes, by hand)

1. Get GitHub access to `uyqv/MongoDB-Hackathon` from Andrew, then:
   ```bash
   git clone https://github.com/uyqv/MongoDB-Hackathon.git && cd MongoDB-Hackathon
   git checkout david
   ```
   On Andrew's laptop instead? Use a separate folder: `git worktree add ../MongoDB-Hackathon-david david`, then `cd` there.
2. Get the `.env` file from Andrew over a private channel. Never commit it. In your copy, change two lines:
   - `DB_NAME=second_shift_david`
   - `OPENROUTER_API_KEY=<your own key, the one you redeemed the $10 on>`
3. `python3 -m venv .venv && .venv/bin/pip install -r requirements-worker.txt`
4. Open Claude Code in that folder. Paste **Prompt 1**. When it finishes, text Andrew the summary it prints. Paste **Prompt 2** only after Andrew says merge 1 is done.

If the Atlas connection times out, ask Andrew to add your IP under Atlas → Network Access.

---

## Prompt 1 (paste at ~12:45, runs until ~2:15)

```
You are building half of a hackathon project on the `david` branch of this repo. Andrew is building the other half on the `Andrew` branch at the same time. The deadline is hard (feature freeze 3:30 PM, submission 5:00 PM), so ship working, tested, minimal code. Don't polish.

READ FIRST, in full: docs/WORKPLAN.md, docs/CONTRACTS.md, harness/contracts.py, harness/db.py. CONTRACTS.md is your spec. If it contradicts itself, harness/contracts.py wins.

HARD RULES
- Stay on branch `david`. Never touch `main` or `Andrew`. Never force-push, rebase shared history, or merge anything.
- Only create or edit files that CONTRACTS.md §1 assigns to David. You must NOT edit harness/contracts.py, harness/db.py, requirements.txt, .env.example, .gitignore, or any Andrew-owned file. If you think one of them needs a change, write it in docs/DAVID_LOG.md under "requests for Andrew" and work around it.
- Need a new pip package? pip install it locally and list it in docs/DAVID_LOG.md under "deps needed".
- Never read, print, or commit .env values. Load them with python-dotenv. Confirm DB_NAME is `second_shift_david` before writing to the database, and refuse to run seed_fake against `second_shift`.
- Never invent metrics. Fake UI data must carry `fake: true` and only exist in `second_shift_david`.
- After each task: run its tests, `git add` only your files, commit with a clear message, `git push origin david`.
- Keep docs/DAVID_LOG.md updated: tasks done, test results, anything stubbed or skipped, requests for Andrew, deps needed.
- If something external fails (Voyage, OpenRouter, Atlas vector index), implement the fallback CONTRACTS.md specifies, note it in the log, and move on. Don't spend more than 10 minutes stuck on any one thing.

TASKS, in this order:

D1. Setup + fake seed (≤15 min)
- Check `.venv/bin/python -c "from harness.contracts import all_configs; print(len(all_configs()))"` prints 225.
- Write eval/seed_fake.py. Running `python -m eval.seed_fake` inserts one fake campaign (goal_version 2, constraints {max_channels: 9}, goal_history showing 64 then 9), about 8 fake experiments using real configs from contracts.all_configs() (mixed statuses done/running/queued/failed, fake val_balanced_accuracy in 0.45–0.80, some all64 so eligibility filtering is visible), about 6 memories (at least one verified_result rendered with contracts.render_result_text, 2 synthetic_stress), about 20 events covering worker_start, job_committed, job_reused, worker_killed, context_reset, goal_changed, and one packets doc shaped like contracts.EvidencePacket. Every doc has fake: true. It must be idempotent (delete prior fake docs first).

D2. harness/planner.py + tests/test_planner.py (≤35 min)
- Implement plan() exactly as CONTRACTS.md §5 describes: OpenRouter via the openai SDK, tool calling with propose_experiment and stop, all 4 validation checks, one repair retry, deterministic fallback, provider usage.
- The system prompt explains the objective and the allowed surface (packet["surface"]), and says: only propose untried, eligible configs; cite evidence ids from the packet; never state a metric that is not in the packet; rationale at most 2 sentences.
- Tests use a fake client (inject via a module-level factory or parameter). Cover: valid proposal accepted; invalid config → repair → accepted; repeat of a tried key → repair → fallback; ineligible under max_channels → rejected; unknown evidence id rejected; nothing left → stop.
- One live test, skipped unless LIVE=1, that sends a small real packet and asserts a valid PlannerResult. Run it once with LIVE=1 and log the model id, request id, tokens, and cost in DAVID_LOG.md.

D3. harness/memory.py + tests/test_memory.py (≤30 min)
- Implement embed, ensure_vector_index, add_memory, search_memories, mark_obsolete per CONTRACTS.md §5, against DB second_shift_david.
- Check the real embedding dimension with one call.
- Live test (skipped unless LIVE=1): insert 3 memories for campaign A (one about a csp_lda broad-band result, one failure, one synthetic_stress), plus 1 memory for campaign B and 1 with a different protocol_id. Assert that search for campaign A returns only campaign A and the current protocol, and that the most relevant note ranks first. Wait for the index to be queryable before searching.
- Test the fallback path by forcing embed to raise.

D4. api/main.py + web/ dashboard v1 (≤45 min)
- FastAPI with every GET endpoint in CONTRACTS.md §6 (POST controls come in prompt 2; stub them with 501 for now). Never return `embedding`. Use contracts.is_eligible for the computed `eligible` and the incumbent.
- /api/eeg/preview: return 501 for now.
- web/index.html + web/app.js + web/styles.css, vanilla JS, Chart.js from https://cdn.jsdelivr.net/npm/chart.js. Poll every 2 s. Campaign dropdown defaults to the newest campaign. Six panels:
  1. Goal: objective, state, goal_version, max_channels, budget used/remaining, goal history.
  2. Metric trajectory: done experiments in order on x, val balanced accuracy on y. Eligible points solid, ineligible hollow/grey. Incumbent line. Dashed 0.5 chance line. Plot only values from the API.
  3. Experiment table: label, status, attempt, channels, eligible, val bal acc, proposer (model name or FALLBACK), and a "reused" badge when a job_reused event references it.
  4. Latest context packet: strategy, goal_version it saw, token estimate (labeled "estimate"), then each retrieved memory with memory_id, kind, verified badge, source_ids, score, and retrieval type.
  5. Timeline: worker_start, worker_killed, context_reset, goal_changed, job_reused, lease_expired, stale_commit_rejected, finalized, with local timestamps.
  6. EEG input: placeholder saying "real EEG from PhysioNet loads here" until D7.
  Show a red "FAKE DATA" banner whenever any displayed doc has fake: true.
- tests/test_api.py with FastAPI TestClient against the seeded dev DB.
- Run it: `uvicorn api.main:app --port 8000`. Check every panel renders with seed data.

WHEN D1–D4 ARE DONE, OR AT 2:10 PM, WHICHEVER COMES FIRST: commit and push what works, stub what doesn't, update DAVID_LOG.md, then STOP and print a summary for Andrew under 15 lines: tasks done, tests passing, anything stubbed, requests for Andrew, deps needed, the verified embedding dimension, and the planner's live-call result. Do not start prompt-2 work.
```

---

## Prompt 2 (paste only after Andrew says "merge 1 done", ~2:20, runs until 3:25)

```
Continue on branch `david`. Same hard rules as before, same file ownership.

First: `git fetch origin && git merge origin/main`. Andrew's real worker, store, runner, and context builder are now in the repo. Read docs/WORKPLAN.md and docs/CONTRACTS.md again in case Andrew changed them, and skim harness/store.py and harness/worker.py. Run `.venv/bin/python -m pytest -q` and log the result.

D5. harness/control.py + POST endpoints + dashboard buttons (≤30 min)
- Implement control.py exactly per CONTRACTS.md §5 (constraint change, context reset, start/kill worker with SIGKILL, worker status).
- Wire the POST endpoints from §6 and add buttons: Start worker, Kill worker (SIGKILL), Reset context, and a channel budget selector (9/21/64 + reason text).
- Point the dashboard at the real data. Check with Andrew's real campaign by setting DB_NAME=second_shift in a separate shell for the API only. Read-only checks, no controls pressed against the real DB unless Andrew says so.
- Tests for control.py against second_shift_david: the constraint change bumps goal_version, pushes history, writes an event; reset bumps context_epoch; kill on a dummy `sleep` subprocess writes worker_killed.

D6. eval/fixtures.py + tests/test_fixtures.py (≤30 min)
- Implement build_scenario and score per CONTRACTS.md §8. Source is Andrew's real campaign in DB second_shift (read only; ask Andrew for the campaign id if it's not in DAVID_LOG or the README). Destination is second_shift_eval.
- The 5 scenarios, all labeled synthetic where injected. Memories go through harness.memory.add_memory so they get embeddings.
- Write `python -m eval.fixtures --src-campaign <id>`, which builds all 5 and prints their ids + expected/forbidden evidence ids as JSON to eval/scenarios.json.

D7. EEG preview (≤20 min)
- Implement /api/eeg/preview per CONTRACTS.md §7 (MNE, cached JSON), and panel 6: a C3/Cz/C4 trace plus a PSD chart comparing T1 fists vs T2 feet, captioned with the PhysioNet source.

D8. docs/ATTRIBUTION.md (≤10 min)
- PhysioNet eegmmidb v1.0.0 citation (Schalk et al. 2004, BCI2000, IEEE TBME 51(6):1034–1043; DOI 10.13026/C28G6P; Open Data Commons Attribution License), plus the PhysioNet platform citation from the dataset page. Credit MNE-Python, scikit-learn, FastAPI, Chart.js, Voyage AI, OpenRouter, MongoDB Atlas. State that only the harness, adapter integration, tests, and UI are original work from today.

D9. REQUIRED (not a stretch; do it right after D8 whatever the time): harness/jev.py + tests/test_jev.py
- route_note per its docstring. Verify the model id first: the OpenRouter catalog lists `typesafe/jev-router`, while older docs say `typesafe/jev-1.13` on POST /api/alpha/decisions with {state, questions}. Make one authenticated call and log the returned provider, model, request id, and usage. On any failure, return label "review" with fallback_used true. Do NOT wire it into the worker. A 20-note hand-labeled fixture with ambiguous and adversarial notes, reported as a smoke test, not accuracy.

AT 3:25 PM, OR WHEN DONE: commit, push, update DAVID_LOG.md, then STOP and print a summary for Andrew under 15 lines: what's done, tests passing, what's stubbed, the eval/scenarios.json location, and requests for Andrew.
```

---

## Prompt 3 (paste when Prompt 2 is done, before 3:10 PM)

```
Continue on branch `david`. Same hard rules, same file ownership. First: `git fetch origin && git merge origin/main`, then run the tests.

Context: Andrew ran a real campaign (DB second_shift, camp_0f8981ee): 10 planner calls, 0 fallbacks, $0.085. Two issues surfaced, and these tasks fix them and polish the demo. Do them in order, commit and push after each.

P1. harness/planner.py: no early stop (≤15 min)
- In that campaign the model called `stop` with 1 of 10 experiments left, claiming nothing could beat the incumbent, after exploring only csp_lda in one band. Statement 2 asks for relentless optimization within budget.
- Change the system prompt and code: `stop` is valid only when packet goal.budget.remaining == 0 or no eligible untried config exists. Treat any other stop as a validation failure: one repair asking for a proposal, then the deterministic fallback. When nearby variants look exhausted, the prompt tells the model to explore a different method, band, or window.
- Update tests: premature stop → repair → proposal; stop with remaining 0 → accepted.

P2. Dashboard polish for the video (≤30 min). Recorded at 1440 px wide, so readability matters.
- Header "Second Shift" plus a one-line subtitle. Larger base font, high contrast.
- Timeline: also show fault_injection (red), proposal_rejected, and a compact llm_call line (model, provider input tokens, cost).
- Experiments table: highlight the incumbent row. Expandable row shows the planner rationale and evidence_ids, each id linking to its memory or experiment.
- Goal panel: when campaign.final exists, show final validation vs sealed test balanced accuracy and n_test. Show running totals of provider input tokens and cost from llm_call events, labeled "provider".
- Show the WAITING state and the lease expiry countdown when a job is stuck in running.
- Screenshot every panel with a real campaign from second_shift (read only) and describe the result in DAVID_LOG.md.

P3. eval/stress.py + stress results (≤30 min)
- Copy the real campaign camp_0f8981ee (experiments + verified memories) into a new campaign in DB second_shift_eval. Insert synthetic distractor notes (kind synthetic_stress, synthetic True, varied plausible EEG-ish text), embedded in batches with memory.add_memories: first 1,000, then 10,000 total.
- At 0, 1,000 and 10,000 distractors, measure: search_memories latency p50/p95 over 20 queries; whether the real incumbent's verified_result memory is in the top 4 for a query about the best eligible configuration; the evidence packet token_estimate from harness.context.build_packet (it must stay under budget_tokens as history grows); the total memory count.
- Write eval/stress.json and a markdown table in DAVID_LOG.md. Report whatever happens, including misses.

P4. If D9 (Jev) is still undone, do it now as specified in Prompt 2. Jev is REQUIRED, not a stretch, whatever the time. Andrew wires it into the worker.

AT 3:25 PM, OR WHEN DONE: commit, push, update DAVID_LOG.md, then STOP and print a summary for Andrew under 15 lines.
```
