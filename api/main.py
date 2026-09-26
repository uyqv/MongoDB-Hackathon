"""FastAPI app: read endpoints, operator controls, and serves web/. OWNER: David.

Run: uvicorn api.main:app --reload --port 8000
See docs/CONTRACTS.md for the endpoint list.

Every value shown in the dashboard comes from Atlas through here. Eligibility
and the incumbent are computed on read with contracts.is_eligible. The
`embedding` field is never returned.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from bson import ObjectId
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from harness import contracts as C
from harness import control
from harness.db import get_db

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="Second Shift")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


def clean(obj: Any) -> Any:
    """JSON-safe copy: ObjectId and datetime to strings, `embedding` dropped everywhere."""
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items() if k != "embedding"}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def db():
    return get_db()


def _campaign_or_404(cid: str) -> dict:
    camp = db().campaigns.find_one({"_id": cid})
    if not camp:
        raise HTTPException(404, f"campaign {cid} not found")
    return camp


def _eligible(cfg: dict, constraints: dict) -> bool | None:
    try:
        return C.is_eligible(cfg, constraints)
    except (ValueError, KeyError, TypeError):
        return None


def incumbent(camp: dict, experiments: list[dict]) -> dict | None:
    """Eligible `done` experiment with the best val balanced accuracy under the current protocol."""
    best = None
    for e in experiments:
        if e.get("status") != "done" or e.get("protocol_id") != camp.get("protocol_id"):
            continue
        acc = (e.get("result") or {}).get("val_balanced_accuracy")
        if acc is None or not _eligible(e["config"], camp["constraints"]):
            continue
        if best is None or acc > best["result"]["val_balanced_accuracy"]:
            best = e
    if best is None:
        return None
    return {"experiment_id": best["_id"], "label": best.get("label") or C.config_label(best["config"]),
            "config": best["config"], "val_balanced_accuracy": best["result"]["val_balanced_accuracy"],
            "n_channels": best.get("n_channels")}


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health():
    d = db()
    d.command("ping")
    return {"ok": True, "db": d.name}


@app.get("/api/campaigns")
def campaigns():
    proj = {"objective": 1, "state": 1, "goal_version": 1, "constraints": 1, "created_at": 1, "fake": 1}
    return clean(list(db().campaigns.find({}, proj).sort("created_at", -1)))


@app.get("/api/campaigns/{cid}")
def campaign(cid: str):
    camp = _campaign_or_404(cid)
    exps = list(db().experiments.find({"campaign_id": cid}, {"config": 1, "status": 1, "result": 1,
                                                             "protocol_id": 1, "label": 1, "n_channels": 1}))
    used = len(exps)
    max_exp = (camp.get("budget") or {}).get("max_experiments")
    camp["used"] = used
    camp["remaining"] = None if max_exp is None else max(0, max_exp - used)
    camp["incumbent"] = incumbent(camp, exps)
    return clean(camp)


@app.get("/api/campaigns/{cid}/experiments")
def experiments(cid: str):
    camp = _campaign_or_404(cid)
    d = db()
    reused = {e["payload"].get("experiment_id")
              for e in d.events.find({"campaign_id": cid, "type": "job_reused"}, {"payload": 1})}
    out = []
    for e in d.experiments.find({"campaign_id": cid}).sort("created_at", 1):
        e["eligible"] = _eligible(e.get("config", {}), camp["constraints"])
        e["reused"] = e["_id"] in reused
        out.append(e)
    return clean(out)


@app.get("/api/campaigns/{cid}/events")
def events(cid: str, after: str | None = None, limit: int = Query(200, ge=1, le=2000)):
    """Ordered by ts. With `after`: the next `limit` events after it. Without: the latest `limit`."""
    col = db().events
    if after:
        rows = list(col.find({"campaign_id": cid, "ts": {"$gt": after}}).sort("ts", 1).limit(limit))
    else:
        rows = list(col.find({"campaign_id": cid}).sort("ts", -1).limit(limit))[::-1]
    return clean(rows)


@app.get("/api/campaigns/{cid}/packets/latest")
def latest_packet(cid: str, strategy: str = "evidence"):
    doc = db().packets.find_one({"campaign_id": cid, "strategy": strategy}, sort=[("ts", -1)])
    if not doc:
        raise HTTPException(404, "no packet yet")
    return clean(doc)


@app.get("/api/campaigns/{cid}/memories")
def memories(cid: str, kind: str | None = None, include_synthetic: bool = False):
    flt: dict = {"campaign_id": cid}
    if kind:
        flt["kind"] = kind
    if not include_synthetic:
        flt["synthetic"] = {"$ne": True}
    return clean(list(db().memories.find(flt, {"embedding": 0}).sort("created_at", -1)))


class StartBody(BaseModel):
    campaign_id: str


class ConstraintBody(BaseModel):
    max_channels: int
    reason: str = ""


@app.get("/api/eeg/preview")
def eeg_preview():
    return JSONResponse({"error": "EEG preview not implemented yet"}, status_code=501)


@app.get("/api/worker/status")
def worker_status():
    return control.worker_status()


@app.post("/api/worker/start")
def worker_start(body: StartBody):
    _campaign_or_404(body.campaign_id)
    try:
        return {"pid": control.start_worker(body.campaign_id)}
    except RuntimeError as e:
        raise HTTPException(409, str(e))


@app.post("/api/worker/kill")
def worker_kill():
    return control.kill_worker()


@app.post("/api/campaigns/{cid}/constraint")
def constraint(cid: str, body: ConstraintBody):
    _campaign_or_404(cid)
    try:
        return clean(control.change_constraint(db(), cid, body.max_channels, body.reason))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/campaigns/{cid}/context-reset")
def context_reset(cid: str):
    _campaign_or_404(cid)
    return {"context_epoch": control.reset_context(db(), cid)}
