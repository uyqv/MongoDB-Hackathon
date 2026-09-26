"""EEG numerical runner (PhysioNet eegmmidb, runs 6/10/14, imagined fists vs feet).

OWNER: Andrew.

No language model touches anything in this file. It computes every metric.

Protocol (fixed before any results were seen, see docs/WORKPLAN.md): within
subject. Each subject gets its own model fit on run 6 and scored on run 10;
run 14 stays sealed until score_test_once. Predictions are pooled across
subjects before computing balanced accuracy / macro F1.

Filtering is offline zero-phase FIR on each continuous run. It is not learned,
so it cannot leak labels, but it is not a causal real-time decoder either.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import mne
import numpy as np
from mne.datasets import eegbci
from mne.decoding import CSP
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from harness.contracts import (
    BANDS, CHANNEL_SETS, EVALUATOR_VERSION, SEED, WINDOWS, normalize_config, protocol_id,
)

mne.set_log_level("ERROR")

MODES = {"smoke": (1,), "demo": (1, 2, 3, 4, 5)}
SPLIT_RUNS = {"train": 6, "val": 10, "test": 14}
EVENT_IDS = {"T1": 0, "T2": 1}   # runs 6/10/14: T1 = both fists, T2 = both feet


def data_dir() -> str:
    return os.environ.get("EEG_DATA_DIR", "data/eeg")


@dataclass
class Recording:
    subject: int
    run: int
    ch_names: list[str]
    sfreq: float
    signal: np.ndarray      # (n_channels, n_times)
    onsets: np.ndarray      # sample index of each task cue
    labels: np.ndarray      # 0 = fists, 1 = feet
    trial_ids: list[str]


@dataclass
class EEGData:
    recordings: dict[tuple[int, int], Recording]
    _filtered: dict[tuple[int, int, str], np.ndarray] = field(default_factory=dict)

    def filtered(self, subject: int, run: int, band: str) -> np.ndarray:
        key = (subject, run, band)
        if key not in self._filtered:
            rec = self.recordings[(subject, run)]
            lo, hi = BANDS[band]
            self._filtered[key] = mne.filter.filter_data(rec.signal, rec.sfreq, lo, hi, phase="zero")
        return self._filtered[key]


def _edf_path(subject: int, run: int) -> Path:
    return Path(eegbci.load_data(subject, [run], path=data_dir(), update_path=False)[0])


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_recording(subject: int, run: int) -> Recording:
    raw = mne.io.read_raw_edf(_edf_path(subject, run), preload=True)
    eegbci.standardize(raw)
    raw.pick("eeg")
    events, _ = mne.events_from_annotations(raw, event_id={"T1": 1, "T2": 2})
    signal = raw.get_data()
    onsets = events[:, 0] - raw.first_samp
    validate_recording(signal, onsets, f"S{subject:03d}R{run:02d}")
    return Recording(
        subject=subject, run=run, ch_names=list(raw.ch_names), sfreq=float(raw.info["sfreq"]),
        signal=signal, onsets=onsets, labels=events[:, 2] - 1,
        trial_ids=[f"S{subject:03d}R{run:02d}T{i:02d}" for i in range(len(onsets))],
    )


def validate_recording(signal: np.ndarray, onsets: np.ndarray, name: str) -> None:
    if not np.isfinite(signal).all():
        raise ValueError(f"non-finite samples in {name}")
    if len(set(onsets.tolist())) != len(onsets):
        raise ValueError(f"duplicate epoch onsets in {name}")


def check_splits(split_ids: dict[str, list[str]]) -> None:
    """No trial appears twice within a split or in more than one split."""
    seen: dict[str, str] = {}
    for split, ids in split_ids.items():
        if len(set(ids)) != len(ids):
            raise ValueError(f"duplicate trial ids in {split}")
        for i in ids:
            if i in seen:
                raise ValueError(f"trial {i} is in both {seen[i]} and {split}")
            seen[i] = split


def load_protocol(mode: str = "demo", evidence_version: int | None = None) -> tuple[dict, EEGData]:
    """Download (cached) and parse train/val runs for `mode`. Test runs are hashed, not parsed."""
    if evidence_version not in (None, 1):
        raise ValueError("unsupported validation evidence version")
    subjects = MODES[mode]
    files: dict[str, str] = {}
    recordings: dict[tuple[int, int], Recording] = {}
    split_ids: dict[str, list[str]] = {"train": [], "val": []}
    for s in subjects:
        for split, run in SPLIT_RUNS.items():
            path = _edf_path(s, run)
            files[path.name] = _sha256(path)
            if split == "test":
                continue
            rec = load_recording(s, run)
            recordings[(s, run)] = rec
            split_ids[split].extend(rec.trial_ids)
    check_splits(split_ids)
    protocol = {
        "dataset": "physionet-eegmmidb-1.0.0",
        "task": "imagined both fists (T1) vs both feet (T2)",
        "mode": mode,
        "scheme": "within_subject_pooled",
        "subjects": list(subjects),
        "split_runs": dict(SPLIT_RUNS),
        "split_ids": split_ids,
        "test": "sealed: run 14 of each subject, scored once at finalize",
        "files": files,
        "evaluator_version": EVALUATOR_VERSION,
        "seed": SEED,
    }
    if evidence_version is not None:
        protocol["validation_evidence_version"] = evidence_version
    return protocol, EEGData(recordings)


def _epochs(data: EEGData, subject: int, run: int, cfg: dict) -> tuple[np.ndarray, np.ndarray]:
    rec = data.recordings[(subject, run)]
    wanted = CHANNEL_SETS[cfg["channels"]] or rec.ch_names
    missing = [c for c in wanted if c not in rec.ch_names]
    if missing:
        raise ValueError(f"missing channels {missing} in S{subject:03d}R{run:02d}")
    idx = [rec.ch_names.index(c) for c in wanted]
    lo, hi = WINDOWS[cfg["window"]]
    start = rec.onsets + int(round(lo * rec.sfreq))
    length = int(round((hi - lo) * rec.sfreq))
    keep = start + length <= rec.signal.shape[1]
    sig = data.filtered(subject, run, cfg["band"])
    X = np.stack([sig[idx, s:s + length] for s in start[keep]])
    y = rec.labels[keep]
    if len(set(y.tolist())) < 2:
        raise ValueError(f"S{subject:03d}R{run:02d} lacks both classes after windowing")
    return X, y


def _log_variance(X: np.ndarray) -> np.ndarray:
    return np.log(np.var(X, axis=2))


def _pipeline(cfg: dict):
    if cfg["method"] == "bandpower_lr":
        return make_pipeline(
            FunctionTransformer(_log_variance), StandardScaler(),
            LogisticRegression(C=cfg["C"], max_iter=1000, random_state=SEED),
        )
    return make_pipeline(
        CSP(n_components=cfg["n_components"], reg=None, log=True, norm_trace=False),
        LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"),
    )


def _checked(value: float, name: str) -> float:
    if not np.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name}={value} is not a finite value in [0, 1]")
    return round(float(value), 4)


def _fit_predict(cfg: dict, protocol: dict, data: EEGData, eval_run: int,
                 predictions: list | None = None) -> tuple[list, list, dict, int, int]:
    y_true: list[int] = []
    y_pred: list[int] = []
    per_subject: dict[str, float] = {}
    n_train = n_eval = 0
    for s in protocol["subjects"]:
        X_tr, y_tr = _epochs(data, s, SPLIT_RUNS["train"], cfg)
        X_ev, y_ev = _epochs(data, s, eval_run, cfg)
        pred = _pipeline(cfg).fit(X_tr, y_tr).predict(X_ev)
        if predictions is not None:
            rec = data.recordings[(s, eval_run)]
            lo, hi = WINDOWS[cfg["window"]]
            ends = rec.onsets + int(round(lo * rec.sfreq)) + int(round((hi - lo) * rec.sfreq))
            ids = [tid for tid, keep in zip(rec.trial_ids, ends <= rec.signal.shape[1]) if keep]
            predictions.extend({"trial_id": tid, "subject": int(s), "run": eval_run,
                                "y_true": int(y), "y_pred": int(p)} for tid, y, p in zip(ids, y_ev, pred))
        per_subject[str(s)] = round(float(balanced_accuracy_score(y_ev, pred)), 4)
        y_true.extend(y_ev.tolist())
        y_pred.extend(pred.tolist())
        n_train += len(y_tr)
        n_eval += len(y_ev)
    return y_true, y_pred, per_subject, n_train, n_eval


def run_experiment(cfg: dict, protocol: dict, data: EEGData) -> dict:
    """Fit on train (run 6), score on validation (run 10). Returns a contracts.ExperimentResult."""
    c = normalize_config(cfg)
    t0 = time.perf_counter()
    predictions = [] if protocol.get("validation_evidence_version") == 1 else None
    y_true, y_pred, per_subject, n_train, n_val = _fit_predict(c, protocol, data, SPLIT_RUNS["val"], predictions)
    n_ch = len(CHANNEL_SETS[c["channels"]] or data.recordings[(protocol["subjects"][0], SPLIT_RUNS["train"])].ch_names)
    result = {
        "val_balanced_accuracy": _checked(balanced_accuracy_score(y_true, y_pred), "val_balanced_accuracy"),
        "val_f1": _checked(f1_score(y_true, y_pred, average="macro"), "val_f1"),
        "n_train": n_train,
        "n_val": n_val,
        "n_channels": n_ch,
        "fit_seconds": round(time.perf_counter() - t0, 3),
        "evaluator_version": EVALUATOR_VERSION,
        "per_subject_val_balanced_accuracy": per_subject,
    }
    if predictions is not None:
        from harness.uncertainty import summarize
        result.update(validation_evidence_version=1, validation_predictions=predictions,
                      uncertainty=summarize(predictions))
    return result


def score_test_once(cfg: dict, protocol: dict, data: EEGData) -> dict:
    """Separate evaluator capability: parse and score the sealed test runs.

    The caller (store/worker) guarantees this runs once per campaign, after the
    config is frozen. File hashes are re-checked so a changed file can't be scored.
    """
    c = normalize_config(cfg)
    run = SPLIT_RUNS["test"]
    for s in protocol["subjects"]:
        path = _edf_path(s, run)
        if _sha256(path) != protocol["files"][path.name]:
            raise ValueError(f"{path.name} changed since the protocol was frozen")
        if (s, run) not in data.recordings:
            data.recordings[(s, run)] = load_recording(s, run)
    y_true, y_pred, per_subject, _, n_test = _fit_predict(c, protocol, data, run)
    return {
        "test_balanced_accuracy": _checked(balanced_accuracy_score(y_true, y_pred), "test_balanced_accuracy"),
        "test_f1": _checked(f1_score(y_true, y_pred, average="macro"), "test_f1"),
        "n_test": n_test,
        "per_subject_test_balanced_accuracy": per_subject,
    }


def main() -> None:
    """Gate 1: load real data, print membership + hashes, run a few configs on validation only."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="smoke", choices=list(MODES))
    args = ap.parse_args()
    t0 = time.perf_counter()
    protocol, data = load_protocol(args.mode)
    print(f"protocol {protocol_id(protocol)}  mode={args.mode}  load {time.perf_counter() - t0:.1f}s")
    for name, sha in protocol["files"].items():
        print(f"  {name}  sha256 {sha[:16]}…")
    for split, ids in protocol["split_ids"].items():
        print(f"  {split}: {len(ids)} trials  e.g. {ids[:2]}")
    for (s, r), rec in sorted(data.recordings.items()):
        counts = np.bincount(rec.labels, minlength=2)
        print(f"  S{s:03d}R{r:02d}: {counts[0]} fists / {counts[1]} feet, {len(rec.ch_names)} ch @ {rec.sfreq} Hz")
    probes = [
        {"method": "csp_lda", "band": "broad_8_30", "window": "w1.0_3.0", "channels": "all64", "n_components": 4},
        {"method": "csp_lda", "band": "broad_8_30", "window": "w1.0_3.0", "channels": "central9", "n_components": 4},
        {"method": "bandpower_lr", "band": "mu_8_12", "window": "w1.0_3.0", "channels": "central9", "C": 1.0},
        {"method": "bandpower_lr", "band": "beta_13_30", "window": "w0.5_2.5", "channels": "motor21", "C": 0.1},
    ]
    for cfg in probes:
        r = run_experiment(cfg, protocol, data)
        print(f"  {cfg['method']:12s} {cfg['band']:14s} {cfg['window']:9s} {cfg['channels']:8s} "
              f"val_bacc={r['val_balanced_accuracy']:.3f} f1={r['val_f1']:.3f} "
              f"n={r['n_train']}/{r['n_val']} {r['fit_seconds']:.2f}s per_subject={r['per_subject_val_balanced_accuracy']}")


if __name__ == "__main__":
    main()
