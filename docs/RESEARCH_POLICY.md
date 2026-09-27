# Uncertainty-aware research planning

`research_v1` is an opt-in experiment-selection policy. It uses the existing 225 configurations,
two EEG pipelines, within-subject protocol, MongoDB store and single worker. Its numerical
surrogate ranks candidates; the language model selects a candidate and explains why; code
records and assesses the comparison hypothesis.

[Measured results](RESEARCH_RESULTS.md) include all 40 benchmark rollouts and the real recovery campaign.

## Run

```bash
.venv/bin/python -m harness.worker --new --mode demo --budget 10 --policy research_v1
.venv/bin/python -m harness.worker --campaign <campaign_id>
.venv/bin/uvicorn api.main:app --port 8000
```

Use `--research-seed 42` to reproduce the numerical ordering. Resume reads the stored campaign
policy and seed. Existing campaigns without a policy use the original planner. The first three
accepted configurations use seeded max-min diversity and do not require a planner API call.
These experiments count toward the same budget, including failures and cancellations.

The dashboard's evidence inspector shows the shortlist and recent hypothesis assessments.
Open an experiment to see its measured subject interval and paired comparison. Predictions,
predictive standard deviations and expected improvement are surrogate estimates, not measured
accuracy or calibrated population guarantees.

## Frozen numerical policy

- Encode every effective configuration field categorically using a fixed vocabulary from the
  complete allowed surface. Inactive method parameters contribute zero indicators.
- Fit `GaussianProcessRegressor` on validation balanced accuracy minus the chance prior, 0.5.
  Use `ConstantKernel(0.04) * Matern(length_scale=1.0, nu=2.5)`, no hyperparameter optimizer,
  and no target normalization. Noise is the subject-bootstrap variance, floored at `1e-4`.
  Single-subject runs use a configured surrogate noise variance of `0.01` while their measured
  subject uncertainty remains unavailable.
- Rank by expected improvement over the current eligible incumbent, with zero improvement
  margin. Offer three improvement choices, two additional uncertainty choices and one
  additional single-parameter neighbor of the incumbent. Backfill shortages by improvement.
- All choices satisfy current constraints and exclude every previously accepted configuration.
  Failures do not become fabricated low scores. Invalid evidence or a numerical fitting error
  triggers a logged, seeded diversity fallback.
- Seeds, policy settings, source experiment IDs and the ranking are stored with each decision.
  Rebuilding from the same committed evidence reproduces the numerical ranking. LLM responses
  are stored but are not claimed to be reproducible.

The evidence packet retains complete duplicate membership and source provenance as audit data.
`planner_view` omits that growing audit data, the full tried list and the full surface for this
policy. Planner-input estimates are limited to 4,000 tokens; notes, recent rows and optional
evidence are trimmed before candidates. The goal, incumbent and at least one candidate remain.
An impossibly small budget fails explicitly. Actual provider tokens include tool schemas and
instructions and are reported separately.

## Evidence and hypotheses

Research protocols add `validation_evidence_version: 1` to the protocol hash. A legacy cached
result cannot satisfy this contract. The scalar EEG evaluator remains unchanged, and legacy
protocols remain resumable. Research results additionally contain `validation_predictions`
and `uncertainty`. Each prediction records `trial_id`, `subject`, `run`, `y_true` and `y_pred`.
Only run 10 is accepted as validation evidence. Duplicate identities, invalid labels and
aggregate scores inconsistent with predictions are rejected.

Uncertainty uses 2,000 subject-cluster resamples with seed 42. Each sampled subject contributes
all its trials; balanced accuracy is computed from the pooled confusion counts. A paired
comparison resamples the same subjects on both sides and requires identical trial identities,
subjects, runs and true labels. The interval is the 2.5th to 97.5th percentile. One subject
cannot provide a subject-level interval. Identical predictions give an exactly zero paired
difference.

Before execution, the experiment's `proposed_by.hypothesis` records a fixed comparison claim:
the candidate improves its reference's validation balanced accuracy by at least 0.02.
Initialization and proposals without an eligible reference are exploration. The predicted
improvement comes from the surrogate, not an LLM-generated number. Claims are scoped to the
specific configuration pair; multiple parameter changes do not establish a causal explanation.

Code assesses a committed result as:

| Status | Meaning |
|---|---|
| `pending` | The experiment has not produced an assessed outcome |
| `exploration` | No comparative claim was registered |
| `supported_on_validation` | The entire paired interval is above 0.02 |
| `contradicted_on_validation` | The entire paired interval is below 0.02 |
| `inconclusive` | The interval touches/crosses 0.02, is unavailable, or evidence is incompatible |
| `execution_failed` | Numerical execution failed; no scientific conclusion |
| `cancelled` | Constraints made the queued configuration ineligible before execution |

The `hypotheses` collection is an idempotent projection of the durable pre-execution proposal
and committed results. Restart repairs missing registrations and pending assessments. Existing
assessments keep their timestamps. Neither Jev nor vector retrieval assigns these statuses.
Goal changes retain historical comparisons while rebuilding the eligible incumbent and shortlist.
Constraints are checked after planning, on enqueue and immediately before numerical execution.

`GET /api/campaigns/{cid}/hypotheses` returns only that campaign and protocol's claims. Experiment
responses include their hypothesis, and packet responses include research fields. Snapshot
export records the new endpoint and these additive fields. HTTP serving does not import the
scientific runtime; the numerical policy runs in the worker.

## Verification and benchmark

```bash
.venv/bin/python -m pytest -q tests/test_research.py tests/test_research_benchmark.py
DB_NAME=second_shift_david .venv/bin/python -m pytest -q --run-integration tests/test_research_store.py
.venv/bin/python -m eval.research_benchmark --precompute
.venv/bin/python -m eval.research_benchmark
.venv/bin/python -m eval.research_demo
```

Export one research campaign for a snapshot viewer with
`python scripts/export_dashboard_snapshot.py --campaign <campaign_id> --output output/research/dashboard_snapshot.json`.
Omitting these options retains the existing full-dashboard export behavior.

The benchmark caches the 225 actual validation outcomes in the ignored local file
`output/research/oracle.json`. This is evaluator-only data. Each policy receives only the
measurements it has selected. No test run is parsed or scored by the benchmark. A protocol
change invalidates the cache.

The previous local cache and run logs were preserved under
`archive/2026-09-26/output/research/`. To reuse that cache, copy `oracle.json` back
to `output/research/oracle.json` before running the benchmark. These large local
outputs are not part of the Git checkout or dashboard deployment.

Four arms compare the current planner, hybrid shortlist planner, numerical optimizer and
seeded random search. Each uses a budget of ten, the same three initial configurations for
each seed, five seeds, and two scenarios: a constant 64-channel budget and a reduction to nine
channels after experiment five. Both language-model arms use the existing provider/model and
exact-evidence context; replay excludes live vector notes and Jev routing for both arms.
Initialization is not counted as a provider call. The benchmark reports real provider token
usage, cost, fallbacks, best-so-far scores and regret against the currently eligible validation
optimum. Reports resume completed rollouts and preserve every measured outcome.

The recovery demonstration creates a real campaign, kills its worker after the fourth result
commit and before assessment, reduces the channel budget, resets context and starts a fresh
worker. It checks assessment repair, numerical reconstruction, no rerun of committed work,
constraint compliance and one finalization. Outputs are `eval/research_results.json` and
`eval/research_demo.json`. The worker also supports `--crash-after-commit N` for direct testing.

These are exploratory comparisons on five subjects and a repeatedly queried validation run.
Bootstrap intervals do not correct adaptive selection, and five search seeds are not five
independent datasets. Hypothesis support is not a population or clinical finding. Final model
selection remains validation accuracy, then F1, with a stable identity tie-break; the reserved
test set is scored through the existing finalization path. Report benchmark losses and ties
alongside gains.
