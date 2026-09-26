"""Bounded context reconstruction. OWNER: Andrew.

Every planner decision is built from Atlas, never from chat history:

evidence       latest goal + constraints (exact read), incumbent eligible result
               (exact read), pending jobs, a small recent window, and a few
               memories ranked by Vector Search after filtering by
               campaign/protocol/status.
recent_window  the same goal block and hard guards, plus the last N experiments
               only. This is the baseline arm for eval/run_ablation.py.
"""
from __future__ import annotations

import json
import secrets

from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database

from harness import store
from harness.contracts import is_eligible, surface_summary
from harness.db import log_event, now_iso

RECENT_EVIDENCE = 3
RECENT_BASELINE = 6
RETRIEVE_K = 4
LEADERS = 3
LAGGARDS = 2


def estimate_tokens(obj) -> int:
    """~4 characters per token. An estimate, and labeled as one everywhere it's shown."""
    return len(json.dumps(obj, default=str)) // 4


def _search(db: Database, campaign: dict, query: str, k: int) -> list[dict]:
    """David's memory.search_memories when present; exact filtered read otherwise."""
    try:
        from harness.memory import search_memories
    except ImportError:
        search_memories = None
    if search_memories is not None:
        return search_memories(db, campaign_id=campaign["_id"], protocol_id=campaign["protocol_id"],
                               query=query, k=k)
    docs = db.memories.find({"campaign_id": campaign["_id"], "protocol_id": campaign["protocol_id"],
                             "status": "active"}, {"embedding": 0}).sort("created_at", DESCENDING).limit(k)
    return [{"memory_id": d["_id"], "kind": d["kind"], "text": d["text"], "source_ids": d["source_ids"],
             "score": None, "verified": d["verified"], "retrieval": "fallback"} for d in docs]


def _exp_row(e: dict, constraints: dict) -> dict:
    return {
        "experiment_id": e["_id"],
        "label": e["label"],
        "status": e["status"],
        "val_balanced_accuracy": (e.get("result") or {}).get("val_balanced_accuracy"),
        "eligible": is_eligible(e["config"], constraints),
    }


def build_packet(db: Database, campaign_id: str, strategy: str = "evidence", budget_tokens: int = 4000,
                 worker_id: str | None = None) -> dict:
    campaign = store.get_campaign(db, campaign_id)
    constraints = campaign["constraints"]
    exps = store.experiments(db, campaign_id)
    used = len(exps)
    max_exp = campaign["budget"]["max_experiments"]
    finished = [e for e in exps if e["status"] in ("done", "failed")]

    packet: dict = {
        "packet_id": "pk_" + secrets.token_hex(6),
        "campaign_id": campaign_id,
        "protocol_id": campaign["protocol_id"],
        "strategy": strategy,
        "goal": {
            "objective": campaign["objective"],
            "goal_version": campaign["goal_version"],
            "constraints": constraints,
            "budget": {"max_experiments": max_exp, "used": used, "remaining": max(0, max_exp - used)},
        },
        "incumbent": None,
        "pending": [],
        "recent": [],
        "retrieved": [],
        "tried_keys": [e["key"] for e in exps],
        "tried": [e["label"] for e in exps],
        "leaders": [],
        "laggards": [],
        "surface": surface_summary(),
        "token_estimate": 0,
        "budget_tokens": budget_tokens,
    }

    if strategy == "evidence":
        inc = store.incumbent(db, campaign)
        if inc:
            packet["incumbent"] = {"experiment_id": inc["_id"], "label": inc["label"], "config": inc["config"],
                                   "val_balanced_accuracy": inc["result"]["val_balanced_accuracy"]}
        packet["pending"] = [{"experiment_id": e["_id"], "label": e["label"], "status": e["status"]}
                             for e in exps if e["status"] in ("queued", "running")]
        packet["recent"] = [_exp_row(e, constraints) for e in finished[-RECENT_EVIDENCE:]]
        # Numerical evidence by exact read, never by semantic similarity.
        done = sorted((e for e in finished if e["status"] == "done" and e["protocol_id"] == campaign["protocol_id"]),
                      key=lambda e: e["result"]["val_balanced_accuracy"], reverse=True)
        packet["leaders"] = [_exp_row(e, constraints) for e in done if is_eligible(e["config"], constraints)][:LEADERS]
        packet["laggards"] = ([_exp_row(e, constraints) for e in finished if e["status"] == "failed"]
                              + [_exp_row(e, constraints) for e in done[::-1]])[:LAGGARDS]
        query = (f"Choosing the next EEG motor imagery experiment with at most {constraints['max_channels']} "
                 f"channels. Useful: results and failures for eligible channel sets"
                 + (f"; current best is {inc['label']}" if inc else "") + ".")
        packet["retrieved"] = _search(db, campaign, query, RETRIEVE_K)
    elif strategy == "recent_window":
        packet["recent"] = [_exp_row(e, constraints) for e in finished[-RECENT_BASELINE:]]
    else:
        raise ValueError(f"unknown strategy {strategy!r}")

    # Enforce the finite budget: drop retrieved notes, then the oldest recent rows.
    packet["token_estimate"] = estimate_tokens(packet)
    while packet["token_estimate"] > budget_tokens and (packet["retrieved"] or packet["recent"]):
        if packet["retrieved"]:
            packet["retrieved"].pop()        # lowest-ranked note first
        else:
            packet["recent"].pop(0)          # then the oldest recent row
        packet["token_estimate"] = estimate_tokens(packet)

    # Stored flat so the API/UI read the same fields the planner saw.
    db.packets.insert_one({"_id": packet["packet_id"], "ts": now_iso(), "context_epoch": campaign["context_epoch"],
                           "planner_result": None, **packet})
    log_event(db, campaign_id, "packet_built", {
        "packet_id": packet["packet_id"], "strategy": strategy, "goal_version": campaign["goal_version"],
        "token_estimate": packet["token_estimate"], "budget_tokens": budget_tokens,
        "retrieved_ids": [m["memory_id"] for m in packet["retrieved"]],
        "incumbent_id": (packet["incumbent"] or {}).get("experiment_id"),
    }, worker_id)
    return packet
