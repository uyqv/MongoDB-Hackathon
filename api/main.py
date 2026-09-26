"""FastAPI app: read endpoints, operator controls, and serves web/. OWNER: David.

Run: uvicorn api.main:app --reload --port 8000
See docs/CONTRACTS.md for the endpoint list.

Every value shown in the dashboard comes from Atlas through here. Eligibility
and the incumbent are computed on read with contracts.is_eligible. The
`embedding` field is never returned.
"""
from __future__ import annotations

import json
import os
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
    camp["llm_usage"] = llm_usage(cid)
    camp["running"] = [{"experiment_id": e["_id"], "label": e.get("label"), "attempt": e.get("attempt"),
                        "lease": e.get("lease")}
                       for e in db().experiments.find({"campaign_id": cid, "status": "running"},
                                                      {"label": 1, "attempt": 1, "lease": 1})]
    return clean(camp)


def llm_usage(cid: str) -> dict:
    """Running totals over llm_call events. Token and cost sums count provider-reported usage only."""
    out = {"calls": 0, "fallbacks": 0, "provider_calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
    for ev in db().events.find({"campaign_id": cid, "type": "llm_call"}, {"payload": 1}):
        p = ev.get("payload") or {}
        u = p.get("usage") or {}
        out["calls"] += 1
        out["fallbacks"] += bool(p.get("fallback_used"))
        if u.get("source") == "provider":
            out["provider_calls"] += 1
            out["input_tokens"] += u.get("input_tokens") or 0
            out["output_tokens"] += u.get("output_tokens") or 0
            out["cost_usd"] += u.get("cost_usd") or 0.0
    out["cost_usd"] = round(out["cost_usd"], 6)
    return out


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


EEG_SOURCE = "PhysioNet eegmmidb v1.0.0, S001 run 6"
EEG_CHANNELS = ("C3", "Cz", "C4")


def build_eeg_preview() -> dict:
    """Display only: never feeds any metric. Real S001 run 6 (imagined both fists vs both feet)."""
    import mne
    import numpy as np
    from mne.datasets import eegbci

    mne.set_log_level("ERROR")
    data_dir = os.environ.get("EEG_DATA_DIR", "data/eeg")
    path = eegbci.load_data(1, [6], path=data_dir, update_path=False)[0]
    raw = mne.io.read_raw_edf(path, preload=True)
    eegbci.standardize(raw)
    sf = raw.info["sfreq"]
    events, event_id = mne.events_from_annotations(raw)
    cues = [(int(s), code) for s, _, code in events if code in (event_id["T1"], event_id["T2"])]
    first = cues[0][0]
    picks = [raw.ch_names.index(c) for c in EEG_CHANNELS]
    x = raw.get_data(picks=picks) * 1e6  # volts to microvolts

    filt = mne.filter.filter_data(x, sf, 1.0, 40.0, phase="zero")
    step = 2  # 160 Hz -> 80 Hz for display, after the 40 Hz low-pass
    seg = filt[:, first:first + int(6 * sf):step]
    t = (np.arange(seg.shape[1]) * step / sf).round(4)

    lo, hi = int(1 * sf), int(3 * sf)
    by_class: dict[str, list] = {"T1": [], "T2": []}
    code_name = {event_id["T1"]: "T1", event_id["T2"]: "T2"}
    for s0, code in cues:
        if s0 + hi <= x.shape[1]:
            by_class[code_name[code]].append(x[:, s0 + lo:s0 + hi])
    psd = {}
    freqs = None
    for cls, epochs in by_class.items():
        arr = np.stack(epochs)  # (n_epochs, n_channels, n_times)
        p, freqs = mne.time_frequency.psd_array_welch(arr, sf, fmin=4.0, fmax=40.0, n_fft=int(2 * sf))
        psd[cls] = {ch: (10 * np.log10(p[:, i, :].mean(axis=0))).round(3).tolist()
                    for i, ch in enumerate(EEG_CHANNELS)}
    return {
        "source": EEG_SOURCE,
        "labels": {"T1": "imagined both fists", "T2": "imagined both feet"},
        "trace": {"t": t.tolist(), "sfreq_display": sf / step, "units": "µV", "filter": "1-40 Hz zero-phase FIR",
                  "cue": "first task cue", "cue_label": code_name[cues[0][1]],
                  "channels": {ch: seg[i].round(3).tolist() for i, ch in enumerate(EEG_CHANNELS)}},
        "psd": {"freqs": np.asarray(freqs).round(3).tolist(), "units": "dB (µV²/Hz)",
                "window": "1-3 s after cue, Welch", "n_epochs": {k: len(v) for k, v in by_class.items()},
                "by_class": psd},
        "display_only": True,
    }


@app.get("/api/eeg/preview")
def eeg_preview():
    cache = Path(os.environ.get("EEG_PREVIEW_CACHE", "data/eeg_preview.json"))
    if cache.exists():
        return json.loads(cache.read_text())
    try:
        out = build_eeg_preview()
    except Exception as e:  # download or parse failure: the panel says so, nothing else breaks
        return JSONResponse({"error": f"EEG preview unavailable: {type(e).__name__}: {e}"}, status_code=503)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out))
    return out


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


ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str):
    p = ROOT / rel
    return json.loads(p.read_text()) if p.exists() else None


@app.get("/api/proof")
def proof():
    """Measured results for the Results view, read from the eval output files (never typed in by hand)."""
    checks = _read("eval/checks.json") or []
    latest = {}
    for r in checks:
        latest[r["check"]] = r
    passed = sum(sum(r["checks"].values()) for r in latest.values())
    total = sum(len(r["checks"]) for r in latest.values())
    stress = _read("eval/stress.json") or {}
    levels = [{"memories": x["memories_total"], "p50_ms": x["search_ms_p50"], "p95_ms": x["search_ms_p95"]}
              for x in stress.get("results", [])]
    current = _read("eval/stress_current_packet.json") or {}
    ab = (_read("eval/results.json") or {}).get("summary", {})
    rec = (latest.get("recovery") or {}).get("checks", {})
    lost = 0 if rec.get("every_experiment_committed_once") and rec.get("done_experiments_not_recomputed") else None
    return {
        "results_lost": lost,
        "checks": {"passed": passed, "total": total,
                   "by_check": {k: {"passed": sum(v["checks"].values()), "total": len(v["checks"]),
                                    "campaign_id": v["campaign_id"]} for k, v in latest.items()}},
        "memory": {"notes": current.get("memories"), "packet_tokens": current.get("packet_token_estimate"),
                   "budget_tokens": current.get("budget_tokens"), "levels": levels},
        "ablation": {arm: {"cited": v.get("cited_expected_evidence"), "decisions": v.get("decisions"),
                           "tokens": v.get("mean_input_tokens_provider")} for arm, v in ab.items()},
    }


SOURCE_FILES = {"harness/store.py", "harness/context.py", "harness/worker.py", "harness/eeg.py", "harness/planner.py",
                "harness/memory.py", "harness/jev.py", "harness/contracts.py"}


@app.get("/api/source")
def source(file: str, fn: str):
    """One function's source, straight from the repo, for the Code view."""
    import ast
    if file not in SOURCE_FILES:
        raise HTTPException(404, "not an allowed file")
    text = (ROOT / file).read_text()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == fn:
            lines = text.splitlines()[node.lineno - 1: node.end_lineno]
            return {"file": file, "fn": fn, "start": node.lineno, "end": node.end_lineno, "code": "\n".join(lines)}
    raise HTTPException(404, "function not found")
