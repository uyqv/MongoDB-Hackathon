"""Measured recovery and constraint-change checks for the README and video. OWNER: Andrew.

    python -m eval.demo_checks recovery     # SIGKILL mid-job, restart, verify invariants
    python -m eval.demo_checks constraint   # 64 -> 9 channels mid-campaign, verify re-eligibility
    python -m eval.demo_checks all

Each check spawns real worker processes on real EEG data and asserts on what
Atlas holds afterwards. Results are appended to eval/checks.json.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from harness import eeg, store
from harness.contracts import is_eligible
from harness.db import get_db, log_event, now_iso
from harness.worker import OBJECTIVE

OUT = Path("eval/checks.json")


def _worker(*args: str) -> int:
    return subprocess.run([sys.executable, "-m", "harness.worker", *args],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode


def _new_campaign(db, max_channels: int, budget: int) -> str:
    protocol, _ = eeg.load_protocol("demo")
    store.ensure_indexes(db)
    return store.create_campaign(db, protocol=protocol, objective=OBJECTIVE, max_channels=max_channels,
                                 max_experiments=budget)


def _change_constraint(db, cid: str, max_channels: int, reason: str) -> None:
    try:
        from harness.control import change_constraint
    except ImportError:
        change_constraint = None
    if change_constraint is not None:
        change_constraint(db, cid, max_channels, reason)
        return
    before = store.get_campaign(db, cid)
    after = db.campaigns.find_one_and_update(
        {"_id": cid}, {"$inc": {"goal_version": 1}, "$set": {"constraints": {"max_channels": max_channels},
                                                            "updated_at": now_iso()}},
        return_document=True)
    db.campaigns.update_one({"_id": cid}, {"$push": {"goal_history": {
        "version": after["goal_version"], "constraints": after["constraints"], "changed_at": now_iso(),
        "reason": reason}}})
    log_event(db, cid, "goal_changed", {"from_version": before["goal_version"], "to_version": after["goal_version"],
                                        "old_constraints": before["constraints"],
                                        "new_constraints": after["constraints"], "reason": reason})


def _commits(db, cid: str) -> Counter:
    return Counter(ev["payload"]["experiment_id"] for ev in db.events.find({"campaign_id": cid, "type": "job_committed"}))


def check_recovery(db) -> dict:
    cid = _new_campaign(db, max_channels=64, budget=5)
    rc_crash = _worker("--campaign", cid, "--crash-after-claim", "3")
    done_before = {e["_id"] for e in db.experiments.find({"campaign_id": cid, "status": "done"})}
    crashed = db.experiments.find_one({"campaign_id": cid, "status": "running"})
    rc_restart = _worker("--campaign", cid)
    camp = store.get_campaign(db, cid)
    commits = _commits(db, cid)
    crashed_after = db.experiments.find_one({"_id": crashed["_id"]}) if crashed else None
    starts = [ev["payload"] for ev in db.events.find({"campaign_id": cid, "type": "worker_start"}).sort("ts", 1)]
    checks = {
        "worker_was_sigkilled": rc_crash == -9,
        "job_left_running_by_crash": crashed is not None,
        "restart_exited_cleanly": rc_restart == 0,
        "restart_reported_resume": len(starts) == 2 and starts[1]["resumed"],
        "done_experiments_not_recomputed": all(commits[e] == 1 for e in done_before),
        "every_experiment_committed_once": all(n == 1 for n in commits.values()),
        "crashed_job_rerun_as_attempt_2": bool(crashed_after and crashed_after["attempt"] == 2
                                               and crashed_after["status"] == "done"),
        "sealed_test_scored_once": bool(camp.get("final"))
        and db.events.count_documents({"campaign_id": cid, "type": "finalized"}) == 1,
    }
    return {"check": "recovery", "campaign_id": cid, "passed": all(checks.values()), "checks": checks,
            "done_before_crash": len(done_before), "experiments": len(commits),
            "final_test_balanced_accuracy": (camp.get("final") or {}).get("test_balanced_accuracy")}


def check_constraint(db) -> dict:
    cid = _new_campaign(db, max_channels=64, budget=8)
    _worker("--campaign", cid, "--max-steps", "4")
    camp = store.get_campaign(db, cid)
    inc_before = store.incumbent(db, camp)
    commits_at_change = sum(_commits(db, cid).values())
    _change_constraint(db, cid, 9, "hardware now has a 9-electrode headset")
    camp = store.get_campaign(db, cid)
    inc_after = store.incumbent(db, camp)             # recomputed from existing results, no new runs
    commits_after_change = sum(_commits(db, cid).values())
    _worker("--campaign", cid)
    camp = store.get_campaign(db, cid)
    later = list(db.experiments.find({"campaign_id": cid, "goal_version_at_proposal": camp["goal_version"]}))
    checks = {
        "goal_version_bumped": camp["goal_version"] == 2,
        "eligibility_recomputed_without_new_runs": commits_at_change == commits_after_change,
        "incumbent_is_eligible_after_change": inc_after is None or is_eligible(inc_after["config"], camp["constraints"]),
        "all_later_proposals_eligible": bool(later) and all(e["n_channels"] <= 9 for e in later),
        "final_respects_current_goal": bool(camp.get("final")) and camp["final"]["constraints"]["max_channels"] == 9
        and is_eligible(camp["final"]["config"], {"max_channels": 9}),
    }
    return {"check": "constraint", "campaign_id": cid, "passed": all(checks.values()), "checks": checks,
            "incumbent_before": inc_before and {"label": inc_before["label"],
                                                "val": inc_before["result"]["val_balanced_accuracy"]},
            "incumbent_after_change": inc_after and {"label": inc_after["label"],
                                                     "val": inc_after["result"]["val_balanced_accuracy"]},
            "final": {k: camp["final"].get(k) for k in ("label", "val_balanced_accuracy", "test_balanced_accuracy")}
            if camp.get("final") else None}


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    db = get_db()
    results = []
    if which in ("recovery", "all"):
        results.append(check_recovery(db))
    if which in ("constraint", "all"):
        results.append(check_constraint(db))
    history = json.loads(OUT.read_text()) if OUT.exists() else []
    for r in results:
        r["db"] = db.name
        r["ran_at"] = now_iso()
    OUT.write_text(json.dumps(history + results, indent=2))
    print(json.dumps(results, indent=2))
    sys.exit(0 if all(r["passed"] for r in results) else 1)


if __name__ == "__main__":
    main()
