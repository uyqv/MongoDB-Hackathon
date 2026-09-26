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

## Tests

- `tests/test_planner.py`: 9 passed, 1 live skipped by default; live passed with `LIVE=1`.
- `tests/test_memory.py`: 2 passed (fallback path with embed forced to raise; verified-only rule), live vector test passed with `LIVE=1`. Tests refuse any DB other than `second_shift_david`.
- `tests/test_api.py`: 7 passed (TestClient against the seeded dev DB).
- Full suite 12:51 ET: 27 passed, 2 live skipped.

## Stubbed / skipped

## Assumptions Andrew should check

- `/api/campaigns/{cid}` computes `used` as the count of experiment docs in the campaign (any status) and `remaining = budget.max_experiments - used`. Change if the worker counts budget differently.
- `/api/campaigns/{cid}/events` without `after` returns the latest `limit` events (ascending), so the timeline shows recent history on long runs. With `after`, it returns the next `limit` after that ts.
- `/api/campaigns/{cid}/packets/latest` sorts packets by `ts` descending, matching the `packets {campaign_id:1, ts:-1}` index. Packets need a `ts` field.
- Experiments get an extra computed `reused: true` when a `job_reused` event has `payload.experiment_id` equal to their `_id`.

- Event payloads that reference an experiment use `payload.experiment_id` (the dashboard's "reused" badge reads `job_reused.payload.experiment_id`).

## Requests for Andrew

- **Voyage key rate limit.** The Voyage key in `.env` has no payment method, so it is capped at 3 requests/min and 10K tokens/min (live error text says so). The worker embeds every memory and every search query, and D6 embeds 1,000+ distractor notes. Add a payment method at dashboard.voyageai.com (free 200M tokens still apply), or the demo will run on the fallback retrieval path.

## Deps needed

## Environment notes

- `harness/planner.py` exposes `client_factory` (module-level) so tests inject a fake client.
- David's Claude Code session inherited empty `VOYAGE_API_KEY` / `OPENROUTER_API_KEY` from the terminal that launched it (not from ~/.zshrc). `load_dotenv()` never overrides an existing var, even an empty one, so a worker spawned from that shell would silently lose the planner and memory. `planner.py` and `memory.py` now read keys through `_env()`, which falls back to `.env` when the exported value is empty. `harness/db.py` and the worker still use plain `load_dotenv()`; launch them from a clean shell.

## Status

- 12:51 ET: D1-D4 done and pushed. Stopped per prompt 1; waiting for "merge 1 done" before prompt 2.
