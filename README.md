# Second Shift

**A research agent that can lose its working context, or its whole process, without losing its research campaign.**

Built today (September 26, 2026) at the MongoDB x Cerebral Valley Harness Engineering hackathon, Problem Statement 2: Long Horizon Engineering.

Long running agents forget why they ran old experiments, rerun work they already paid for, and keep optimizing against goals that changed hours ago. Second Shift keeps the campaign in MongoDB Atlas and rebuilds every decision from durable evidence, so the model's context window can be thrown away after each step.

The reference workload is a real one: classifying imagined movement (both fists vs both feet) from EEG recordings in PhysioNet's EEG Motor Movement/Imagery dataset.

## What it does

- **One campaign survives everything.** Goal, constraints, protocol, every experiment and its measured result live in Atlas. Kill the worker with `SIGKILL`, start a new one, and it picks up where the last one died.
- **The model picks, code measures.** Claude Sonnet 5 (through OpenRouter) chooses the next configuration from a fixed menu of 225 and cites evidence IDs. It never computes or reports a metric. Every number comes from the numerical runner and is stored in the experiment document.
- **Bounded context, rebuilt every step.** Each decision gets a fresh evidence packet: the latest goal (exact read), the best eligible result (exact read), pending jobs, a short recent window, and a few older notes ranked by Atlas Vector Search over Voyage embeddings. The packet has a token budget, and it is saved so you can see exactly what the model saw.
- **Goals can change mid campaign.** Drop the electrode budget from 64 to 9 and eligibility is recomputed from results already measured. Nothing is rerun and nothing comparable is thrown away.
- **Work is never paid for twice.** Experiments are keyed by a hash of the effective configuration plus the protocol (data file hashes, exact splits, evaluator version, seed). A finished experiment is reused. A changed dataset or evaluator can never silently reuse old numbers.

## Measured today

All numbers below come from real runs against real PhysioNet data and our Atlas Sandbox cluster. Nothing is simulated except where labeled.

**A full LLM driven campaign** (`camp_0f8981ee`, budget 10 experiments, subjects 1 to 5):

- 10 planner decisions, 0 fallbacks, 0 proposals rejected by the code guards
- 30,341 provider reported input tokens, $0.085 total
- Validation balanced accuracy went 0.692, 0.571, 0.745, 0.665, 0.774, ...
- The planner noticed from measured results that 21 motor channels beat all 64 and narrowed its search accordingly
- Final pick: CSP + LDA, 13 to 30 Hz, 0.5 to 2.5 s window, 21 channels. **0.774 validation, 0.732 on the sealed test set** (75 trials, scored once)
- The planner stopped with 1 experiment unspent, arguing nearby variants were exhausted. That call is recorded with its rationale.

**Recovery and constraint checks** (`python -m eval.demo_checks all`): _RESULTS PENDING: filled in from eval/checks.json._

**Context comparison** (`python -m eval.run_ablation`): _RESULTS PENDING: filled in from eval/results.json, whichever arm wins._

## How it works

```mermaid
flowchart LR
    subgraph Worker["Worker (one long lived Python process)"]
        R[REHYDRATE] --> P[PLAN] --> V[VALIDATE] --> Q[QUEUE] --> E[EXECUTE] --> C[COMMIT] --> R
    end
    P -- evidence packet --> LLM[Claude Sonnet 5<br/>via OpenRouter]
    LLM -- config + rationale + evidence IDs --> V
    E --> EEG[EEG runner<br/>MNE + scikit-learn]
    subgraph Atlas["MongoDB Atlas"]
        campaigns[(campaigns)]
        experiments[(experiments)]
        memories[(memories<br/>Vector Search)]
        events[(events)]
        packets[(packets)]
    end
    R <--> campaigns
    R <--> experiments
    P <--> memories
    C --> experiments
    C --> memories
    Worker --> events
    API[FastAPI + dashboard] <--> Atlas
```

- `harness/worker.py` runs the state loop. Between steps it holds no conversation history.
- `harness/context.py` builds the evidence packet under a token budget and stores it in `packets`.
- `harness/planner.py` calls the model with two tools (`propose_experiment`, `stop`), validates the answer in code, allows one repair, then falls back to a deterministic pick.
- `harness/store.py` owns durable state: atomic job claims with leases, commits fenced by lease token (a zombie worker cannot overwrite a newer attempt), dedup and reuse, and a sealed test set that can be scored only once.
- `harness/memory.py` embeds notes with Voyage and retrieves them with `$vectorSearch`, filtering by campaign, protocol and status before ranking.
- `harness/eeg.py` is the only place metrics are computed.

## The experiment

- **Data:** PhysioNet EEG Motor Movement/Imagery v1.0.0, runs 6, 10 and 14 (imagined both fists vs both feet), 64 channels at 160 Hz, subjects 1 to 5.
- **Protocol, fixed before any results were seen:** within subject. Each subject gets its own model trained on run 6 and scored on run 10. Run 14 stays sealed until the campaign finalizes. Predictions are pooled across subjects.
- **Menu:** 2 methods (log band power + logistic regression, CSP + shrinkage LDA) x 5 bands x 3 time windows x 3 channel sets x 2 or 3 method settings = 225 configurations.
- **Scope:** offline classification only. Zero phase filtering is offline, not a real time decoder. No clinical claims. Repeated use of the validation run is model selection, which is why the test run is sealed.

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # MONGODB_URI, OPENROUTER_API_KEY, VOYAGE_API_KEY, DB_NAME=second_shift

.venv/bin/python -m harness.eeg --mode demo                     # real data gate: hashes, splits, sample results
.venv/bin/python -m harness.worker --new --mode demo --budget 10 # run a campaign
.venv/bin/uvicorn api.main:app --port 8000                      # dashboard at http://localhost:8000
.venv/bin/python -m eval.demo_checks all                        # recovery + constraint checks
.venv/bin/python -m pytest -q
```

The EEG files (about 39 MB for subjects 1 to 5) download from PhysioNet on first run.

## What we do not claim

- We did not run billions of tokens today. The campaign here is small on purpose. What we show is the mechanism that keeps context bounded as history grows, plus a measured check with synthetic distractor notes (labeled `synthetic_stress` and kept out of all result summaries).
- Checkpointing is not new (LangGraph has it). What we add is verified result memory, evidence packets with provenance, constraint aware reuse, and fenced recovery for a numerical research loop.
- A job killed mid computation is rerun as a new attempt. We do not claim mid training checkpoints or exactly once execution of external computation.
- Accuracy numbers are from 5 subjects and 75 validation trials. They show the loop works on real data, not population level performance.

## Attribution

EEG data: Schalk G., McFarland D.J., Hinterberger T., Birbaumer N., Wolpaw J.R. (2004). BCI2000: A General-Purpose Brain-Computer Interface (BCI) System. IEEE Transactions on Biomedical Engineering 51(6):1034 to 1043. Distributed by PhysioNet (DOI 10.13026/C28G6P) under the Open Data Commons Attribution License. Full credits, including MNE-Python, scikit-learn, Voyage AI, OpenRouter and MongoDB Atlas, are in `docs/ATTRIBUTION.md`.

The harness, EEG adapter, tests and dashboard in this repository are our original work from today.

## Team

Andrew Shatsky and David Shatsky.
