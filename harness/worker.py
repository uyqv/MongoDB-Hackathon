"""The single long-lived worker. OWNER: Andrew.

CLI (the API spawns this exact command, so keep it stable):
    python -m harness.worker --campaign <campaign_id>
    python -m harness.worker --new --mode {smoke,demo} --max-channels 64 --budget 10

State loop: REHYDRATE -> PLAN -> VALIDATE -> QUEUE -> EXECUTE -> COMMIT -> REHYDRATE,
plus WAITING / FAILED / DONE. Holds no conversation history between steps: every
decision starts from a fresh read of Atlas.

--crash-after-claim N is fault injection for the recovery demo. After the Nth
claim, the worker logs a `fault_injection` event and SIGKILLs itself mid-job.
"""
from __future__ import annotations

import argparse
import os
import random
import signal
import socket
import time
import traceback

from pymongo.database import Database

from harness import context, eeg, store
from harness.contracts import (
    all_configs, experiment_key, is_eligible, normalize_config, protocol_id, render_failure_text,
    render_result_text,
)
from harness.db import get_db, log_event, now_iso

OBJECTIVE = ("Maximize validation balanced accuracy for imagined both-fists vs both-feet motor imagery EEG "
             "(PhysioNet eegmmidb runs 6/10/14), within the experiment budget and the current channel limit.")
WAIT_POLL_SECONDS = 1.0


# ------------------------------------------------------------------ helpers

def add_memory(db: Database, **kw) -> str:
    """David's memory.add_memory when present (adds an embedding); plain insert otherwise."""
    try:
        from harness.memory import add_memory as _add
    except ImportError:
        _add = None
    if _add is not None:
        return _add(db, **kw)
    mid = "m_" + os.urandom(6).hex()
    db.memories.insert_one({"_id": mid, "status": "active", "synthetic": kw.pop("synthetic", False),
                            "embedding": None, "created_at": now_iso(), **kw})
    return mid


def fallback_plan(packet: dict, reason: str) -> dict:
    """Deterministic stand-in: a seeded shuffle of eligible, untried configs."""
    tried = set(packet["tried_keys"])
    constraints = packet["goal"]["constraints"]
    order = all_configs()
    random.Random(packet["campaign_id"]).shuffle(order)
    for cfg in order:
        if is_eligible(cfg, constraints) and experiment_key(packet["protocol_id"], cfg) not in tried:
            return {"action": "propose", "config": cfg, "rationale": f"Fallback pick ({reason}).",
                    "evidence_ids": [], "model": "none", "request_id": None,
                    "usage": {"input_tokens": None, "output_tokens": None, "cost_usd": None, "source": "estimate"},
                    "fallback_used": True, "fallback_reason": reason}
    return {"action": "stop", "config": None, "rationale": "No eligible untried configs remain.",
            "evidence_ids": [], "model": "none", "request_id": None,
            "usage": {"input_tokens": None, "output_tokens": None, "cost_usd": None, "source": "estimate"},
            "fallback_used": True, "fallback_reason": reason}


def call_planner(packet: dict) -> dict:
    try:
        from harness.planner import plan
        return plan(packet)
    except NotImplementedError:
        return fallback_plan(packet, "planner not implemented yet")
    except Exception as exc:  # the planner must never take the worker down
        return fallback_plan(packet, f"planner error: {type(exc).__name__}: {exc}"[:300])


def guard(packet: dict, result: dict) -> str | None:
    """Hard guards in code, applied to every proposal whatever the planner claims."""
    try:
        cfg = normalize_config(result["config"])
    except (ValueError, TypeError) as exc:
        return f"outside allowed surface: {exc}"
    if not is_eligible(cfg, packet["goal"]["constraints"]):
        return f"ineligible under max_channels={packet['goal']['constraints']['max_channels']}"
    if experiment_key(packet["protocol_id"], cfg) in set(packet["tried_keys"]):
        return "already tried under this protocol"
    return None


# ------------------------------------------------------------------- worker

class Worker:
    def __init__(self, db: Database, campaign_id: str, *, crash_after_claim: int | None = None,
                 strategy: str = "evidence"):
        self.db = db
        self.cid = campaign_id
        self.worker_id = f"w_{socket.gethostname().split('.')[0][:10]}_{os.getpid()}"
        self.crash_after_claim = crash_after_claim
        self.strategy = strategy
        self.claims = 0
        self.protocol: dict | None = None
        self.data: eeg.EEGData | None = None
        self.epoch_seen: int | None = None

    def log(self, type_: str, **payload) -> None:
        log_event(self.db, self.cid, type_, payload, self.worker_id)

    def state(self, s: str, **payload) -> None:
        store.set_state(self.db, self.cid, s, self.worker_id, **payload)

    # REHYDRATE --------------------------------------------------------------
    def rehydrate(self) -> dict:
        self.state("REHYDRATE")
        camp = store.get_campaign(self.db, self.cid)
        if self.epoch_seen is not None and camp["context_epoch"] != self.epoch_seen:
            self.log("state_change", note="context reset observed; next decision rebuilt from Atlas only",
                     context_epoch=camp["context_epoch"])
        self.epoch_seen = camp["context_epoch"]
        store.reclaim_expired(self.db, self.cid, self.worker_id)
        self.repair_projections(camp)
        return camp

    def repair_projections(self, camp: dict) -> None:
        """A crash between result commit and memory write leaves a done experiment with no memory. Fix it."""
        for e in self.db.experiments.find({"campaign_id": self.cid, "status": {"$in": ["done", "failed"]}}):
            if self.db.memories.count_documents({"campaign_id": self.cid, "source_ids": e["_id"]}, limit=1):
                continue
            self.write_result_memory(camp, e)

    def write_result_memory(self, camp: dict, e: dict) -> None:
        done = e["status"] == "done"
        mid = add_memory(self.db, campaign_id=self.cid, protocol_id=camp["protocol_id"],
                         kind="verified_result" if done else "failure",
                         text=render_result_text(e) if done else render_failure_text(e),
                         source_ids=[e["_id"]], verified=done)
        self.log("memory_added", memory_id=mid, experiment_id=e["_id"], kind="verified_result" if done else "failure")

    # boot -------------------------------------------------------------------
    def boot(self) -> dict:
        camp = store.get_campaign(self.db, self.cid)
        counts = {s: self.db.experiments.count_documents({"campaign_id": self.cid, "status": s})
                  for s in ("done", "failed", "running", "queued")}
        self.log("worker_start", resumed=any(counts.values()), pid=os.getpid(), counts=counts,
                 note=(f"resuming: {counts['done']} done experiments will be reused, not recomputed"
                       if counts["done"] else "fresh start"))
        self.protocol, self.data = eeg.load_protocol(camp["protocol"]["mode"])
        if protocol_id(self.protocol) != camp["protocol_id"]:
            self.state("FAILED", reason="data/split/evaluator changed; refusing to reuse old measurements")
            raise SystemExit("protocol mismatch")
        return camp

    # main loop --------------------------------------------------------------
    def run(self, max_steps: int | None = None) -> None:
        self.boot()
        steps = 0
        while max_steps is None or steps < max_steps:
            camp = self.rehydrate()
            if camp.get("final"):
                self.state("DONE")
                break

            running = store.running_jobs(self.db, self.cid)
            if running:  # a dead worker's lease: poll until it expires, no LLM calls meanwhile
                self.state("WAITING", experiment_id=running[0]["_id"],
                           lease_expires_at=running[0]["lease"]["expires_at"])
                while store.running_jobs(self.db, self.cid):
                    time.sleep(WAIT_POLL_SECONDS)
                    store.reclaim_expired(self.db, self.cid, self.worker_id)
                continue

            if not self.db.experiments.find_one({"campaign_id": self.cid, "status": "queued"}):
                if store.budget_used(self.db, self.cid) >= camp["budget"]["max_experiments"]:
                    self.finish(camp, "budget spent")
                    break
                if not self.plan_and_queue(camp):
                    self.finish(camp, "planner stopped")
                    break

            self.execute(camp)
            steps += 1
        self.log("worker_stop", steps=steps)

    def plan_and_queue(self, camp: dict) -> bool:
        """PLAN -> VALIDATE -> QUEUE. Returns False when the campaign should stop."""
        for _ in range(3):
            self.state("PLAN")
            packet = context.build_packet(self.db, self.cid, self.strategy, worker_id=self.worker_id)
            result = call_planner(packet)
            self.log("llm_call", packet_id=packet["packet_id"], model=result["model"],
                     request_id=result["request_id"], usage=result["usage"], action=result["action"],
                     fallback_used=result["fallback_used"], fallback_reason=result["fallback_reason"])

            self.state("VALIDATE")
            if result["action"] == "propose":
                problem = guard(packet, result)
                if problem:
                    self.log("proposal_rejected", packet_id=packet["packet_id"], reason=problem,
                             config=result.get("config"))
                    result = fallback_plan(packet, f"guard rejected planner proposal: {problem}")
            self.db.packets.update_one({"_id": packet["packet_id"]}, {"$set": {"planner_result": result}})
            if result["action"] == "stop":
                return False

            self.state("QUEUE")
            cfg = normalize_config(result["config"])
            self.log("proposal", packet_id=packet["packet_id"], config=cfg, rationale=result["rationale"],
                     evidence_ids=result["evidence_ids"], model=result["model"])
            _, outcome = store.enqueue(self.db, camp, cfg, {
                "model": result["model"], "request_id": result["request_id"], "rationale": result["rationale"],
                "evidence_ids": result["evidence_ids"], "fallback_used": result["fallback_used"],
                "packet_id": packet["packet_id"],
            }, self.worker_id)
            if outcome != "reused":
                return True
            camp = store.get_campaign(self.db, self.cid)  # reused: no budget spent, plan again
        return False

    def execute(self, camp: dict) -> None:
        """EXECUTE -> COMMIT."""
        self.state("EXECUTE")
        job = store.claim_next(self.db, self.cid, self.worker_id)
        if job is None:
            return
        self.claims += 1
        if self.crash_after_claim and self.claims >= self.crash_after_claim:
            self.log("fault_injection", experiment_id=job["_id"], attempt=job["attempt"],
                     note="worker SIGKILLs itself mid-job to prove recovery")
            os.kill(os.getpid(), signal.SIGKILL)
        token = job["lease"]["token"]
        try:
            result = eeg.run_experiment(job["config"], self.protocol, self.data)
        except Exception as exc:
            self.state("COMMIT")
            if store.fail_job(self.db, job["_id"], token, f"{type(exc).__name__}: {exc}", self.worker_id):
                self.write_result_memory(camp, self.db.experiments.find_one({"_id": job["_id"]}))
            traceback.print_exc()
            return
        self.state("COMMIT")
        if store.commit_result(self.db, job["_id"], token, result, self.worker_id):
            self.write_result_memory(camp, self.db.experiments.find_one({"_id": job["_id"]}))

    def finish(self, camp: dict, why: str) -> None:
        """Freeze the incumbent under the CURRENT goal and score the sealed test set once."""
        camp = store.get_campaign(self.db, self.cid)
        best = store.incumbent(self.db, camp)
        if best is None:
            self.state("DONE", reason=f"{why}; no eligible result to finalize")
            return
        if not store.begin_finalize(self.db, self.cid, self.worker_id):
            self.state("DONE", reason="already finalized")
            return
        test = eeg.score_test_once(best["config"], self.protocol, self.data)
        store.finalize(self.db, camp, best, test, self.worker_id)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign")
    ap.add_argument("--new", action="store_true")
    ap.add_argument("--mode", default="demo", choices=list(eeg.MODES))
    ap.add_argument("--max-channels", type=int, default=64)
    ap.add_argument("--budget", type=int, default=10)
    ap.add_argument("--max-steps", type=int)
    ap.add_argument("--crash-after-claim", type=int)
    ap.add_argument("--strategy", default="evidence", choices=["evidence", "recent_window"])
    args = ap.parse_args()
    db = get_db()
    store.ensure_indexes(db)
    if args.new:
        protocol, _ = eeg.load_protocol(args.mode)
        cid = store.create_campaign(db, protocol=protocol, objective=OBJECTIVE, max_channels=args.max_channels,
                                    max_experiments=args.budget)
        print(cid, flush=True)
    elif args.campaign:
        cid = args.campaign
    else:
        ap.error("pass --campaign <id> or --new")
    Worker(db, cid, crash_after_claim=args.crash_after_claim, strategy=args.strategy).run(args.max_steps)


if __name__ == "__main__":
    main()
