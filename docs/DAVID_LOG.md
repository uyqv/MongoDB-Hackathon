# David's log

Branch `david`. Dev DB `second_shift_david`.

## Tasks done

- **D1** setup + `eval/seed_fake.py`. `all_configs()` = 225. Seed is idempotent (deletes `fake: true` docs first) and refuses any DB other than `second_shift_david`. Inserts 1 campaign (`camp_fa4e0001`, goal_version 2, 64 then 9 channels), 8 experiments, 6 memories, 31 events, 1 packet. All docs carry `fake: true`.

- **D2** `harness/planner.py`: OpenRouter via openai SDK, `tool_choice="required"`, tools `propose_experiment` / `stop`, 4 code checks (normalize, eligible, untried key, evidence ids in packet), one repair retry via a tool-result message, deterministic fallback (`model="deterministic-fallback"`), provider usage summed across both calls. Pure: no DB writes. If no eligible untried config exists it returns `stop` without calling the model. Provider/network exceptions also fall back and never raise.
  - Live call ~12:42 ET: model `anthropic/claude-sonnet-5`, request id `gen-1790441024-0rMRYMsxZqircOq56Cq6`, 2067 input / 202 output tokens (provider), cost $0.006154. Valid proposal, no fallback, cited the incumbent.
- **D3** `harness/memory.py`: Voyage `voyage-3.5`, **verified dimension 1024** (one live call). `memories_vec` created in `second_shift_david` (cosine, filters campaign_id/protocol_id/status/kind/synthetic), READY + queryable. `search_memories` filters inside `$vectorSearch`, projects out `embedding`, returns `vectorSearchScore`; falls back to an exact filtered find (newest first, `retrieval="fallback"`) when embed or vector search fails or returns nothing. Extra helper `add_memories(db, docs)` embeds in one call per 128 texts (for fixtures). Query embeddings are cached in-process (`lru_cache`), Voyage client uses `max_retries=3`.
  - Live test: 3 campaign-A/current-protocol memories returned, other campaign and other protocol excluded, broad-band csp_lda note ranked first (0.852 vs 0.704, 0.624).

## Tests

- `tests/test_planner.py`: 9 passed, 1 live skipped by default; live passed with `LIVE=1`.
- `tests/test_memory.py`: 2 passed (fallback path with embed forced to raise; verified-only rule), live vector test passed with `LIVE=1`. Tests refuse any DB other than `second_shift_david`.

## Stubbed / skipped

## Assumptions Andrew should check

- Event payloads that reference an experiment use `payload.experiment_id` (the dashboard's "reused" badge reads `job_reused.payload.experiment_id`).

## Requests for Andrew

- **Voyage key rate limit.** The Voyage key in `.env` has no payment method, so it is capped at 3 requests/min and 10K tokens/min (live error text says so). The worker embeds every memory and every search query, and D6 embeds 1,000+ distractor notes. Add a payment method at dashboard.voyageai.com (free 200M tokens still apply), or the demo will run on the fallback retrieval path.

## Deps needed

## Environment notes

- `harness/planner.py` exposes `client_factory` (module-level) so tests inject a fake client.
- On David's laptop the shell exports empty `VOYAGE_API_KEY` / `OPENROUTER_API_KEY`, and `load_dotenv()` does not override existing vars. Commands here run under `env -u VOYAGE_API_KEY -u OPENROUTER_API_KEY`.
