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
- Andrew: Voyage card added, so full rate limits apply. Real campaign id for D6: _pending, Andrew sends it in ~5 min_.
- **D5** `harness/control.py` + POST endpoints + dashboard buttons (Start worker, Kill worker SIGKILL, Reset context, channel budget 9/21/64 + reason). `change_constraint` does the `$inc goal_version`, `$set constraints`, and `$push goal_history` in ONE `find_one_and_update` guarded on the old `goal_version` (so version and history can never disagree), then logs `goal_changed`. `start_worker` strips empty exported keys from the child env (so the worker's `load_dotenv()` fills them from `.env`), pins the child's `DB_NAME` to the API's DB, and runs it in its own session; `kill_worker` SIGKILLs, reaps, logs `worker_killed`, removes `run/worker.json`. Endpoint errors: 400 bad max_channels, 404 unknown campaign, 409 worker already running.
  - Read-only check against the real DB (`DB_NAME=second_shift` on port 8001, no buttons pressed): campaign `camp_51b0f538` rendered all panels, vector retrieval live (scores 0.75), planner usage from the provider, `fault_injection` and resumed `worker_start` on the timeline.
  - The worker pill only tracks workers the API started (`run/worker.json`). A worker Andrew starts from the CLI shows as "API worker: stopped", and Start worker would launch a second one, so don't press it while a CLI worker runs.

## Tests

- `tests/test_planner.py`: 9 passed, 1 live skipped by default; live passed with `LIVE=1`.
- `tests/test_memory.py`: 2 passed (fallback path with embed forced to raise; verified-only rule), live vector test passed with `LIVE=1`. Tests refuse any DB other than `second_shift_david`.
- `tests/test_api.py`: 7 passed (TestClient against the seeded dev DB).
- Full suite 12:51 ET: 27 passed, 2 live skipped.
- control.py tests live in `tests/test_api.py` (CONTRACTS §1 gives David no `test_control.py`): constraint bump + history + event, context_epoch bump, start/kill/status on a dummy sleep process, and all POST endpoints. Full suite 13:00 ET: 44 passed, 2 live skipped.

## Stubbed / skipped

## Assumptions Andrew should check

- `/api/campaigns/{cid}` computes `used` as the count of experiment docs in the campaign (any status) and `remaining = budget.max_experiments - used`. Change if the worker counts budget differently.
- `/api/campaigns/{cid}/events` without `after` returns the latest `limit` events (ascending), so the timeline shows recent history on long runs. With `after`, it returns the next `limit` after that ts.
- `/api/campaigns/{cid}/packets/latest` sorts packets by `ts` descending, matching the `packets {campaign_id:1, ts:-1}` index. Packets need a `ts` field.
- Experiments get an extra computed `reused: true` when a `job_reused` event has `payload.experiment_id` equal to their `_id`.

- Confirmed after merge: `job_reused.payload.experiment_id` matches store.enqueue; `worker_start.payload.counts.done` drives the timeline's resumed count.

## Requests for Andrew

- ~~Voyage key rate limit~~ resolved: Andrew added a card. Original note: The Voyage key in `.env` has no payment method, so it is capped at 3 requests/min and 10K tokens/min (live error text says so). The worker embeds every memory and every search query, and D6 embeds 1,000+ distractor notes. Add a payment method at dashboard.voyageai.com (free 200M tokens still apply), or the demo will run on the fallback retrieval path.

## Deps needed

## Environment notes

- `harness/planner.py` exposes `client_factory` (module-level) so tests inject a fake client.
- David's Claude Code session inherited empty `VOYAGE_API_KEY` / `OPENROUTER_API_KEY` from the terminal that launched it (not from ~/.zshrc). `load_dotenv()` never overrides an existing var, even an empty one, so a worker spawned from that shell would silently lose the planner and memory. `planner.py` and `memory.py` now read keys through `_env()`, which falls back to `.env` when the exported value is empty. `harness/db.py` and the worker still use plain `load_dotenv()`; launch them from a clean shell.

## Status

- 12:51 ET: D1-D4 done and pushed. Stopped per prompt 1.
- 13:00 ET: prompt 2 started; D5 done.
