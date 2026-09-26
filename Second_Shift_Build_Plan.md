# Second Shift — one-day build plan
## A horizontal memory-and-recovery harness, with an EEG research adapter

Decision date: September 26, 2026. This is a scoped engineering recommendation, not a prediction of winning.

## 1. Decision and confidence

Build a research agent that can lose its working context without losing its research campaign. Its initial workload is a small, reproducible EEG motor-imagery classification campaign. The product is the harness; the scientific models are existing numerical components.

High confidence: the direction matches Statement Two, real labeled EEG data are publicly available, and a small subset is sufficient to demonstrate numerical experiment execution. Moderate confidence: two developers can deliver the deliberately reduced scope today, conditional on the real-data and account gates below. Unknown: winning, this team's live account permissions, actual model/API behavior, real-data numerical results, and robustness over billions of tokens or weeks.

Do not build the entire feature list from the earlier recommendation. Do not make Aleph ultrasound reconstruction the critical path. Do not claim that checkpointing alone is novel. LangGraph already documents persistent checkpoint/store functionality [S7].

## 2. What the sources actually establish

### Organizer guide
The uploaded resource guide names Statement Two, Long Horizon Engineering: coherent memory across billions of tokens in one session, sustained pursuit of long-term goals, and learning from hard metric signals. MongoDB is the data and memory layer. Finalist eligibility requires the emailed Atlas Hackathon Sandbox. The guide requires original work, a public repository, an accessible one-minute video of code and functionality built today, an on-site September 26 recording, and a concise description on Cerebral Valley. It also describes six finalists and a September 30 community-vote/on-stage round, with at least one finalist teammate present 10 AM–4:30 PM.

The complete supplied guide does not specify a submission clock time, numerical judging weights, or an explicit minimum measured token volume. Obtain the exact cutoff from the organizers immediately. Do not infer that the event end time is the submission time. Treat the billion-token wording as a serious scaling target, not as an achieved result or an automatically waived condition.

### Aleph audit
The article's repository link redirects to `alephneuro/microbubbles`. The inspected default-branch tree has code and browser-viewer templates, not a ready-made small labeled EEG dataset. The README describes a roughly 96 GB, 216-acquisition sample download. Beamforming requires the optional MACH/CUDA path; the core tracking/viewing install does not itself require GPU. `--beamformed` avoids download and beamforming only when a compatible pre-beamformed file already exists. No such small ready-to-use input was verified. The data describe ultrasound localization microscopy, not sleep staging or motor-imagery labels [S1, S2].

Conclusion: this is a real open-source research pipeline, but the wrong same-day dependency without already working access to a small compatible intermediate and an appropriate evaluation metric. Do not treat a generated viewer as evidence that the agent improved the reconstruction. Dataset bytes are not LLM tokens.

### EEG replacement
Use PhysioNet EEG Motor Movement/Imagery v1.0.0. It is open access under the stated Open Data Commons Attribution License. There are 64 EEG channels sampled at 160 Hz. Runs 6, 10, and 14 represent imagined both-hands versus both-feet activity; T1 and T2 are the two task classes in these runs. Other runs have different label semantics [S3, S4]. MNE publishes a CSP/classification example using this same run family [S5]. Subject 1's relevant files are listed at about 2.5 MB each [S8].

## 3. Exact demo task and minimum data

Objective: maximize validation balanced accuracy for hands-versus-feet motor imagery within a fixed experiment budget, then select an eligible configuration under a changed electrode budget. Preserve all decisions and evidence across a forced context reset and worker restart.

Scientific scope: offline signal classification only. No brain stimulation, diagnosis, clinical claims, novel neural foundation model, or real-time headset integration.

Use the included `smoke_test.py`:

- Smoke mode: subject 1, runs 6/10/14. Train on run 6; validate on run 10; reserve run 14 without scoring it. Approximately 7.5 MB according to the displayed file listing. The script reports actual usable epochs after parsing; do not hard-code the count.
- Demo mode: subjects 1–5, those same three runs. Train on subjects 1–3, validate on subject 4, reserve subject 5 without scoring it. Approximately 40 MB as a planning estimate, not a measured download total. A few hundred task epochs are expected; the loader reports exact counts and dropped events.
- Keep subjects 6 onward unexamined for expansion after the core demo works. Do not choose subjects based on which make the best chart.

This is enough to show a real experiment loop. It is not enough for population-level or clinical validation. A large model or a full dataset download is unnecessary for the software proof.

The harness needs another kind of evidence: about 8–12 real completed experiments, their actual error/decision records, and a separately labeled synthetic memory-load fixture. Scientific sample count and memory-history volume are different dimensions.

## 4. Allowed experiment surface

The provided numerical runner has two methods: log-bandpower features with logistic regression, and CSP with shrinkage LDA. Its band choices are 8–12, 13–30, and 8–30 Hz. Channel presets are central nine and all 64. CSP component counts are two or four. The analysis interval is fixed at 1–3 seconds after the task cue. The zero-phase filtering is offline, not a real-time causal decoder.

The LLM selects a configuration, a next action, and a short rationale referring to evidence IDs. It does not write arbitrary executable code. Its tool surface is limited to proposing an experiment, reading a bounded evidence packet, inspecting campaign progress, and stopping. The numerical worker—not any language model—computes accuracy, F1, durations, channel counts, and all comparisons.

Fit every learned preprocessing step on the training partition only. Keep trial/subject/run identifiers through preprocessing. Never split overlapping windows from the same trial across partitions. Never tune using the sealed final test set. At finalization, freeze the selected configuration and score the reserved test partition once through a separate evaluator capability. Repeated validation-set use is model selection, not an unbiased generalization estimate.

## 5. Four must-build behaviors

### A. Persistent campaign state
One campaign ID survives process and context resets. MongoDB stores the current objective/version, immutable dataset and split manifests, completed experiments, pending jobs, and source-backed memory. The planner gets the latest authoritative goal on every call; the goal is never reconstructed from chat summaries.

### B. Verified result memory
Numerical results are canonical records, not free-form notes. An observation can enter the verified-result channel only when an evaluator result exists, the referenced protocol/configuration match, and its metrics are finite and in range. Render factual metric summaries from those records in code. LLM interpretations remain labeled hypotheses. A Jev output never upgrades an interpretation to numerical evidence.

### C. Bounded context reconstruction
At each decision assemble: latest goal and constraints; incumbent eligible result; currently pending jobs; a small recent-results window; and a few retrieved historical failure/interpretation notes. Filter by campaign/protocol and status before semantic retrieval. Use MongoDB Vector Search for semantic memory selection, but exact MongoDB reads for budgets, permissions, latest goal, and numerical evidence. Set and log a finite context budget. Log provider-reported token usage; label estimates as estimates.

### D. Real recovery and current eligibility
Kill and restart the worker, then reconstruct state from Atlas. A completed experiment is reused instead of recomputed. A job killed during computation may need rerunning; do not claim mid-training checkpoint recovery or universal exactly-once execution. After an explicit change from a 64-channel allowance to nine, recompute which existing results are eligible and continue under the current goal. Do not discard scientifically comparable measurements merely because the business constraint changed.

## 6. Small architecture

Use Python for the numerical runner, planner controller, and explicit state machine; FastAPI for a small API; a minimal React/Next.js dashboard; MongoDB Atlas for durable state and memory; the team's already accessible text model through OpenRouter for planning; Voyage embeddings for the small semantic-memory collection if access works; and optional Jev for routing unstructured notes.

Keep one active worker. Do not add Redis, Kafka, a distributed executor, automatic model switching, a generic framework SDK, or multiple planning agents. Keep the Python worker in a long-lived process on an existing suitable host or the demo laptop. Do not put a continuous numerical loop inside a frontend serverless request.

State sequence:

`REHYDRATE -> PLAN -> VALIDATE -> QUEUE -> EXECUTE -> COMMIT -> REHYDRATE`

`WAITING`, `PAUSED`, `FAILED`, and `DONE` are explicit states. While a job is pending, wait or poll; do not keep asking the LLM whether it is finished.

Collections:

| Collection | Canonical responsibility |
|---|---|
| campaigns | Current goal/version, protocol ID, state, experiment limits, chosen final config |
| experiments | Unique experiment key, config, status, lease/attempt, numerical result, artifact references |
| memories | Candidate notes or verified record references, scope, kind, source IDs, optional embedding |
| events | Append-only UI/audit events, actual timestamps, model/tool metadata, provenance |

Keep the metrics and completed status together in the experiment document. Its durable commit is the source of truth. A recovery pass can regenerate any missing memory/UI projections after a crash between result commit and event creation. Projection operations must themselves be idempotent.

Deduplication key: hash of normalized EFFECTIVE configuration + immutable protocol hash. The protocol includes dataset file hashes, exact split IDs, evaluator code version, and seed. Ignore unused parameters when hashing. An unchanged nine-channel measurement can remain reusable when only the maximum allowed channel count changes; a changed dataset or evaluator cannot silently reuse old measurements.

Use a unique index for the experiment key within a campaign. Claim queued work atomically. If using leases, fence result commits with an attempt/lease token so an expired worker cannot overwrite the active attempt. This prevents duplicate accepted results, not every conceivable duplicate external computation.

The frontend needs only five areas: goal/current constraint; observed metric trajectory; experiment queue; retrieved evidence with source IDs; and context-reset/restart timeline. Display real EEG or its measured spectrum from the loaded file, not an unrelated brain image. Use polling instead of building an elaborate streaming system.

## 7. Jev: useful, optional, narrowly bounded

Jev routes raw text notes into `failure_memory`, `research_note`, `ignore`, or `review`. All raw logs are retained even when excluded from working memory. This tests whether a small decision model can handle the note-routing step without invoking the main planner for every note.

The official OpenRouter route is `POST /api/alpha/decisions`, model `typesafe/jev-1.13`, with `state` and `questions`, not a chat `messages` payload [S6]. The provided `jev_gate.py` implements that shape with an explicit fallback. No live call has been tested here. Read the returned provider/model/request ID and usage instead of assuming the call used Jev.

Do not use Jev to compute scores, compare dates, enforce budget thresholds, validate split disjointness, or declare a result scientifically correct. TypeSafe documents weaknesses in arithmetic, indirection, irrelevant long context, and adversarial inputs [S9]. Typed output is not guaranteed correctness. Do not treat a confidence number as a measured accuracy rate on this workload.

Initial gate: one authenticated call, then a small hand-labeled fixture of about 20 notes with ambiguous and adversarial cases. This is a smoke test, not calibration evidence. If the endpoint/account is unavailable or behavior is unreliable, retain notes as unverified and route to the main planner/review. Display fallback explicitly. Do not let Jev block submission.

## 8. Validation before claiming success

### Already performed in this starter
Fifteen offline unit tests passed in the authoring runtime. They exercise both numerical pipelines on SYNTHETIC signals, split overlap and duplicate-epoch guards, missing channels/nonfinite input, configuration allowlisting, deduplication hashing, and Jev request/response/fallback handling. See `offline_test_output.txt`.

### Not yet performed
Real EDF download and numerical evaluation, authenticated Jev or planner calls, live Atlas connectivity, actual Vector Search, a persisted worker restart, multi-agent/multi-worker behavior, the frontend, and the paired memory benchmark. Binary downloads into the authoring runtime failed; no real-data accuracy or end-to-end success is claimed.

### Gates for the team
1. REAL DATA: run smoke mode and inspect actual labels, finite metrics, train/validation/test membership, file hashes, and measured runtime. At least one allowed pipeline must work. Then run demo mode. A low score is not a software failure; keep it rather than cherry-pick data.
2. ACCOUNTS: ping the emailed Atlas sandbox; insert/read a disposable test record; make one planner call; verify the selected embedding/index path; test Jev only as optional.
3. RECOVERY: complete a real job, kill the worker, start a new process, and verify that campaign ID, completed job key, and metrics survive. Then test a kill during computation separately.
4. MEMORY: bury a genuinely useful earlier result/note beneath separately labeled distractor events, clear in-process context, and show the recovered evidence IDs and current goal. Add an obsolete-protocol record; it must not enter current numerical evidence.
5. FAIR ABLATION: compare recent-window context, rolling-summary context, and the proposed evidence-based context on the same histories, planner/model settings, tool interfaces, and hard guards. Aim for five scenarios per arm as a demo-scale check, not a robust benchmark. Measure correct historical-reference selection, obsolete-reference mistakes, repeated proposals, input-token usage, and cost. Do not manufacture a baseline failure or assume the proposed method wins.

All arms should share the same numerical evaluator and hard authorization/budget rules. Test persistence separately from semantic-memory benefits. Otherwise a comparison can accidentally attribute ordinary database safeguards to an AI-memory improvement.

## 9. Honest long-horizon demonstration

Today's small EEG subset is a micro-workload. It does not itself require billions of language-model tokens or weeks of reasoning. Do not inflate it with sleeps or redundant LLM calls. The larger intended workflow is repeated dataset ingestion, subject-level evaluation, experiment execution, failures, changing constraints, and retained evidence under one persistent mission.

Demonstrate those failure modes today with genuine process/context resets and a bounded real experiment campaign. Add a stress fixture at 1,000 and then 10,000 synthetic note/event records only after the core works. Label each record `synthetic_stress`, keep it out of scientific result summaries, and report the actual history size, retrieval behavior, and context size tested. Do not claim those records are independent human recordings or completed experiments.

A later larger run is a scaling roadmap, not evidence for today's submission. The guide's billion-token target remains unproven until actually tested. Ask the organizers what scale evidence they expect; do not invent an exception.

## 10. Two-person execution budget

These are maximum work allocations, not guaranteed completion estimates. Let D be the confirmed submission cutoff. Protect D minus 90 minutes for recording, README, upload, and submission. Delete features rather than consume that buffer.

| Budget block | Developer A | Developer B | Exit condition |
|---|---|---|---|
| First 30 minutes | Run real EEG smoke gate; freeze task/splits | Verify Atlas sandbox, planner, embedding access; one optional Jev call; confirm D | Real job metrics and a live Atlas write/read |
| Next 90 minutes | Experiment adapter, canonical result commit, single worker | Minimal API/dashboard, campaign and result displays | End-to-end job visible in UI |
| Next 90 minutes | Bounded planner loop, schema/permission/budget checks | Evidence packet builder, scoped memory retrieval, optional Jev note routing | Several real experiments with linked evidence |
| Next 60 minutes | Kill/restart tests; effective-key deduplication | Constraint-change display and five memory scenarios | Demonstrated recovery and current eligibility |
| Remaining pre-freeze time | Small fair ablation, fix defects | Polish evidence/timeline view; stress fixture only if stable | Measured comparison or honest test status |
| Final 90 minutes before D | README, attribution, public-repo/access checks | On-site one-minute capture, upload, audio/access check | Submission completed with both teammates listed |

If fewer than four focused build hours remain, remove Jev first, then synthetic scale testing and visual polish. Preserve the real-data loop, Atlas state, one context reconstruction, one restart proof, and the video. Never cut the sandbox requirement or source attribution.

## 11. One-minute video storyboard

0–8 seconds: “Long-running agents lose the reasoning behind old experiments. Second Shift reconstructs the next decision from durable evidence.” Show the task and actual EEG input.

8–20 seconds: Show completed real configurations, measured validation results, and one source-linked note.

20–33 seconds: Kill/restart the Python worker or show the authentic on-site recording of that operation. The same campaign reappears; completed job keys are not recomputed.

33–47 seconds: Clear working context, reduce electrode budget to nine, and show the new context packet retrieving an eligible earlier result and retaining current constraints. Display its source record.

47–56 seconds: Show only actual benchmark outcomes: recovery, evidence selection, token counts, repeated proposals, or abstention. Show Jev request/provider/label only if the live integration worked.

56–60 seconds: Show the original harness code and Atlas collections. End with: “One persistent mission; bounded context; decisions grounded in measured results.”

Never use invented rising accuracy numbers or claim a recording shows days of execution when it shows a short replay.

## 12. Submission text draft

“Second Shift is a MongoDB-backed harness that preserves a research agent's goals, measured results, and source-linked memory across context resets and worker failures. Our reference workload executes real EEG motor-imagery experiments, retrieves relevant prior evidence, and re-evaluates configurations when constraints change. We demonstrate [insert measured recovery/memory results], with numerical validation enforced by code and [include Jev note routing only if it actually ran].”

## 13. Build exclusions

No full Aleph raw-data pipeline; no EEG foundation-model training; no arbitrary generated-code execution; no multi-agent society; no literature crawler; no voice interface; no generic SDK; no automatic model switching; no whole-brain reconstruction claim; no unsupported SOTA claim; no assumption that a pretty dashboard establishes long-horizon reliability.

The strongest attainable submission is a narrow agent harness with an unmistakable, reproducible failure-and-recovery demonstration and real numerical evidence—not the largest feature list.


## 14. Source audit — checked September 26, 2026

The organizer requirements come from the user's uploaded `[EXTERNAL] THE HARNESS ENGINEERING & MODEL WRANGLING HACKATHON RESOURCE GUIDE.html`. The saved HTML embeds nearly all body content on original line 62; it was converted to readable text for review. The guide is the authority for this plan, not an invented judging rubric.

S1. Aleph Neuro, *Ultrasound imaging of the brain*, June 24, 2026.
https://alephneuro.com/blog/ultrasound-brain

S2. Aleph's public microbubbles repository and README. The article's older `braindump` link redirects here. Inspected default-branch tree SHA: ae169ea2430d23550835863e2e1e53c4231d4181.
https://github.com/alephneuro/microbubbles
https://api.github.com/repos/alephneuro/microbubbles/git/trees/main?recursive=1

S3. Schalk, G. (2009). *EEG Motor Movement/Imagery Dataset*, version 1.0.0. PhysioNet. DOI: 10.13026/C28G6P. Follow the dataset's Open Data Commons Attribution License and citation instructions. The EEG acquisition data are not our original work.
https://physionet.org/content/eegmmidb/1.0.0/

S4. MNE documentation, `mne.datasets.eegbci.load_data`, run/task mapping. Runs 6/10/14 are imagined hands vs feet; 4/8/12 are imagined left vs right.
https://mne.tools/stable/generated/mne.datasets.eegbci.load_data.html

S5. MNE, *Motor imagery decoding from EEG data using the Common Spatial Pattern (CSP)*. This is a primary maintained implementation reference, not our measured result. Our starter uses its own explicitly separated train/validation protocol and does not claim to reproduce the example's reported accuracy.
https://mne.tools/stable/auto_examples/decoding/decoding_csp_eeg.html

S6. OpenRouter, *What Is Jev? TypeSafe's Decision Model Explained for Developers*, September 21, 2026. Documents the Decisions API, model ID, and SDK routing. Provider documentation does not establish account-specific access or performance.
https://openrouter.ai/blog/insights/what-is-jev/

S7. LangChain, *Persistence*. Existing checkpoint/store functionality is prior art; checkpointing alone is not a novel product claim.
https://docs.langchain.com/oss/python/langgraph/persistence

S8. PhysioNet subject 1 directory. Lists relevant EDF files at approximately 2.5 MB each.
https://physionet.org/content/eegmmidb/1.0.0/S001/

S9. TypeSafe, *Jev 1.13 jaggedness*. Numerical precision, long irrelevant context, and adversarial-input limitations.
https://docs.typesafe.ai/model-jaggedness/jev-1.13

S10. TypeSafe API and model references.
https://docs.typesafe.ai/api
https://docs.typesafe.ai/models

S11. Public event page, corroborating the September 26/30 demo/finalist structure.
https://luma.com/j4jecx72

### Required dataset acknowledgements
Schalk G., McFarland D.J., Hinterberger T., Birbaumer N., Wolpaw J.R. (2004). BCI2000: A General-Purpose Brain-Computer Interface (BCI) System. IEEE Transactions on Biomedical Engineering 51(6):1034–1043. The current PhysioNet page additionally requests its platform citation; retain the page's current citation information in the submitted repository.

Credit MNE-Python and scikit-learn for the numerical tools. Credit only the newly built harness, adapter integration, tests, and UI as the team's original work.
