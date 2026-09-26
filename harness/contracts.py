"""Shared contracts for Second Shift.

OWNER: Andrew. Both branches import from here. Do not edit on the `david` branch;
if something here is wrong or missing, stop and tell Andrew.

Everything the two halves of the build agree on lives in this file: the allowed
experiment surface, config normalization, dedup hashing, eligibility, document
shapes, and the text rendered for verified results.
"""
from __future__ import annotations

import hashlib
import json
from itertools import product
from typing import Any, Literal, TypedDict

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

DB_NAME_DEFAULT = "second_shift"
COLLECTIONS = ("campaigns", "experiments", "memories", "events", "packets")
EVALUATOR_VERSION = "eeg-eval-1"
SEED = 42
LEASE_SECONDS = 15

CAMPAIGN_STATES = (
    "REHYDRATE", "PLAN", "VALIDATE", "QUEUE", "EXECUTE", "COMMIT",
    "WAITING", "PAUSED", "FAILED", "DONE",
)
EXPERIMENT_STATUSES = ("queued", "running", "done", "failed")
MEMORY_KINDS = ("verified_result", "failure", "hypothesis", "research_note", "synthetic_stress")
MEMORY_STATUSES = ("active", "obsolete")
EVENT_TYPES = (
    "campaign_created", "worker_start", "worker_stop", "worker_killed",
    "state_change", "packet_built", "llm_call", "proposal", "proposal_rejected",
    "job_queued", "job_reused", "job_claimed", "job_committed", "job_failed",
    "lease_expired", "stale_commit_rejected", "context_reset", "goal_changed",
    "memory_added", "finalized", "fault_injection",
)
PACKET_STRATEGIES = ("evidence", "recent_window")

# --------------------------------------------------------------------------
# Allowed experiment surface. The planner may only propose configs from here.
# 5 bands x 3 windows x 3 channel sets x (2 C values | 3 CSP sizes) = 225 configs.
# --------------------------------------------------------------------------

METHODS = ("bandpower_lr", "csp_lda")

BANDS: dict[str, tuple[float, float]] = {
    "mu_8_12": (8.0, 12.0),
    "lowbeta_13_20": (13.0, 20.0),
    "highbeta_20_30": (20.0, 30.0),
    "beta_13_30": (13.0, 30.0),
    "broad_8_30": (8.0, 30.0),
}

# Seconds after the task cue. Offline analysis windows, not a causal decoder.
WINDOWS: dict[str, tuple[float, float]] = {
    "w0.5_2.5": (0.5, 2.5),
    "w1.0_3.0": (1.0, 3.0),
    "w1.5_3.5": (1.5, 3.5),
}

# Channel names after mne.datasets.eegbci.standardize(raw).
CHANNEL_SETS: dict[str, list[str] | None] = {
    "central9": ["FC3", "FCz", "FC4", "C3", "Cz", "C4", "CP3", "CPz", "CP4"],
    "motor21": [
        "FC5", "FC3", "FC1", "FCz", "FC2", "FC4", "FC6",
        "C5", "C3", "C1", "Cz", "C2", "C4", "C6",
        "CP5", "CP3", "CP1", "CPz", "CP2", "CP4", "CP6",
    ],
    "all64": None,  # every EEG channel in the file
}
CHANNEL_COUNTS = {"central9": 9, "motor21": 21, "all64": 64}

LR_C = (0.1, 1.0)
CSP_COMPONENTS = (2, 4, 6)


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def normalize_config(cfg: dict) -> dict:
    """Return the EFFECTIVE config: validated, canonical, unused params dropped.

    Raises ValueError for anything outside the allowed surface. Unknown keys are
    dropped, so an irrelevant parameter can never create a "new" experiment.
    """
    if not isinstance(cfg, dict):
        raise ValueError("config must be a dict")
    method = cfg.get("method")
    band = cfg.get("band")
    window = cfg.get("window")
    channels = cfg.get("channels")
    if method not in METHODS:
        raise ValueError(f"unknown method {method!r}")
    if band not in BANDS:
        raise ValueError(f"unknown band {band!r}")
    if window not in WINDOWS:
        raise ValueError(f"unknown window {window!r}")
    if channels not in CHANNEL_SETS:
        raise ValueError(f"unknown channel set {channels!r}")
    out: dict[str, Any] = {"method": method, "band": band, "window": window, "channels": channels}
    if method == "bandpower_lr":
        try:
            c = float(cfg.get("C"))
        except (TypeError, ValueError):
            raise ValueError("bandpower_lr needs C") from None
        if c not in LR_C:
            raise ValueError(f"C must be one of {LR_C}")
        out["C"] = c
    else:
        try:
            n = int(cfg.get("n_components"))
        except (TypeError, ValueError):
            raise ValueError("csp_lda needs n_components") from None
        if n not in CSP_COMPONENTS:
            raise ValueError(f"n_components must be one of {CSP_COMPONENTS}")
        if n > CHANNEL_COUNTS[channels]:
            raise ValueError("n_components exceeds channel count")
        out["n_components"] = n
    return out


def all_configs() -> list[dict]:
    """Every allowed effective config, in a fixed deterministic order."""
    out = []
    for band, window, channels in product(BANDS, WINDOWS, CHANNEL_SETS):
        for c in LR_C:
            out.append(normalize_config({"method": "bandpower_lr", "band": band, "window": window,
                                         "channels": channels, "C": c}))
        for n in CSP_COMPONENTS:
            out.append(normalize_config({"method": "csp_lda", "band": band, "window": window,
                                         "channels": channels, "n_components": n}))
    return out


def n_channels(cfg: dict) -> int:
    return CHANNEL_COUNTS[normalize_config(cfg)["channels"]]


def is_eligible(cfg: dict, constraints: dict) -> bool:
    """Eligibility under the CURRENT goal. Recomputed on every read, never stored."""
    return n_channels(cfg) <= int(constraints["max_channels"])


def config_label(cfg: dict) -> str:
    c = normalize_config(cfg)
    extra = f"C={c['C']}" if c["method"] == "bandpower_lr" else f"n={c['n_components']}"
    return f"{c['method']} · {c['band']} · {c['window']} · {c['channels']} · {extra}"


def surface_summary() -> dict:
    """Compact description of the allowed surface, for the planner prompt and UI."""
    return {
        "methods": {"bandpower_lr": {"C": list(LR_C)}, "csp_lda": {"n_components": list(CSP_COMPONENTS)}},
        "bands": {k: list(v) for k, v in BANDS.items()},
        "windows": {k: list(v) for k, v in WINDOWS.items()},
        "channels": dict(CHANNEL_COUNTS),
        "total_configs": len(all_configs()),
    }


# --------------------------------------------------------------------------
# Identity and dedup
# --------------------------------------------------------------------------

def protocol_id(protocol: dict) -> str:
    """Protocol = dataset file hashes + exact split IDs + evaluator version + seed.

    Any change to data, split, or evaluator yields a new protocol id, so old
    measurements can never silently be reused under it.
    """
    return "p_" + _sha(canonical_json(protocol))[:12]


def experiment_key(protocol_id_: str, cfg: dict) -> str:
    """Hash of the normalized EFFECTIVE config + protocol id."""
    return "x_" + _sha(protocol_id_ + "|" + canonical_json(normalize_config(cfg)))[:16]


def experiment_doc_id(campaign_id: str, key: str) -> str:
    """experiments._id. Unique per campaign, which is what makes dedup atomic."""
    return f"{campaign_id}:{key}"


# --------------------------------------------------------------------------
# Rendering. Factual metric text is produced by code, never by a model.
# --------------------------------------------------------------------------

def render_result_text(exp: dict) -> str:
    r = exp["result"]
    return (
        f"Verified result {exp['_id']}: {config_label(exp['config'])} -> "
        f"val balanced accuracy {r['val_balanced_accuracy']:.3f}, macro F1 {r['val_f1']:.3f} "
        f"(n_train={r['n_train']}, n_val={r['n_val']}, {r['n_channels']} channels, "
        f"protocol {exp['protocol_id']})."
    )


def render_failure_text(exp: dict) -> str:
    return f"Failed experiment {exp['_id']}: {config_label(exp['config'])} -> error: {exp.get('error')}"


# --------------------------------------------------------------------------
# Document shapes (documentation for both branches; Mongo does not enforce them)
# --------------------------------------------------------------------------

class Constraints(TypedDict):
    max_channels: int


class GoalChange(TypedDict):
    version: int
    constraints: Constraints
    changed_at: str          # ISO-8601 UTC
    reason: str


class CampaignDoc(TypedDict):
    _id: str                 # "camp_<8 hex>"
    objective: str
    goal_version: int
    constraints: Constraints
    goal_history: list[GoalChange]
    protocol: dict           # full protocol dict (see protocol_id)
    protocol_id: str
    budget: dict             # {"max_experiments": int}
    state: str               # one of CAMPAIGN_STATES
    context_epoch: int       # bumped by every forced context reset
    final: dict | None       # {"experiment_id", "config", "test_balanced_accuracy", "test_f1", "scored_at"}
    created_at: str
    updated_at: str


class ExperimentResult(TypedDict):
    val_balanced_accuracy: float
    val_f1: float
    n_train: int
    n_val: int
    n_channels: int
    fit_seconds: float
    evaluator_version: str


class ExperimentDoc(TypedDict):
    _id: str                 # experiment_doc_id(campaign_id, key)
    key: str
    campaign_id: str
    protocol_id: str
    config: dict             # normalized effective config
    label: str               # config_label(config)
    n_channels: int
    status: str              # one of EXPERIMENT_STATUSES
    attempt: int
    lease: dict | None       # {"owner": worker_id, "token": str, "expires_at": ISO}
    proposed_by: dict        # {"model", "request_id", "rationale", "evidence_ids", "fallback_used"}
    goal_version_at_proposal: int
    result: ExperimentResult | None
    error: str | None
    created_at: str
    started_at: str | None
    finished_at: str | None


class MemoryDoc(TypedDict):
    _id: str
    campaign_id: str
    protocol_id: str
    kind: str                # one of MEMORY_KINDS
    text: str
    source_ids: list[str]    # experiment/event ids this note is grounded in
    verified: bool           # True only for code-rendered verified_result notes
    status: str              # "active" | "obsolete"
    synthetic: bool          # True for stress/distractor fixtures; never in result summaries
    embedding: list[float] | None
    created_at: str


class EventDoc(TypedDict):
    _id: Any                 # ObjectId
    campaign_id: str
    ts: str
    type: str                # one of EVENT_TYPES
    worker_id: str | None
    payload: dict


class RetrievedMemory(TypedDict):
    memory_id: str
    kind: str
    text: str
    source_ids: list[str]
    score: float | None      # vectorSearchScore; None on fallback retrieval
    verified: bool
    retrieval: Literal["vector", "fallback"]


class EvidencePacket(TypedDict):
    """Everything the planner sees for one decision. Built fresh from Atlas every call."""
    packet_id: str           # "pk_<hex>", also the packets._id
    campaign_id: str
    protocol_id: str         # needed to compute experiment_key() of a proposal
    strategy: str            # one of PACKET_STRATEGIES
    goal: dict               # {"objective", "goal_version", "constraints", "budget": {"max_experiments","used","remaining"}}
    incumbent: dict | None   # {"experiment_id", "label", "config", "val_balanced_accuracy"}
    pending: list[dict]      # [{"experiment_id", "label", "status"}]
    recent: list[dict]       # [{"experiment_id", "label", "status", "val_balanced_accuracy", "eligible"}]
    retrieved: list[RetrievedMemory]
    tried_keys: list[str]    # every experiment key already queued/running/done/failed
    surface: dict            # surface_summary()
    token_estimate: int      # estimate, labeled as such in the UI
    budget_tokens: int


class PlannerUsage(TypedDict):
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    source: Literal["provider", "estimate"]


class PlannerResult(TypedDict):
    action: Literal["propose", "stop"]
    config: dict | None      # normalized effective config when action == "propose"
    rationale: str
    evidence_ids: list[str]  # must be ids that appear in the packet
    model: str
    request_id: str | None
    usage: PlannerUsage
    fallback_used: bool
    fallback_reason: str | None
