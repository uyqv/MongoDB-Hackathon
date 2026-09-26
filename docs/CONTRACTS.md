# Contracts

What the `Andrew` and `david` branches agree on. The code version is `harness/contracts.py`; if this file and that one disagree, the code wins. Both are owned by Andrew.

## 1. File ownership

One owner per file. Never edit a file you don't own. That rule is what makes the merges conflict-free.

| Owner | Files |
|---|---|
| **Andrew** | `harness/contracts.py`, `harness/db.py`, `harness/eeg.py`, `harness/store.py`, `harness/worker.py`, `harness/context.py`, `eval/run_ablation.py`, `tests/test_contracts.py`, `tests/test_eeg.py`, `tests/test_store.py`, `tests/test_worker.py`, `requirements.txt`, `.env.example`, `.gitignore`, `README.md`, `docs/WORKPLAN.md`, `docs/CONTRACTS.md`, `docs/DAVID_PROMPTS.md` |
| **David** | `harness/planner.py`, `harness/memory.py`, `harness/control.py`, `harness/jev.py`, `api/**`, `web/**`, `eval/fixtures.py`, `eval/seed_fake.py`, `tests/test_planner.py`, `tests/test_memory.py`, `tests/test_api.py`, `tests/test_fixtures.py`, `tests/test_jev.py`, `docs/ATTRIBUTION.md`, `docs/DAVID_LOG.md` |

David needs a new Python dependency: add it to `docs/DAVID_LOG.md` under "deps needed" and install it locally. Andrew adds it to `requirements.txt` at merge.

## 2. Databases

- Andrew and the demo: `DB_NAME=second_shift`.
- David during development: `DB_NAME=second_shift_david`. Fake seed data lives only here.
- Ablation scenarios: `second_shift_eval`.
- Same Atlas Sandbox cluster for all three. Create **only one** vector index per database (`memories_vec`). Free/sandbox tiers cap the number of search indexes.

## 3. Collections

Field-level shapes are the TypedDicts in `harness/contracts.py`. Summary:

| Collection | `_id` | Canonical for | Written by |
|---|---|---|---|
| `campaigns` | `camp_<8 hex>` | objective, `goal_version`, `constraints.max_channels`, `goal_history`, `protocol` + `protocol_id`, `budget.max_experiments`, `state`, `context_epoch`, `final` | worker (create, state, final); `control.py` (constraint change, context reset) |
| `experiments` | `<campaign_id>:<experiment_key>` | config, status, attempt, lease, **result metrics**, error | worker only |
| `memories` | `m_<12 hex>` | notes and code-rendered verified results, embedding | worker via `memory.add_memory`; fixtures |
| `events` | ObjectId | append-only audit/UI timeline | everyone via `db.log_event` |
| `packets` | `pk_<12 hex>` (= `packet_id`) | the exact evidence packet each planner call saw, plus the planner result and usage | `context.build_packet` (packet), worker (adds `planner_result`) |

Indexes (Andrew's `store.ensure_indexes`): `experiments {campaign_id:1, status:1, created_at:1}`, `events {campaign_id:1, ts:1}`, `packets {campaign_id:1, ts:-1}`, `memories {campaign_id:1, protocol_id:1, status:1}`. Vector index `memories_vec` belongs to David's `memory.ensure_vector_index`.

Rules both sides rely on:
- An experiment's metrics and `status: "done"` are written in **one** fenced update. That document is the source of truth. Events and memories are projections that can be regenerated.
- Eligibility is **computed on read** with `contracts.is_eligible(config, campaign.constraints)`. It is never stored.
- The incumbent is the eligible `done` experiment with the highest `result.val_balanced_accuracy` under the campaign's current `protocol_id`.
- Only code writes `verified: true` memories, and only with text from `contracts.render_result_text`.

## 4. Worker CLI (Andrew builds; David's API spawns it)

```
python -m harness.worker --campaign <campaign_id>
python -m harness.worker --new --mode {smoke,demo} --max-channels 64 --budget 10
```
Writes `worker_start` on boot (with `resumed: true` and the count of reused done experiments when the campaign already existed) and `worker_stop` on a clean exit. A SIGKILL writes nothing, so `control.kill_worker` writes `worker_killed`.

## 5. Module interfaces David builds

### `harness/planner.py`
```python
def plan(packet: EvidencePacket, *, model: str | None = None) -> PlannerResult
```
- A pure function: **no database writes.** The worker logs the call.
- OpenRouter through the `openai` SDK: `base_url="https://openrouter.ai/api/v1"`, key `OPENROUTER_API_KEY`, model `model or os.environ["PLANNER_MODEL"]` (default `anthropic/claude-sonnet-5`, verified on the OpenRouter catalog 2026-09-26). Pass `extra_body={"usage": {"include": True}}` so the provider reports cost.
- Tool calling, `tool_choice="required"`, two tools: `propose_experiment(config, rationale, evidence_ids)` and `stop(rationale, evidence_ids)`.
- Code validation after the call. Every failure gets **one** repair retry with the error message appended:
  1. `contracts.normalize_config(config)` succeeds.
  2. `contracts.is_eligible(config, packet["goal"]["constraints"])`.
  3. `contracts.experiment_key(packet["protocol_id"], config)` is not in `packet["tried_keys"]`.
  4. Every `evidence_id` appears in the packet: `incumbent.experiment_id`, `pending[].experiment_id`, `recent[].experiment_id`, `retrieved[].memory_id`, or `retrieved[].source_ids`.
- After a failed repair, fall back deterministically: the first config in `contracts.all_configs()` order that is eligible and untried, with `fallback_used=True` and a `fallback_reason`. If none is left, return `action="stop"`.
- The rationale must not state metric numbers that are absent from the packet. The prompt says so.
- A proposal with zero evidence IDs is valid (`evidence_ids=[]`). The UI shows it as uncited.
- `usage.source="provider"` when the response carries usage, else `"estimate"`.

### `harness/memory.py`
```python
def embed(texts: list[str], input_type: str = "document") -> list[list[float]]
def ensure_vector_index(db) -> None
def add_memory(db, *, campaign_id, protocol_id, kind, text, source_ids, verified, synthetic=False) -> str
def search_memories(db, *, campaign_id, protocol_id, query, k=4, kinds=None) -> list[RetrievedMemory]
def mark_obsolete(db, memory_ids: list[str]) -> int
```
- Voyage: `voyageai.Client().embed(texts, model=os.environ.get("VOYAGE_MODEL","voyage-3.5"), input_type=...)`. Check the real dimension with one call; don't hard-code it.
- `memories_vec`: `vectorSearch` index with `embedding` (cosine) plus filter fields `campaign_id`, `protocol_id`, `status`, `kind`, `synthetic`. Idempotent: check `list_search_indexes()` first, then wait until it is queryable.
- `search_memories` filters `campaign_id`, `protocol_id`, `status: "active"` (and `kind $in kinds` when given) **inside** `$vectorSearch`, projects out `embedding`, and returns `score` from `vectorSearchScore` with `retrieval="vector"`.
- If Voyage or vector search fails, `add_memory` stores `embedding: None` and still inserts. `search_memories` falls back to an exact filtered `find` sorted newest first, with `score=None, retrieval="fallback"`. Never raise into the worker.

### `harness/control.py`
```python
def change_constraint(db, campaign_id, max_channels: int, reason: str) -> dict   # returns updated campaign
def reset_context(db, campaign_id) -> int                                         # returns new context_epoch
def start_worker(campaign_id) -> int                                              # returns pid
def kill_worker() -> dict                                                         # {"killed": bool, "pid": int|None}
def worker_status() -> dict                                                       # {"running", "pid", "campaign_id"}
```
- `change_constraint`: `max_channels` must be in `{9, 21, 64}`. `find_one_and_update` with `$inc goal_version`, `$set constraints` + `updated_at`, return the new doc. Then `$push goal_history {version, constraints, changed_at, reason}`, then `log_event("goal_changed", {from_version, to_version, old_constraints, new_constraints, reason})`.
- `reset_context`: `$inc context_epoch`, then `log_event("context_reset", {"context_epoch": n})`.
- `start_worker`: refuse when a live worker exists. `subprocess.Popen([sys.executable, "-m", "harness.worker", "--campaign", id])`, stdout/stderr to `run/worker.log`, write `run/worker.json` with `{pid, campaign_id, started_at}`.
- `kill_worker`: `os.kill(pid, signal.SIGKILL)`, a real crash rather than a graceful stop. Then `log_event("worker_killed", {"pid", "signal": "SIGKILL"})` and remove `run/worker.json`. Check liveness with `os.kill(pid, 0)`.

## 6. HTTP API (David, `api/main.py`)

All responses are JSON. ObjectIds become strings. **The `embedding` field is never returned.**

| Method | Path | Returns |
|---|---|---|
| GET | `/` | `web/index.html`; `/static/*` serves `web/` |
| GET | `/api/health` | `{ok, db}` |
| GET | `/api/campaigns` | newest first: `_id, objective, state, goal_version, constraints, created_at` |
| GET | `/api/campaigns/{cid}` | campaign doc plus computed `used`, `remaining`, `incumbent` |
| GET | `/api/campaigns/{cid}/experiments` | ordered by `created_at`, each with computed `eligible` |
| GET | `/api/campaigns/{cid}/events?after=<iso>&limit=200` | ordered by `ts` |
| GET | `/api/campaigns/{cid}/packets/latest?strategy=evidence` | latest packet doc |
| GET | `/api/campaigns/{cid}/memories?kind=&include_synthetic=false` | memories without embeddings |
| GET | `/api/eeg/preview` | real EEG trace + per-class PSD from S001 run 6 (see §7) |
| GET | `/api/worker/status` | `control.worker_status()` |
| POST | `/api/worker/start` `{campaign_id}` | `{pid}` |
| POST | `/api/worker/kill` | `control.kill_worker()` |
| POST | `/api/campaigns/{cid}/constraint` `{max_channels, reason}` | updated campaign |
| POST | `/api/campaigns/{cid}/context-reset` | `{context_epoch}` |

## 7. EEG preview (display only)

`/api/eeg/preview` loads `S001R06.edf` via `mne.datasets.eegbci.load_data(1, [6], path=EEG_DATA_DIR)` and runs `eegbci.standardize`. It returns C3/Cz/C4 as ~6 s of 1–40 Hz filtered signal from the first task cue (downsampled for display), plus Welch PSD (4–40 Hz) averaged over T1 (both fists) vs T2 (both feet) epochs at 1–3 s. It caches to `data/eeg_preview.json` and includes `"source": "PhysioNet eegmmidb v1.0.0, S001 run 6"`. It never feeds any metric.

## 8. Ablation fixtures (David, `eval/fixtures.py`)

```python
def build_scenario(src_db, dst_db, src_campaign_id: str, name: str, *, n_distractors: int = 200, seed: int = 0) -> dict
```
Copies real experiments and verified memories from a real source campaign into a new campaign in `dst_db` (`second_shift_eval`). It then injects the scenario's conditions and returns `{campaign_id, protocol_id, name, expected_evidence_ids, forbidden_evidence_ids, description}`. Scenario names:

1. `buried_best_eligible`: constraint lowered to 9 channels. The best 9-channel result sits early, followed by `n_distractors` synthetic notes.
2. `buried_failure`: a real failed or worst-scoring config family sits early and is buried. The correct move is to avoid it.
3. `obsolete_protocol`: a higher-scoring record under a **different** `protocol_id` (synthetic, labeled). Citing it is a mistake.
4. `goal_changed`: history crosses a 64 → 21 change. The proposal must be eligible under 21.
5. `distractor_flood`: 1,000 synthetic notes. The correct move is to retrieve the real incumbent.

Every injected record carries `synthetic: True, kind: "synthetic_stress"`, except copies of real experiments. `score(scenario, packet, planner_result) -> {cited_expected, cited_forbidden, eligible, fallback_used, input_tokens, cost_usd}` is computed by code.
