"""Durable campaign state in Atlas. OWNER: Andrew.

The experiment document is the source of truth: config, status, lease, and the
numerical result are written together. Events and memories are projections.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from harness.contracts import (
    LEASE_SECONDS, config_label, experiment_doc_id, experiment_key, is_eligible,
    n_channels, normalize_config, protocol_id,
)
from harness.db import log_event, now_iso


def ensure_indexes(db: Database) -> None:
    db.experiments.create_index([("campaign_id", ASCENDING), ("status", ASCENDING), ("created_at", ASCENDING)])
    db.events.create_index([("campaign_id", ASCENDING), ("ts", ASCENDING)])
    db.packets.create_index([("campaign_id", ASCENDING), ("ts", DESCENDING)])
    db.memories.create_index([("campaign_id", ASCENDING), ("protocol_id", ASCENDING), ("status", ASCENDING)])


def _iso_in(seconds: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat(timespec="milliseconds")


# ---------------------------------------------------------------- campaigns

def create_campaign(db: Database, *, protocol: dict, objective: str, max_channels: int,
                    max_experiments: int) -> str:
    cid = "camp_" + secrets.token_hex(4)
    now = now_iso()
    constraints = {"max_channels": int(max_channels)}
    db.campaigns.insert_one({
        "_id": cid,
        "objective": objective,
        "goal_version": 1,
        "constraints": constraints,
        "goal_history": [{"version": 1, "constraints": constraints, "changed_at": now, "reason": "initial goal"}],
        "protocol": protocol,
        "protocol_id": protocol_id(protocol),
        "budget": {"max_experiments": int(max_experiments)},
        "state": "REHYDRATE",
        "context_epoch": 0,
        "final": None,
        "created_at": now,
        "updated_at": now,
    })
    log_event(db, cid, "campaign_created", {"protocol_id": protocol_id(protocol), "constraints": constraints,
                                           "max_experiments": max_experiments, "objective": objective})
    return cid


def get_campaign(db: Database, cid: str) -> dict:
    doc = db.campaigns.find_one({"_id": cid})
    if doc is None:
        raise KeyError(f"no campaign {cid}")
    return doc


def set_state(db: Database, cid: str, state: str, worker_id: str | None = None, **payload) -> None:
    prev = db.campaigns.find_one_and_update({"_id": cid}, {"$set": {"state": state, "updated_at": now_iso()}},
                                           projection={"state": 1})
    if prev and prev.get("state") != state:
        log_event(db, cid, "state_change", {"from": prev.get("state"), "to": state, **payload}, worker_id)


# -------------------------------------------------------------- experiments

def experiments(db: Database, cid: str) -> list[dict]:
    return list(db.experiments.find({"campaign_id": cid}).sort("created_at", ASCENDING))


def budget_used(db: Database, cid: str) -> int:
    """Every distinct experiment ever accepted counts, including failures. Reuse is free."""
    return db.experiments.count_documents({"campaign_id": cid})


def eligible_done(db: Database, campaign: dict) -> list[dict]:
    """Done results under the CURRENT protocol that satisfy the CURRENT constraints."""
    done = db.experiments.find({"campaign_id": campaign["_id"], "protocol_id": campaign["protocol_id"],
                                "status": "done"})
    return [e for e in done if is_eligible(e["config"], campaign["constraints"])]


def incumbent(db: Database, campaign: dict) -> dict | None:
    eligible = eligible_done(db, campaign)
    return max(eligible, key=lambda e: (e["result"]["val_balanced_accuracy"], e["result"]["val_f1"]),
               default=None)


def enqueue(db: Database, campaign: dict, cfg: dict, proposed_by: dict,
            worker_id: str | None = None) -> tuple[str, str]:
    """Insert a queued experiment. Returns (experiment_id, outcome).

    outcome: "queued" (new), "reused" (identical config already done under this
    protocol, so it is not recomputed), or the existing status if still pending.
    The unique _id makes this safe to replay after a crash.
    """
    cfg = normalize_config(cfg)
    cid = campaign["_id"]
    key = experiment_key(campaign["protocol_id"], cfg)
    eid = experiment_doc_id(cid, key)
    try:
        db.experiments.insert_one({
            "_id": eid, "key": key, "campaign_id": cid, "protocol_id": campaign["protocol_id"],
            "config": cfg, "label": config_label(cfg), "n_channels": n_channels(cfg),
            "status": "queued", "attempt": 0, "lease": None, "proposed_by": proposed_by,
            "goal_version_at_proposal": campaign["goal_version"],
            "result": None, "error": None, "created_at": now_iso(), "started_at": None, "finished_at": None,
        })
    except DuplicateKeyError:
        existing = db.experiments.find_one({"_id": eid})
        if existing["status"] == "done":
            log_event(db, cid, "job_reused", {"experiment_id": eid, "label": existing["label"],
                                              "val_balanced_accuracy": existing["result"]["val_balanced_accuracy"]},
                      worker_id)
            return eid, "reused"
        return eid, existing["status"]
    log_event(db, cid, "job_queued", {"experiment_id": eid, "label": config_label(cfg)}, worker_id)
    return eid, "queued"


def claim_next(db: Database, cid: str, worker_id: str) -> dict | None:
    """Atomically move the oldest queued experiment to running under a fresh lease token."""
    token = secrets.token_hex(8)
    doc = db.experiments.find_one_and_update(
        {"campaign_id": cid, "status": "queued"},
        {"$set": {"status": "running", "started_at": now_iso(),
                  "lease": {"owner": worker_id, "token": token, "expires_at": _iso_in(LEASE_SECONDS)}},
         "$inc": {"attempt": 1}},
        sort=[("created_at", ASCENDING)],
        return_document=ReturnDocument.AFTER,
    )
    if doc:
        log_event(db, cid, "job_claimed", {"experiment_id": doc["_id"], "attempt": doc["attempt"],
                                           "lease_token": token}, worker_id)
    return doc


def running_jobs(db: Database, cid: str) -> list[dict]:
    return list(db.experiments.find({"campaign_id": cid, "status": "running"}))


def reclaim_expired(db: Database, cid: str, worker_id: str) -> list[str]:
    """Running jobs whose lease expired (their worker died) go back to queued.

    The next claim bumps `attempt` and issues a new token, so a late commit from
    the dead attempt is rejected by commit_result's fence.
    """
    now = now_iso()
    reclaimed = []
    for doc in db.experiments.find({"campaign_id": cid, "status": "running", "lease.expires_at": {"$lt": now}}):
        res = db.experiments.update_one(
            {"_id": doc["_id"], "status": "running", "lease.token": doc["lease"]["token"]},
            {"$set": {"status": "queued", "lease": None}},
        )
        if res.modified_count:
            reclaimed.append(doc["_id"])
            log_event(db, cid, "lease_expired", {"experiment_id": doc["_id"], "attempt": doc["attempt"],
                                                 "dead_owner": doc["lease"]["owner"]}, worker_id)
    return reclaimed


def commit_result(db: Database, eid: str, token: str, result: dict, worker_id: str | None = None) -> bool:
    """Fenced commit: only the attempt holding the current lease token can write the result."""
    res = db.experiments.update_one(
        {"_id": eid, "status": "running", "lease.token": token},
        {"$set": {"status": "done", "result": result, "finished_at": now_iso(), "lease": None}},
    )
    cid = eid.split(":", 1)[0]
    if res.modified_count:
        log_event(db, cid, "job_committed", {"experiment_id": eid,
                                             "val_balanced_accuracy": result["val_balanced_accuracy"],
                                             "fit_seconds": result["fit_seconds"]}, worker_id)
        return True
    log_event(db, cid, "stale_commit_rejected", {"experiment_id": eid, "lease_token": token}, worker_id)
    return False


def fail_job(db: Database, eid: str, token: str, error: str, worker_id: str | None = None) -> bool:
    res = db.experiments.update_one(
        {"_id": eid, "status": "running", "lease.token": token},
        {"$set": {"status": "failed", "error": error[:500], "finished_at": now_iso(), "lease": None}},
    )
    if res.modified_count:
        log_event(db, eid.split(":", 1)[0], "job_failed", {"experiment_id": eid, "error": error[:500]}, worker_id)
    return bool(res.modified_count)


def begin_finalize(db: Database, cid: str, worker_id: str) -> bool:
    """Take the one-time right to score the sealed test set. False if anyone already took it."""
    res = db.campaigns.update_one({"_id": cid, "final": None, "finalizing": {"$exists": False}},
                                  {"$set": {"finalizing": {"worker_id": worker_id, "at": now_iso()}}})
    return bool(res.modified_count)


def finalize(db: Database, campaign: dict, exp: dict, test_result: dict, worker_id: str | None = None) -> bool:
    """Record the one sealed-test score. The `final: None` filter makes a second scoring impossible."""
    final = {"experiment_id": exp["_id"], "config": exp["config"], "label": exp["label"],
             "val_balanced_accuracy": exp["result"]["val_balanced_accuracy"],
             "goal_version": campaign["goal_version"], "constraints": campaign["constraints"],
             **test_result, "scored_at": now_iso()}
    res = db.campaigns.update_one({"_id": campaign["_id"], "final": None},
                                  {"$set": {"final": final, "state": "DONE", "updated_at": now_iso()}})
    if res.modified_count:
        log_event(db, campaign["_id"], "finalized", final, worker_id)
    return bool(res.modified_count)
