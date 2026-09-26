# Research policy: measured results

The hybrid policy improved search under the changing electrode constraint in this small benchmark,
but finished behind the current planner under a constant constraint and used more provider tokens.
It remains opt-in. These are search-policy comparisons on one five-subject validation dataset,
not independent replications or a population-performance estimate.

## Forty equal-budget rollouts

Five seeds per policy per scenario; ten experiments per rollout; three shared seeded initial
configurations. All 225 oracle configurations were evaluated on validation only. Policies saw only
their selected results. Replay excluded live vector notes and Jev in both language-model arms.

| Policy | Constant 64: final accuracy | 64 → 9 after five: final accuracy | Constant regret | Changed-goal regret | Provider input tokens | Provider cost |
|---|---:|---:|---:|---:|---:|---:|
| Current planner | 0.7621 | 0.7270 | 0.0114 | 0.0322 | 250,572 | $0.6860 |
| Hybrid research policy | 0.7356 | 0.7480 | 0.0379 | 0.0112 | 682,682 | $1.8359 |
| Numerical optimizer | 0.7413 | 0.7424 | 0.0322 | 0.0168 | 0 | $0.0000 |
| Random search | 0.6713 | 0.7143 | 0.1022 | 0.0449 | 0 | $0.0000 |

Accuracy and regret are means across five seeds. Regret is the gap to the best eligible
validation configuration: 0.7735 with 64 channels allowed and 0.7592 with nine allowed.
The hybrid gained 2.10 percentage points over the current planner under the changed goal,
and lost 2.65 points under the constant goal. This does not establish statistical superiority.
All 400 accepted selections were eligible and distinct within their rollout. No planner
or surrogate fallback was used. Provider rate limits were retried. Costs cover completed
rollouts with provider-reported usage; numerical compute is not priced as an API cost.

[Raw benchmark outcomes and decision traces](../eval/research_results.json).

## Real crash and restart

Campaign `camp_f03bf7b8` passed all **10 recovery invariants**. Its process was SIGKILLed
after result four was committed but before its hypothesis assessment. The pending claim was
left untouched for the fresh worker to repair. The electrode limit changed from 64 to nine
and context was reset before restart. All ten experiments committed once with attempt 1.
All ten hypotheses were assessed exactly once; subsequent projection repair was idempotent.
The reconstructed numerical ranking matched before the goal change.

The campaign used three numerical initialization decisions and seven provider planner
decisions, with zero fallbacks. Final validation balanced accuracy was **0.7333**;
the sealed test score was **0.5601** on 75 trials, with one finalization.
Hypothesis outcomes: 2 `contradicted_on_validation`, 3 `exploration`, 5 `inconclusive`.

[Raw recovery evidence](../eval/research_demo.json).

## Software verification

- Full Python suite: **95 passed, 3 optional tests skipped**; follow-up targeted checks passed after final guards and snapshot changes.
- Browser state suite: **8 passed**. JavaScript syntax and diff whitespace checks passed.
- Real browser inspection verified rankings, the recorded forecast versus measured score, intervals, and hypothesis status.
- Exported research snapshot served all ten assessed experiments and ranked packets without contacting Atlas.
- The legacy protocol hash still matched an existing Atlas campaign.

Environment: Python 3.13.10, numpy 2.5.3, scipy 1.18.1, scikit-learn 1.9.1, mne 1.13.2.

[Policy details and reproduction commands](RESEARCH_POLICY.md).
