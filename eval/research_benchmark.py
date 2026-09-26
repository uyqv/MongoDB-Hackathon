"""Four-policy, equal-budget validation replay. Oracle outcomes never enter planner input.

python -m eval.research_benchmark --precompute
python -m eval.research_benchmark
Runs are policy comparisons on one dataset, not independent scientific replications.
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from harness import contracts as C, eeg, research
from harness.context import assemble_packet
from harness.db import now_iso
from harness.hypotheses import assessment
from harness.worker import call_planner, fallback_plan, guard

ARMS = ("current_planner", "hybrid", "optimizer", "random")
SCENARIOS = ("constant64", "reduce_to9_after5")
ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "output/research/oracle.json"
OUTPUT = ROOT / "eval/research_results.json"


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(obj, indent=2, allow_nan=False))
    temporary.replace(path)


def precompute(path=ORACLE):
    protocol, data = eeg.load_protocol("demo", evidence_version=1)
    pid = C.protocol_id(protocol)
    oracle = json.loads(path.read_text()) if path.exists() else {"protocol": protocol, "protocol_id": pid, "outcomes": {}}
    if oracle["protocol_id"] != pid:
        raise ValueError("oracle protocol changed; use a different output path")
    for i, cfg in enumerate(C.all_configs(), 1):
        key = C.experiment_key(pid, cfg)
        if key in oracle["outcomes"]:
            continue
        try:
            outcome = {"status": "done", "result": eeg.run_experiment(cfg, protocol, data)}
        except Exception as exc:
            outcome = {"status": "failed", "result": None, "error": f"{type(exc).__name__}: {exc}"}
        oracle["outcomes"][key] = {"config": cfg, **outcome}
        save(path, oracle)
        if i % 25 == 0:
            print(f"oracle {i}/225", flush=True)
    return oracle


def run_rollout(oracle, arm, scenario, seed, *, planner=call_planner):
    """Only this evaluator owns the oracle. Selectors see the observed history."""
    cid = f"benchmark_{arm}_{scenario}_{seed}"
    campaign = {"_id": cid, "protocol_id": oracle["protocol_id"], "goal_version": 1,
                "objective": "Maximize validation balanced accuracy within current channel and experiment budgets.",
                "constraints": {"max_channels": 64}, "budget": {"max_experiments": 10}, "research_seed": seed}
    observations, claims, steps = [], [], []
    rng = random.Random(seed)
    for step in range(10):
        if step == 5 and scenario == "reduce_to9_after5":
            campaign["constraints"] = {"max_channels": 9}
            campaign["goal_version"] += 1
        initialization = step < 3
        use_research = arm in ("hybrid", "optimizer") or initialization
        campaign["policy"] = "research_v1" if use_research else "legacy"
        packet = assemble_packet(campaign, observations, hypotheses=claims[-3:][::-1])
        started = time.perf_counter()
        if initialization or arm == "optimizer":
            result = fallback_plan(packet, "benchmark numerical selection")
            result.update(model="numerical_policy", fallback_used=False, fallback_reason=None)
        elif arm == "random":
            tried = {e["key"] for e in observations}
            candidates = [c for c in C.all_configs() if C.is_eligible(c, campaign["constraints"])
                          and C.experiment_key(campaign["protocol_id"], c) not in tried]
            result = {"action": "propose", "config": rng.choice(candidates), "rationale": "Seeded uniform random choice",
                      "evidence_ids": [], "model": "random", "fallback_used": False, "usage": {}}
        else:
            result = planner(packet)
        if result["action"] != "propose":
            raise AssertionError("policy stopped before spending an available budget")
        problem = guard(packet, result)
        if problem:
            raise AssertionError(f"invalid benchmark decision: {problem}")
        cfg = result["config"]
        key = C.experiment_key(campaign["protocol_id"], cfg)
        # The only oracle lookup available to a policy is its accepted selection.
        observed = copy.deepcopy(oracle["outcomes"][key])
        experiment = {**observed, "_id": C.experiment_doc_id(cid, key), "key": key,
                      "campaign_id": cid, "protocol_id": campaign["protocol_id"], "config": cfg,
                      "label": C.config_label(cfg), "proposed_by": result,
                      "created_at": str(step), "goal_version_at_proposal": campaign["goal_version"]}
        if "hypothesis" in result:
            reference_id = result["hypothesis"].get("reference_experiment_id")
            ref = next((e for e in observations if e["_id"] == reference_id), None)
            claims.append({"_id": "h_" + experiment["_id"], "experiment_id": experiment["_id"],
                           **result["hypothesis"], **assessment(experiment, ref)})
        observations.append(experiment)
        eligible = [e for e in observations if e["status"] == "done" and C.is_eligible(e["config"], campaign["constraints"])]
        best = max((e["result"]["val_balanced_accuracy"] for e in eligible), default=None)
        # Optimum is judge-only; it is never added to a packet or hypothesis.
        optimum = max(e["result"]["val_balanced_accuracy"] for e in oracle["outcomes"].values()
                      if e["status"] == "done" and C.is_eligible(e["config"], campaign["constraints"]))
        steps.append({"step": step + 1, "config": cfg, "key": key, "max_channels": campaign["constraints"]["max_channels"],
                      "best_eligible_accuracy": best, "eligible_validation_optimum": optimum,
                      "regret": optimum - best if best is not None else None,
                      "selection_seconds": time.perf_counter() - started, "packet_tokens_estimate": packet["token_estimate"],
                      "result_accuracy": (observed.get("result") or {}).get("val_balanced_accuracy"),
                      "model": result.get("model"), "rationale": result["rationale"], "usage": result.get("usage", {}),
                      "fallback_used": result.get("fallback_used", False), "fallback_reason": result.get("fallback_reason"),
                      "surrogate_fallback": packet.get("research", {}).get("fallback_reason"),
                      "candidates": packet.get("research", {}).get("candidates", [])})
    return {"arm": arm, "scenario": scenario, "seed": seed, "steps": steps, "hypotheses": claims}


def summarize_runs(runs):
    summary = []
    for scenario in SCENARIOS:
        for arm in ARMS:
            rows = [r for r in runs if r["scenario"] == scenario and r["arm"] == arm]
            if not rows:
                continue
            mean = lambda vals: sum(vals) / len(vals)
            steps = [s for r in rows for s in r["steps"]]
            finals = [r["steps"][-1] for r in rows]
            summary.append({"scenario": scenario, "arm": arm, "runs": len(rows),
                            "mean_final_eligible_accuracy": mean([s["best_eligible_accuracy"] for s in finals]),
                            "mean_final_regret": mean([s["regret"] for s in finals]),
                            "mean_trajectory_regret": mean([s["regret"] for s in steps if s["regret"] is not None]),
                            "input_tokens": sum(s["usage"].get("input_tokens") or 0 for s in steps if s["usage"].get("source") == "provider"),
                            "cost_usd": sum(s["usage"].get("cost_usd") or 0 for s in steps),
                            "fallbacks": sum(s["fallback_used"] for s in steps),
                            "surrogate_fallbacks": sum(bool(s["surrogate_fallback"]) for s in steps)})
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--precompute", action="store_true")
    ap.add_argument("--arms", nargs="+", choices=ARMS, default=list(ARMS))
    ap.add_argument("--seeds", nargs="+", type=int, default=list(range(5)))
    ap.add_argument("--output", type=Path, default=OUTPUT)
    ap.add_argument("--workers", type=int, choices=(1, 2), default=2,
                    help="Independent policy rollouts; writes stay serialized")
    args = ap.parse_args()
    oracle = precompute()
    if args.precompute:
        print(f"saved {len(oracle['outcomes'])} validation outcomes to {ORACLE}")
        return
    report = {"policy_version": research.POLICY, "settings": research.SETTINGS, "ran_at": now_iso(),
              "protocol_id": oracle["protocol_id"], "protocol": oracle["protocol"],
              "note": "Validation-only policy replay on one dataset; no independent replication or test-set scoring.",
              "runs": []}
    if args.output.exists():
        existing = json.loads(args.output.read_text())
        if existing["protocol_id"] != report["protocol_id"] or existing["settings"] != report["settings"]:
            raise ValueError("benchmark settings changed; choose a new report path")
        report = existing
    completed = {(r["arm"], r["scenario"], r["seed"]) for r in report["runs"]}
    tasks = [(arm, scenario, seed) for scenario in SCENARIOS for seed in args.seeds for arm in args.arms
             if (arm, scenario, seed) not in completed]
    def evaluate(task):
        arm, scenario, seed = task
        print(f"running {scenario} seed={seed} arm={arm}", flush=True)
        return run_rollout(oracle, arm, scenario, seed)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(evaluate, task) for task in tasks]
        for future in as_completed(futures):
            report["runs"].append(future.result())
            report["runs"].sort(key=lambda r: (r["scenario"], r["seed"], r["arm"]))
            report["summary"] = summarize_runs(report["runs"])
            save(args.output, report)
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
