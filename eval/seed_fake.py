"""UI-development seed data for DB second_shift_david ONLY. OWNER: David.

Fake, schema-conformant docs so the API and dashboard can be built before the
real worker lands. Every doc carries "fake": True. Refuses to run when DB_NAME is
"second_shift". Never used in the demo or the video.

Run: python -m eval.seed_fake
"""
from __future__ import annotations

import os
import random
from datetime import datetime, timedelta, timezone

from harness import contracts as C
from harness.db import get_db

ALLOWED_DB = "second_shift_david"
CAMPAIGN_ID = "camp_fa4e0001"


def _iso(t: datetime) -> str:
    return t.isoformat(timespec="milliseconds")


def _check_db_name() -> str:
    name = os.environ.get("DB_NAME", C.DB_NAME_DEFAULT)
    if name != ALLOWED_DB:
        raise SystemExit(f"refusing to seed fake data into DB {name!r}; set DB_NAME={ALLOWED_DB}")
    return name


def clear_fake(db) -> dict:
    return {c: db[c].delete_many({"fake": True}).deleted_count for c in C.COLLECTIONS}


def build(t0: datetime | None = None) -> dict[str, list[dict]]:
    """Build every fake doc in memory. Deterministic for a given t0."""
    rng = random.Random(7)
    t0 = t0 or datetime.now(timezone.utc) - timedelta(minutes=30)
    protocol = {
        "dataset": "FAKE eegmmidb", "subjects": [1, 2, 3, 4, 5], "runs": {"train": 6, "val": 10, "test": 14},
        "evaluator_version": C.EVALUATOR_VERSION, "seed": C.SEED, "fake": True,
    }
    pid = C.protocol_id(protocol)
    cfgs = C.all_configs()

    def pick(**want):
        return next(c for c in cfgs if all(c.get(k) == v for k, v in want.items()))

    chosen = [
        pick(method="csp_lda", band="broad_8_30", window="w1.0_3.0", channels="all64", n_components=6),
        pick(method="csp_lda", band="mu_8_12", window="w0.5_2.5", channels="central9", n_components=4),
        pick(method="bandpower_lr", band="beta_13_30", window="w1.0_3.0", channels="motor21", C=1.0),
        pick(method="csp_lda", band="broad_8_30", window="w1.0_3.0", channels="central9", n_components=4),
        pick(method="bandpower_lr", band="mu_8_12", window="w1.5_3.5", channels="all64", C=0.1),
        pick(method="csp_lda", band="lowbeta_13_20", window="w1.0_3.0", channels="motor21", n_components=6),
        pick(method="bandpower_lr", band="highbeta_20_30", window="w0.5_2.5", channels="central9", C=1.0),
        pick(method="csp_lda", band="beta_13_30", window="w1.5_3.5", channels="central9", n_components=2),
    ]
    statuses = ["done", "done", "done", "done", "failed", "done", "running", "queued"]

    experiments = []
    for i, (cfg, status) in enumerate(zip(chosen, statuses)):
        key = C.experiment_key(pid, cfg)
        created = t0 + timedelta(minutes=2 * i)
        result = None
        if status == "done":
            result = {
                "val_balanced_accuracy": round(rng.uniform(0.45, 0.80), 3),
                "val_f1": round(rng.uniform(0.45, 0.78), 3),
                "n_train": 225, "n_val": 225, "n_channels": C.CHANNEL_COUNTS[cfg["channels"]],
                "fit_seconds": round(rng.uniform(0.5, 4.0), 2), "evaluator_version": C.EVALUATOR_VERSION,
            }
        fallback = i == 5
        experiments.append({
            "_id": C.experiment_doc_id(CAMPAIGN_ID, key), "key": key, "campaign_id": CAMPAIGN_ID,
            "protocol_id": pid, "config": cfg, "label": C.config_label(cfg),
            "n_channels": C.CHANNEL_COUNTS[cfg["channels"]], "status": status,
            "attempt": 2 if i == 6 else 1,
            "lease": ({"owner": "w_fake", "token": "tok_fake", "expires_at": _iso(created + timedelta(seconds=15))}
                      if status == "running" else None),
            "proposed_by": {
                "model": "deterministic-fallback" if fallback else "anthropic/claude-sonnet-5",
                "request_id": None if fallback else f"gen-fake-{i:04d}",
                "rationale": "FAKE rationale for UI development.",
                "evidence_ids": [], "fallback_used": fallback,
            },
            "goal_version_at_proposal": 1 if i < 4 else 2,
            "result": result,
            "error": "FAKE: ValueError in fit" if status == "failed" else None,
            "created_at": _iso(created),
            "started_at": _iso(created + timedelta(seconds=5)) if status != "queued" else None,
            "finished_at": _iso(created + timedelta(seconds=40)) if status in ("done", "failed") else None,
            "fake": True,
        })

    goal_history = [
        {"version": 1, "constraints": {"max_channels": 64}, "changed_at": _iso(t0), "reason": "initial goal"},
        {"version": 2, "constraints": {"max_channels": 9}, "changed_at": _iso(t0 + timedelta(minutes=7)),
         "reason": "FAKE: headset budget cut to 9 channels"},
    ]
    campaign = {
        "_id": CAMPAIGN_ID,
        "objective": "FAKE: maximize val balanced accuracy, imagined fists vs feet",
        "goal_version": 2, "constraints": {"max_channels": 9}, "goal_history": goal_history,
        "protocol": protocol, "protocol_id": pid, "budget": {"max_experiments": 10},
        "state": "EXECUTE", "context_epoch": 1, "final": None,
        "created_at": _iso(t0), "updated_at": _iso(t0 + timedelta(minutes=16)), "fake": True,
    }

    done = [e for e in experiments if e["status"] == "done"]
    failed = [e for e in experiments if e["status"] == "failed"]
    memories = []

    def mem(i, kind, text, source_ids, verified, synthetic=False, status="active"):
        memories.append({
            "_id": f"m_fa4e{i:08x}", "campaign_id": CAMPAIGN_ID, "protocol_id": pid, "kind": kind,
            "text": text, "source_ids": source_ids, "verified": verified, "status": status,
            "synthetic": synthetic, "embedding": None,
            "created_at": _iso(t0 + timedelta(minutes=3 + i)), "fake": True,
        })

    mem(1, "verified_result", C.render_result_text(done[0]), [done[0]["_id"]], True)
    mem(2, "verified_result", C.render_result_text(done[3]), [done[3]["_id"]], True)
    mem(3, "failure", C.render_failure_text(failed[0]), [failed[0]["_id"]], False)
    mem(4, "hypothesis", "FAKE: mu-band CSP on central channels may hold up under the 9-channel budget.",
        [done[1]["_id"]], False)
    mem(5, "synthetic_stress", "FAKE synthetic distractor: gamma band looked promising in an unrelated study.",
        [], False, synthetic=True)
    mem(6, "synthetic_stress", "FAKE synthetic distractor: a 128-channel montage was best last year.",
        [], False, synthetic=True)

    events = []

    def ev(minute, type_, payload=None, worker_id="w_fake"):
        events.append({"campaign_id": CAMPAIGN_ID, "ts": _iso(t0 + timedelta(minutes=minute)), "type": type_,
                       "worker_id": worker_id, "payload": payload or {}, "fake": True})

    ev(0.0, "campaign_created", {"max_channels": 64, "budget": 10})
    ev(0.1, "worker_start", {"resumed": False, "reused_done": 0})
    for i, e in enumerate(experiments):
        m = 2 * i
        ev(m + 0.1, "proposal", {"experiment_id": e["_id"], "label": e["label"],
                                 "fallback_used": e["proposed_by"]["fallback_used"]})
        ev(m + 0.2, "job_queued", {"experiment_id": e["_id"]})
        if e["status"] == "done":
            ev(m + 1.0, "job_committed", {"experiment_id": e["_id"],
                                         "val_balanced_accuracy": e["result"]["val_balanced_accuracy"]})
        elif e["status"] == "failed":
            ev(m + 1.0, "job_failed", {"experiment_id": e["_id"], "error": e["error"]})
    ev(7.0, "goal_changed", {"from_version": 1, "to_version": 2, "old_constraints": {"max_channels": 64},
                             "new_constraints": {"max_channels": 9}, "reason": "FAKE: headset budget cut"})
    ev(9.5, "context_reset", {"context_epoch": 1}, worker_id=None)
    ev(11.0, "worker_killed", {"pid": 99999, "signal": "SIGKILL"}, worker_id=None)
    ev(11.5, "worker_start", {"resumed": True, "reused_done": 4})
    ev(11.6, "job_reused", {"experiment_id": done[0]["_id"]})
    ev(12.0, "lease_expired", {"experiment_id": experiments[6]["_id"], "attempt": 1})
    ev(12.1, "stale_commit_rejected", {"experiment_id": experiments[6]["_id"], "attempt": 1})
    events.sort(key=lambda d: d["ts"])

    eligible_done = [e for e in done if C.is_eligible(e["config"], campaign["constraints"])]
    inc = max(eligible_done, key=lambda e: e["result"]["val_balanced_accuracy"])
    retrieved = [
        {"memory_id": m["_id"], "kind": m["kind"], "text": m["text"], "source_ids": m["source_ids"],
         "score": s, "verified": m["verified"], "retrieval": "vector"}
        for m, s in zip([memories[1], memories[3], memories[2]], [0.83, 0.71, 0.64])
    ]
    packet = {
        "campaign_id": CAMPAIGN_ID, "protocol_id": pid, "strategy": "evidence",
        "goal": {"objective": campaign["objective"], "goal_version": 2, "constraints": {"max_channels": 9},
                 "budget": {"max_experiments": 10, "used": len(experiments), "remaining": 10 - len(experiments)}},
        "incumbent": {"experiment_id": inc["_id"], "label": inc["label"], "config": inc["config"],
                      "val_balanced_accuracy": inc["result"]["val_balanced_accuracy"]},
        "pending": [{"experiment_id": e["_id"], "label": e["label"], "status": e["status"]}
                    for e in experiments if e["status"] in ("queued", "running")],
        "recent": [{"experiment_id": e["_id"], "label": e["label"], "status": e["status"],
                    "val_balanced_accuracy": (e["result"] or {}).get("val_balanced_accuracy"),
                    "eligible": C.is_eligible(e["config"], campaign["constraints"])} for e in experiments[-4:]],
        "retrieved": retrieved,
        "tried_keys": [e["key"] for e in experiments],
        "surface": C.surface_summary(),
        "token_estimate": 1850, "budget_tokens": 4000,
        "context_epoch": 1, "goal_version": 2,
        "ts": _iso(t0 + timedelta(minutes=14)),
        "planner_result": {
            "action": "propose", "config": chosen[7], "rationale": "FAKE rationale.",
            "evidence_ids": [inc["_id"], memories[1]["_id"]], "model": "anthropic/claude-sonnet-5",
            "request_id": "gen-fake-0007",
            "usage": {"input_tokens": 1900, "output_tokens": 120, "cost_usd": 0.0075, "source": "provider"},
            "fallback_used": False, "fallback_reason": None,
        },
        "fake": True,
    }
    return {"campaigns": [campaign], "experiments": experiments, "memories": memories,
            "events": events, "packets": [packet]}


def main() -> None:
    name = _check_db_name()
    db = get_db(name)
    removed = clear_fake(db)
    docs = build()
    counts = {}
    for coll, rows in docs.items():
        if rows:
            db[coll].insert_many(rows)
        counts[coll] = len(rows)
    print(f"DB {name}: removed {removed}, inserted {counts}, campaign {CAMPAIGN_ID}")


if __name__ == "__main__":
    main()
