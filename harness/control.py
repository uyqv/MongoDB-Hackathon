"""Operator controls the API calls. OWNER: David.

change_constraint(db, campaign_id, max_channels, reason) -> dict   (updated campaign)
reset_context(db, campaign_id) -> int                              (new context_epoch)
start_worker(campaign_id) -> int                                   (pid)
kill_worker() -> dict                                              ({"killed", "pid"})
worker_status() -> dict                                            ({"running", "pid", "campaign_id"})
See docs/CONTRACTS.md §5 for the exact writes.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

from pymongo import ReturnDocument

from harness.db import get_db, log_event, now_iso

ALLOWED_MAX_CHANNELS = (9, 21, 64)
ROOT = Path(__file__).resolve().parent.parent
RUN_DIR = ROOT / "run"
# Keys the worker needs from .env. An EMPTY exported value would block load_dotenv() in the child.
ENV_KEYS = ("MONGODB_URI", "VOYAGE_API_KEY", "OPENROUTER_API_KEY", "PLANNER_MODEL", "VOYAGE_MODEL")

_children: dict[int, subprocess.Popen] = {}


def worker_cmd(campaign_id: str) -> list[str]:
    return [sys.executable, "-m", "harness.worker", "--campaign", campaign_id]


def _state_file() -> Path:
    return RUN_DIR / "worker.json"


def _read_state() -> dict | None:
    try:
        return json.loads(_state_file().read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _alive(pid: int | None) -> bool:
    if not pid:
        return False
    child = _children.get(pid)
    if child is not None:  # our own child: poll() reaps it, so a killed worker is not a live zombie
        return child.poll() is None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


# ------------------------------------------------------------------ goal

def change_constraint(db, campaign_id: str, max_channels: int, reason: str) -> dict:
    max_channels = int(max_channels)
    if max_channels not in ALLOWED_MAX_CHANNELS:
        raise ValueError(f"max_channels must be one of {ALLOWED_MAX_CHANNELS}")
    reason = (reason or "").strip() or "operator constraint change"
    for _ in range(5):
        before = db.campaigns.find_one({"_id": campaign_id})
        if before is None:
            raise KeyError(f"no campaign {campaign_id}")
        now = now_iso()
        new_version = before["goal_version"] + 1
        constraints = {**before.get("constraints", {}), "max_channels": max_channels}
        # Guarded on goal_version so the version bump and its history entry can never disagree.
        after = db.campaigns.find_one_and_update(
            {"_id": campaign_id, "goal_version": before["goal_version"]},
            {"$inc": {"goal_version": 1},
             "$set": {"constraints": constraints, "updated_at": now},
             "$push": {"goal_history": {"version": new_version, "constraints": constraints,
                                        "changed_at": now, "reason": reason}}},
            return_document=ReturnDocument.AFTER,
        )
        if after is not None:
            log_event(db, campaign_id, "goal_changed", {
                "from_version": before["goal_version"], "to_version": after["goal_version"],
                "old_constraints": before.get("constraints"), "new_constraints": constraints, "reason": reason,
            })
            return after
    raise RuntimeError("goal_version kept changing underneath; try again")


def reset_context(db, campaign_id: str) -> int:
    doc = db.campaigns.find_one_and_update({"_id": campaign_id},
                                           {"$inc": {"context_epoch": 1}, "$set": {"updated_at": now_iso()}},
                                           return_document=ReturnDocument.AFTER)
    if doc is None:
        raise KeyError(f"no campaign {campaign_id}")
    log_event(db, campaign_id, "context_reset", {"context_epoch": doc["context_epoch"]})
    return doc["context_epoch"]


# ---------------------------------------------------------------- worker

def worker_status() -> dict:
    st = _read_state() or {}
    pid = st.get("pid")
    running = _alive(pid)
    return {"running": running, "pid": pid if running else None, "campaign_id": st.get("campaign_id"),
            "started_at": st.get("started_at"), "last_pid": pid}


def start_worker(campaign_id: str) -> int:
    st = worker_status()
    if st["running"]:
        raise RuntimeError(f"worker already running (pid {st['pid']}, campaign {st['campaign_id']})")
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not (k in ENV_KEYS and not v)}
    env["DB_NAME"] = get_db().name  # the worker writes to the same DB this API reads
    log = open(RUN_DIR / "worker.log", "ab")
    proc = subprocess.Popen(worker_cmd(campaign_id), cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                            start_new_session=True)
    log.close()
    _children[proc.pid] = proc
    _state_file().write_text(json.dumps({"pid": proc.pid, "campaign_id": campaign_id, "started_at": now_iso()}))
    return proc.pid


def kill_worker() -> dict:
    """SIGKILL: a real crash, not a graceful stop. The worker writes nothing, so we log worker_killed."""
    st = _read_state() or {}
    pid = st.get("pid")
    if not _alive(pid):
        _state_file().unlink(missing_ok=True)
        return {"killed": False, "pid": pid}
    os.kill(pid, signal.SIGKILL)
    child = _children.pop(pid, None)
    if child is not None:
        child.wait(timeout=5)
    if st.get("campaign_id"):
        log_event(get_db(), st["campaign_id"], "worker_killed", {"pid": pid, "signal": "SIGKILL"})
    _state_file().unlink(missing_ok=True)
    return {"killed": True, "pid": pid}
