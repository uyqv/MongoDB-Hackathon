"""Exploratory subject-cluster uncertainty, never sealed-test inference.

Subjects are resampled with replacement, retaining every trial in each sampled
subject. Paired comparisons use the same draws and require identical identities
and labels. Repeated adaptive validation selection is not corrected by these CIs.
"""
from __future__ import annotations

import numpy as np

EVIDENCE_VERSION = 1
BOOTSTRAP_SEED = 42
N_RESAMPLES = 2000
THRESHOLD = 0.02


def validate_predictions(rows: list[dict]) -> list[dict]:
    if not isinstance(rows, list) or not rows:
        raise ValueError("validation predictions must be a nonempty list")
    seen = set()
    for r in rows:
        if not isinstance(r, dict) or not isinstance(r.get("trial_id"), str) or not r["trial_id"]:
            raise ValueError("missing trial identity")
        if r["trial_id"] in seen:
            raise ValueError("duplicate trial identity")
        seen.add(r["trial_id"])
        if type(r.get("subject")) is not int or r["subject"] < 1 or r.get("run") != 10:
            raise ValueError("evidence must identify a subject and validation run 10")
        if any(type(r.get(k)) is not int or r[k] not in (0, 1) for k in ("y_true", "y_pred")):
            raise ValueError("labels and predictions must be binary integers")
    for s in {r["subject"] for r in rows}:
        if {r["y_true"] for r in rows if r["subject"] == s} != {0, 1}:
            raise ValueError("each subject must have both validation classes")
    return sorted(rows, key=lambda r: r["trial_id"])


def _counts(rows):
    return np.array([[sum(r["subject"] == s and r["y_true"] == label and r["y_pred"] == pred
                         for r in rows) for label, pred in ((0, 0), (0, 1), (1, 1), (1, 0))]
                     for s in sorted({r["subject"] for r in rows})], dtype=float)


def _accuracy(counts):
    return (counts[..., 0] / (counts[..., 0] + counts[..., 1])
            + counts[..., 2] / (counts[..., 2] + counts[..., 3])) / 2


def summarize(rows: list[dict], reference: list[dict] | None = None) -> dict:
    rows = validate_predictions(rows)
    counts = _counts(rows)
    ref_counts = None
    if reference is not None:
        reference = validate_predictions(reference)
        identity = lambda rr: [(r["trial_id"], r["subject"], r["run"], r["y_true"]) for r in rr]
        if identity(rows) != identity(reference):
            raise ValueError("paired evidence has different trial identities or labels")
        ref_counts = _counts(reference)
    estimate = float(_accuracy(counts.sum(axis=0)))
    if ref_counts is not None:
        estimate -= float(_accuracy(ref_counts.sum(axis=0)))
    out = {"method": "subject_cluster_percentile", "seed": BOOTSTRAP_SEED,
           "n_resamples": N_RESAMPLES, "confidence_level": 0.95, "n_subjects": len(counts),
           "estimate": estimate, "interval": None, "variance": None,
           "scope": "exploratory_adaptive_validation", "paired": reference is not None}
    if len(counts) < 2:
        return {**out, "available": False, "reason": "subject uncertainty requires at least two subjects"}
    draws = np.random.default_rng(BOOTSTRAP_SEED).integers(len(counts), size=(N_RESAMPLES, len(counts)))
    values = _accuracy(counts[draws].sum(axis=1))
    if ref_counts is not None:
        values -= _accuracy(ref_counts[draws].sum(axis=1))
    return {**out, "available": True, "interval": np.quantile(values, [0.025, 0.975]).tolist(),
            "variance": float(np.var(values, ddof=1))}


def validate_result(result: dict) -> list[dict]:
    if result.get("validation_evidence_version") != EVIDENCE_VERSION:
        raise ValueError("missing or unsupported validation evidence version")
    rows = validate_predictions(result.get("validation_predictions"))
    accuracy = float(_accuracy(_counts(rows).sum(axis=0)))
    score = result.get("val_balanced_accuracy")
    if (not isinstance(score, (float, int)) or not np.isfinite(score)
            or abs(score - accuracy) > 0.000051 or result.get("n_val") != len(rows)):
        raise ValueError("aggregate validation result disagrees with trial evidence")
    return rows
