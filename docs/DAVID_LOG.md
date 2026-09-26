# David's log

Branch `david`. Dev DB `second_shift_david`.

## Tasks done

- **D1** setup + `eval/seed_fake.py`. `all_configs()` = 225. Seed is idempotent (deletes `fake: true` docs first) and refuses any DB other than `second_shift_david`. Inserts 1 campaign (`camp_fa4e0001`, goal_version 2, 64 then 9 channels), 8 experiments, 6 memories, 31 events, 1 packet. All docs carry `fake: true`.

- **D2** `harness/planner.py`: OpenRouter via openai SDK, `tool_choice="required"`, tools `propose_experiment` / `stop`, 4 code checks (normalize, eligible, untried key, evidence ids in packet), one repair retry via a tool-result message, deterministic fallback (`model="deterministic-fallback"`), provider usage summed across both calls. Pure: no DB writes. If no eligible untried config exists it returns `stop` without calling the model. Provider/network exceptions also fall back and never raise.
  - Live call ~12:42 ET: model `anthropic/claude-sonnet-5`, request id `gen-1790441024-0rMRYMsxZqircOq56Cq6`, 2067 input / 202 output tokens (provider), cost $0.006154. Valid proposal, no fallback, cited the incumbent.
- **D3** `harness/memory.py`: Voyage `voyage-3.5`, **verified dimension 1024** (one live call). `memories_vec` created in `second_shift_david` (cosine, filters campaign_id/protocol_id/status/kind/synthetic), READY + queryable. `search_memories` filters inside `$vectorSearch`, projects out `embedding`, returns `vectorSearchScore`; falls back to an exact filtered find (newest first, `retrieval="fallback"`) when embed or vector search fails or returns nothing. Extra helper `add_memories(db, docs)` embeds in one call per 128 texts (for fixtures). Query embeddings are cached in-process (`lru_cache`), Voyage client uses `max_retries=3`.
  - Live test: 3 campaign-A/current-protocol memories returned, other campaign and other protocol excluded, broad-band csp_lda note ranked first (0.852 vs 0.704, 0.624).
- **D4** `api/main.py` + `web/index.html`, `web/app.js`, `web/styles.css`. Every GET endpoint in CONTRACTS §6; `/api/eeg/preview`, `/api/worker/status` and the four POST controls return 501 until prompt 2. `embedding` is stripped recursively from every response. `eligible` and `incumbent` are computed on read with `contracts.is_eligible`. Six panels render against the seed (checked with a headless Chrome screenshot), FAKE DATA banner shows when any displayed doc has `fake: true`, polling every 2 s.
  - Run: `.venv/bin/uvicorn api.main:app --port 8000`, open http://localhost:8000.

### Prompt 2

- 13:00 ET: merged `origin/main` (merge 1 + Andrew's A1-A3, A5, A6 scaffold) into `david`, no conflicts. Full suite after merge: 41 passed, 2 live skipped.
- Andrew: Voyage card added, so full rate limits apply. D6 source campaign (from Andrew): **`camp_0f8981ee` in DB `second_shift`**. After prompt 2, go straight to prompt 3 (no merge wait).
- **D5** `harness/control.py` + POST endpoints + dashboard buttons (Start worker, Kill worker SIGKILL, Reset context, channel budget 9/21/64 + reason). `change_constraint` does the `$inc goal_version`, `$set constraints`, and `$push goal_history` in ONE `find_one_and_update` guarded on the old `goal_version` (so version and history can never disagree), then logs `goal_changed`. `start_worker` strips empty exported keys from the child env (so the worker's `load_dotenv()` fills them from `.env`), pins the child's `DB_NAME` to the API's DB, and runs it in its own session; `kill_worker` SIGKILLs, reaps, logs `worker_killed`, removes `run/worker.json`. Endpoint errors: 400 bad max_channels, 404 unknown campaign, 409 worker already running.
  - Read-only check against the real DB (`DB_NAME=second_shift` on port 8001, no buttons pressed): campaign `camp_51b0f538` rendered all panels, vector retrieval live (scores 0.75), planner usage from the provider, `fault_injection` and resumed `worker_start` on the timeline.
  - The worker pill only tracks workers the API started (`run/worker.json`). A worker Andrew starts from the CLI shows as "API worker: stopped", and Start worker would launch a second one, so don't press it while a CLI worker runs.
- **D6** `eval/fixtures.py` + `tests/test_fixtures.py`. `build_scenario` copies the source campaign's finished experiments (re-keyed to the new campaign, `copied_from` set, results untouched, only `created_at` reordered) and re-renders a verified_result/failure memory per copy with `contracts.render_*_text`, embedded through `memory.add_memories`. Injected records are all `synthetic: True, kind: "synthetic_stress"`. `score()` returns the contract keys plus `expected_in_packet` (did the context strategy surface the evidence at all) and, for `buried_failure`, `repeated_bad_family`.
  - 13:05 ET: built from `camp_0f8981ee` into `second_shift_eval` (vector index `memories_vec` created there, READY; 1,846 memories, 0 without embedding). `eval/scenarios.json`:
    - `buried_best_eligible`: `camp_5abba2f8` (9 experiments, 200 synthetic notes)
    - `buried_failure`: `camp_9e778811` (9 experiments, 200 synthetic notes)
    - `obsolete_protocol`: `camp_64a220b5` (10 experiments, 200 synthetic notes)
    - `goal_changed`: `camp_75ae27d2` (9 experiments, 200 synthetic notes)
    - `distractor_flood`: `camp_99e13e91` (9 experiments, 1000 synthetic notes)
  - `buried_failure`: the source has no failed experiment, so the worst-scoring one (csp_lda · beta_13_30 · all64, 0.571) sits first. "Family" = method + band + channels, because every real experiment is csp_lda · beta_13_30.
  - `obsolete_protocol`: the trap is a synthetic experiment under a different protocol_id (evaluator `eeg-eval-0`), val bal acc = real incumbent + 0.12, created last. `store.incumbent` excludes it; the recent_window packet shows it.
  - Rebuild: `python -m eval.fixtures --src-campaign camp_0f8981ee --reset` (reset deletes only `fixture: true` docs and their packets/events).
- **D7** `/api/eeg/preview` + panel 6 (13:08 ET). Real `S001R06.edf` via `eegbci.load_data(1, [6])` + `standardize`: C3/Cz/C4, 1-40 Hz zero-phase FIR, 6 s from the first task cue, shown at 80 Hz; Welch PSD 4-40 Hz on 1-3 s epochs, T1 fists (n=7) vs T2 feet (n=8). Cached to `data/eeg_preview.json` (gitignored). Returns 503 with the reason if the download fails. Caption names the PhysioNet source and says it is display only.
- **D8** `docs/ATTRIBUTION.md` (13:08 ET): eegmmidb v1.0.0 (DOI 10.13026/C28G6P, ODC-By 1.0), Schalk et al. 2004 BCI2000 citation, Goldberger et al. 2000 PhysioNet citation, software/service table with licenses, and the statement of what is original work from today.
- Andrew: Jev (D9) is REQUIRED now, not stretch; do it after D8 regardless of time; do not wire it into the worker.
- **D9** `harness/jev.py` + `tests/test_jev.py` (13:10 ET). Model id checked first: the catalog's `typesafe/jev-router` is a chat-completions router (different product); the Decisions API `POST https://openrouter.ai/api/alpha/decisions` with `{model: "typesafe/jev-1.13", state, questions}` works. `questions` must be a record: one `choice` question `route` whose criteria are the 4 labels. Any HTTP error, exception, unknown label, out-of-range confidence, or confidence < 0.6 returns `label: "review", fallback_used: true` with the reason. Note text capped at 2,000 chars. No DB writes; NOT wired into the worker (Andrew does that).
  - Authenticated call: provider `TypeSafe`, model `typesafe/jev-1.13-20260917`, request id `gen-dec-1790442586-oeMIa4WHgWSzvMgDcADH`, usage 356-ish in / ~41 out tokens, cost $0.00002 per call.
  - **Smoke test (not accuracy):** 20 hand-labeled notes (4 per label plus 4 ambiguous/adversarial), agreement 19/20, total cost $0.000395. All 4 prompt-injection / unsupported-metric / goal-change notes went to `review` at confidence 1.0. The one miss: "mu band failed... or maybe it was beta, the log got overwritten" (hand label `review`) went to `failure_memory` at 0.82. Hand labels are ours and n=20, so this says the integration works, not how accurate Jev is.

### Prompt 3

- 13:11 ET: merged origin/main (prompt 3 added to DAVID_PROMPTS.md). Suite: 59 passed, 3 live skipped.
- **P1** planner no early stop. `stop` validates only when `goal.budget.remaining == 0` or no eligible untried config exists; any other stop is a validation failure, gets one repair ("propose one; explore a different method, band, or window"), then the deterministic fallback proposes. With `remaining == 0` the planner returns `stop` without calling the model. System prompt now says optimize relentlessly within budget. New tests: premature stop, repair, proposal; double premature stop, fallback proposal; stop at remaining 0 accepted; no call when budget spent. Live call re-run after the change: valid proposal, no fallback.
- **P2** dashboard polish for the 1440 px video (13:14 ET). Base font 15.5 px, 26 px title with subtitle, higher-contrast palette. Timeline adds `fault_injection` (red), `proposal_rejected`, and a compact `llm_call` line (model or FALLBACK, action, provider input tokens, cost). Experiments: incumbent row highlighted with a green bar and badge; click any row to expand the planner rationale, request id, and `evidence_ids`, where experiment ids scroll to and flash their row and memory ids open the memory text inline. Goal panel: state pill (WAITING pulses amber), running totals from `llm_call` events (calls, fallbacks, provider input/output tokens, cost, labeled "provider"), a lease countdown for every running job ("expires in N s", then red "expired N s ago, waiting for reclaim"), and when `campaign.final` exists a block with validation vs sealed-test balanced accuracy, test F1 and n_test. API: `/api/campaigns/{cid}` adds computed `llm_usage` and `running`. URL options `?campaign=<id>` pins a campaign and `?expand=all` opens every row (for the video).
  - Screenshots, read only, `DB_NAME=second_shift`, `camp_0f8981ee` at 1440 px: goal panel shows DONE, 9 used / 1 remaining of 10, incumbent 0.773 val (csp_lda · beta_13_30 · w0.5_2.5 · motor21 · n=6), 10 planner calls, 0 fallback, 30,341 in / 2,439 out tokens, $0.0851 (provider), final block validation 0.773 vs sealed test 0.732, F1 0.729, n_test 75. Trajectory: 9 eligible points, best-so-far step line 0.692, 0.745, 0.773. Experiments: 9 rows, row 5 highlighted as incumbent, every expanded row shows its rationale and linked evidence (row 1 uncited, rows 2-9 cite 1-2 ids). Packet panel: evidence strategy, 940 tokens (estimate) of 4,000, last planner action `stop` (the premature stop P1 now blocks). Timeline: worker_stop, finalized (val 0.773, test 0.732, n=75), llm_call lines with provider tokens and cost. EEG panel renders. The WAITING pill and lease countdown were checked on the fake campaign ("lease expires in 35 s").
  - The real campaign's `llm_usage` total ($0.085072, 10 calls, 0 fallbacks) matches Andrew's report.
- **P3** `eval/stress.py` + `eval/stress.json` (13:18 ET). Copied `camp_0f8981ee` (9 experiments, 9 re-rendered verified memories) into `camp_ed8675ea` in `second_shift_eval`, then added synthetic distractors through `memory.add_memories` in 1,000-note batches. Latency = end-to-end `search_memories` (Voyage query embedding + `$vectorSearch`) from David's laptop, 20 distinct queries per level, query cache cleared.

| distractors | memories | insert+embed s | index sync s | search p50 ms | search p95 ms | incumbent memory in top 4 | top-4 kinds (incumbent query) | packet tokens (estimate) / budget | packet retrieved kinds |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 9 | 0.0 | 0.0 | 239.6 | 317.5 | NO | 4x verified_result | 940 / 4000 | 4x verified_result |
| 1,000 | 1,009 | 7.2 | 3.5 | 261.4 | 309.7 | NO | 4x verified_result | 780 / 4000 | 4x synthetic_stress |
| 10,000 | 10,009 | 105.1 | 4.5 | 726.5 | 4613.5 | NO | 4x verified_result | 781 / 4000 | 4x synthetic_stress |

  - **Miss, reported as-is:** the real incumbent's verified_result memory (`m_ce9f5f81e5fd`, val 0.773) is NOT in the top 4 for the "best eligible configuration" query at any level, including 0 distractors. The top 4 are other verified results with near-identical scores (0.788-0.791): embeddings cannot rank by a number inside the text. The evidence packet still carries the incumbent at every level through the exact `store.incumbent` read, so the planner never loses it.
  - Filtering held: the incumbent query's top 4 stayed all verified_result even at 10,000 distractors. The packet's generic query did not: its 4 retrieved slots flip to synthetic notes once distractors exist (same finding as D6).
  - Packet size stays well under budget as memory grows (940 then 781 tokens estimated, of 4,000), because retrieval is capped at k=4 and the recent window is fixed.
  - Latency: p50 grows from ~240 ms to ~727 ms and p95 reaches ~4.6 s at 10,000; much of that is the Voyage embedding round trip, measured from a laptop on venue wifi, not isolated Atlas time.

## Tests

- `tests/test_planner.py`: 9 passed, 1 live skipped by default; live passed with `LIVE=1`.
- `tests/test_memory.py`: 2 passed (fallback path with embed forced to raise; verified-only rule), live vector test passed with `LIVE=1`. Tests refuse any DB other than `second_shift_david`.
- `tests/test_api.py`: 7 passed (TestClient against the seeded dev DB).
- Full suite 12:51 ET: 27 passed, 2 live skipped.
- `tests/test_jev.py`: 9 passed (request shape is not chat, 5 failure paths to review, missing key, empty note, truncation, fixture shape) + live smoke with `LIVE=1`. Full suite 13:10 ET: 59 passed, 3 live skipped.
- control.py tests live in `tests/test_api.py` (CONTRACTS §1 gives David no `test_control.py`): constraint bump + history + event, context_epoch bump, start/kill/status on a dummy sleep process, and all POST endpoints. Full suite 13:00 ET: 44 passed, 2 live skipped.

## Stubbed / skipped

## Assumptions Andrew should check

- `/api/campaigns/{cid}` computes `used` as the count of experiment docs in the campaign (any status) and `remaining = budget.max_experiments - used`. Change if the worker counts budget differently.
- `/api/campaigns/{cid}/events` without `after` returns the latest `limit` events (ascending), so the timeline shows recent history on long runs. With `after`, it returns the next `limit` after that ts.
- `/api/campaigns/{cid}/packets/latest` sorts packets by `ts` descending, matching the `packets {campaign_id:1, ts:-1}` index. Packets need a `ts` field.
- Experiments get an extra computed `reused: true` when a `job_reused` event has `payload.experiment_id` equal to their `_id`.

- Confirmed after merge: `job_reused.payload.experiment_id` matches store.enqueue; `worker_start.payload.counts.done` drives the timeline's resumed count.

## Requests for Andrew

- **Finding, not tuned away:** on the real fixtures, the evidence packet's 4 retrieved memories are ALL synthetic distractors in every scenario (scores 0.77-0.79; verified results rank lower). The evidence arm still carries the expected evidence in 4 of 5 scenarios through the exact incumbent read; `buried_failure` is surfaced by neither arm. The distractors share the query's vocabulary (bands, channel sets, methods) with no results in them. Options in `context.py` (yours): pass `kinds=["verified_result","failure"]`, or add a `synthetic: False` filter, to `search_memories`. Either one is a design change, so report whichever arm wins on the version you run.

- ~~Voyage key rate limit~~ resolved: Andrew added a card. Original note: The Voyage key in `.env` has no payment method, so it is capped at 3 requests/min and 10K tokens/min (live error text says so). The worker embeds every memory and every search query, and D6 embeds 1,000+ distractor notes. Add a payment method at dashboard.voyageai.com (free 200M tokens still apply), or the demo will run on the fallback retrieval path.

## Deps needed

## Environment notes

- `harness/planner.py` exposes `client_factory` (module-level) so tests inject a fake client.
- David's Claude Code session inherited empty `VOYAGE_API_KEY` / `OPENROUTER_API_KEY` from the terminal that launched it (not from ~/.zshrc). `load_dotenv()` never overrides an existing var, even an empty one, so a worker spawned from that shell would silently lose the planner and memory. `planner.py` and `memory.py` now read keys through `_env()`, which falls back to `.env` when the exported value is empty. `harness/db.py` and the worker still use plain `load_dotenv()`; launch them from a clean shell.

## Status

- 12:51 ET: D1-D4 done and pushed. Stopped per prompt 1.
- 13:00 ET: prompt 2 started; D5 done.
- 13:10 ET: prompt 2 done (D5-D9). Moving to prompt 3 after merging origin/main.
- 13:14 ET: P1, P2 done. Suite 64 passed, 3 live skipped.
- 13:18 ET: P3 done. Prompt 3 complete (P4 = D9 already done in prompt 2). Stopped.
