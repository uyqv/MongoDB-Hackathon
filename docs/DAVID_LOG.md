# David's log

Branch `david`. Dev DB `second_shift_david`.

## Tasks done

- **D1** setup + `eval/seed_fake.py`. `all_configs()` = 225. Seed is idempotent (deletes `fake: true` docs first) and refuses any DB other than `second_shift_david`. Inserts 1 campaign (`camp_fa4e0001`, goal_version 2, 64 then 9 channels), 8 experiments, 6 memories, 31 events, 1 packet. All docs carry `fake: true`.

## Tests

## Stubbed / skipped

## Assumptions Andrew should check

- Event payloads that reference an experiment use `payload.experiment_id` (the dashboard's "reused" badge reads `job_reused.payload.experiment_id`).

## Requests for Andrew

## Deps needed

## Environment notes

- On David's laptop the shell exports empty `VOYAGE_API_KEY` / `OPENROUTER_API_KEY`, and `load_dotenv()` does not override existing vars. Commands here run under `env -u VOYAGE_API_KEY -u OPENROUTER_API_KEY`.
