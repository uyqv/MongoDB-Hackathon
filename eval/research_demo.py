"""Real research campaign: SIGKILL in the commit/assessment gap, change goal, resume."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from harness import control, eeg, hypotheses, research, store
from harness.db import get_db, now_iso
from eval.research_benchmark import save


def main():
    db = get_db()
    store.ensure_indexes(db)
    protocol, _ = eeg.load_protocol("demo", 1)
    cid = store.create_campaign(db, protocol=protocol, objective="Uncertainty-aware EEG research and recovery demonstration",
                                max_channels=64, max_experiments=10, policy="research_v1")
    save(Path("output/research/live_campaign.json"), {"campaign_id": cid, "db": db.name})
    print(f"research campaign {cid}", flush=True)
    env = {**os.environ, "DB_NAME": db.name}
    command = [sys.executable, "-m", "harness.worker", "--campaign", cid]
    logpath = Path("output/research/live_campaign.log")
    with logpath.open("w") as log:
        killed = subprocess.run(command + ["--crash-after-commit", "4"], env=env, stdout=log, stderr=subprocess.STDOUT)
        if killed.returncode != -9:
            raise RuntimeError(f"expected SIGKILL, got {killed.returncode}; see {logpath}")
        camp = store.get_campaign(db, cid)
        committed = store.experiments(db, cid)
        rank_before = research.rank(camp, committed)
        pending_before = db.hypotheses.count_documents({"campaign_id": cid, "status": "pending"})
        assert len(committed) == 4 and all(e["status"] == "done" for e in committed)
        assert pending_before == 1
        print("killed after 4 commits; one hypothesis pending", flush=True)
        rank_after = research.rank(store.get_campaign(db, cid), store.experiments(db, cid))
        # Leave the pending claim untouched: the resumed worker must repair it.
        control.change_constraint(db, cid, 9, "Real recovery demonstration: electrode budget reduced after SIGKILL")
        control.reset_context(db, cid)
        resumed = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
        if resumed.returncode:
            raise RuntimeError(f"resume failed: see {logpath}")
    camp = store.get_campaign(db, cid)
    snapshots = list(db.hypotheses.find({"campaign_id": cid}).sort("_id", 1))
    hypotheses.reconcile(db, camp)
    projection_idempotent = snapshots == list(db.hypotheses.find({"campaign_id": cid}).sort("_id", 1))
    exps = store.experiments(db, cid)
    claims = list(db.hypotheses.find({"campaign_id": cid}, {"_id": 0}))
    invariants = {
        "sigkill_in_commit_gap": killed.returncode == -9 and pending_before == 1,
        "ranking_reconstructed": rank_before == rank_after,
        "assessments_idempotent": projection_idempotent,
        "ten_distinct_experiments": len(exps) == 10,
        "no_committed_experiment_reexecuted": all(e["attempt"] == 1 for e in exps),
        "each_result_committed_once": all(db.events.count_documents({"campaign_id": cid, "type": "job_committed",
                                         "payload.experiment_id": e["_id"]}) == 1 for e in exps),
        "one_assessment_per_experiment": len(claims) == len(exps) and all(h["status"] != "pending" for h in claims),
        "later_proposals_respect_nine_channels": all(e["n_channels"] <= 9 for e in exps if e["goal_version_at_proposal"] == 2),
        "final_respects_goal": camp["final"] is not None and camp["final"]["constraints"]["max_channels"] == 9,
        "one_finalization": db.events.count_documents({"campaign_id": cid, "type": "finalized"}) == 1,
    }
    report = {"ran_at": now_iso(), "campaign_id": cid, "db": db.name, "invariants": invariants,
              "final": camp["final"], "hypotheses": claims,
              "llm_calls": list(db.events.find({"campaign_id": cid, "type": "llm_call"}, {"_id": 0}))}
    save(Path("eval/research_demo.json"), report)
    print(json.dumps({"campaign_id": cid, "invariants": invariants, "final": camp["final"]}, indent=2))
    if not all(invariants.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
