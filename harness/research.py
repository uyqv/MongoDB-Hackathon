"""Versioned, reproducible finite-surface experimental design. No LLM or DB I/O."""
from __future__ import annotations

import hashlib
import numpy as np
from scipy.special import ndtr
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern

from harness import contracts as C
from harness.uncertainty import summarize, validate_result, THRESHOLD

POLICY = "research_v1"
SETTINGS = {"encoding": "one_hot_effective_fields_v1", "kernel": "constant_times_matern",
            "amplitude": 0.04, "length_scale": 1.0, "nu": 2.5, "prior_mean": 0.5,
            "noise_floor": 1e-4, "single_subject_noise": 0.01, "ei_margin": 0.0,
            "initial_experiments": 3, "shortlist_size": 6}
SURFACE = C.all_configs()
FEATURES = sorted({(k, str(v)) for c in SURFACE for k, v in c.items()})


def encode(configs):
    return np.array([[float(str(c.get(k, "<inactive>")) == v) for k, v in FEATURES]
                     for c in configs])


def changed_parameters(a, b):
    return [k for k in sorted(a.keys() | b.keys()) if a.get(k) != b.get(k)]


def _tie(seed, cfg):
    return hashlib.sha256(f"{seed}|{C.canonical_json(cfg)}".encode()).hexdigest()


def diverse_order(candidates, tried, seed):
    """Greedy max-min one-hot distance, with deterministic seeded tie breaking."""
    remaining = sorted(candidates, key=lambda c: _tie(seed, c))
    selected = list(tried)
    out = []
    while remaining:
        if selected:
            x, prev = encode(remaining), encode(selected)
            distances = ((x[:, None, :] - prev[None, :, :]) ** 2).sum(axis=2).min(axis=1)
            index = int(np.argmax(distances))
        else:
            index = 0
        cfg = remaining.pop(index)
        selected.append(cfg)
        out.append(cfg)
        if len(out) == SETTINGS["shortlist_size"]:
            break
    return out


def rank(campaign: dict, experiments: list[dict]) -> dict:
    pid = campaign["protocol_id"]
    seed = campaign.get("research_seed", C.SEED)
    exps = sorted((e for e in experiments if e["protocol_id"] == pid), key=lambda e: e["_id"])
    tried = {e["key"] for e in exps}
    candidates = [c for c in SURFACE if C.is_eligible(c, campaign["constraints"])
                  and C.experiment_key(pid, c) not in tried]
    done = [e for e in exps if e["status"] == "done"]
    eligible = [e for e in done if C.is_eligible(e["config"], campaign["constraints"])]
    incumbent = max(eligible, key=lambda e: (e["result"]["val_balanced_accuracy"], e["result"]["val_f1"], e["_id"]),
                    default=None)
    meta = {"policy_version": POLICY, "settings": SETTINGS, "seed": seed,
            "source_experiment_ids": [e["_id"] for e in done], "goal_version": campaign["goal_version"],
            "phase": "initialization" if len(exps) < 3 else "optimization", "fallback_reason": None,
            "reference_experiment_id": incumbent["_id"] if incumbent else None}

    def row(cfg, reason, mu=None, std=None, ei=None):
        return {"candidate_id": C.experiment_key(pid, cfg), "config": cfg, "label": C.config_label(cfg),
                "selection_reason": reason, "predicted_accuracy": mu, "predictive_std": std,
                "expected_improvement": ei,
                "changed_parameters": changed_parameters(incumbent["config"], cfg) if incumbent else []}

    def diversity(reason):
        configs = diverse_order(candidates, [e["config"] for e in exps], seed)
        # Initialization is deliberately prescribed and shared by benchmark arms.
        if meta["phase"] == "initialization":
            configs = configs[:1]
        return {**meta, "candidates": [row(c, reason) for c in configs]}

    if not candidates:
        return {**meta, "candidates": []}
    if len(exps) < 3:
        return diversity("seeded_initialization")
    try:
        if not done:
            raise ValueError("no successful observations")
        uncertainties = [summarize(validate_result(e["result"])) for e in done]
        gp = GaussianProcessRegressor(
            kernel=ConstantKernel(SETTINGS["amplitude"], "fixed") * Matern(
                length_scale=SETTINGS["length_scale"], length_scale_bounds="fixed", nu=SETTINGS["nu"]),
            alpha=np.array([max(u["variance"], SETTINGS["noise_floor"]) if u["available"]
                            else SETTINGS["single_subject_noise"] for u in uncertainties]),
            optimizer=None, normalize_y=False, random_state=seed)
        gp.fit(encode([e["config"] for e in done]),
               np.array([u["estimate"] for u in uncertainties]) - SETTINGS["prior_mean"])
        mu, std = gp.predict(encode(candidates), return_std=True)
        mu += SETTINGS["prior_mean"]
        target = incumbent["result"]["val_balanced_accuracy"] if incumbent else SETTINGS["prior_mean"]
        delta = mu - target
        z = np.divide(delta, std, out=np.zeros_like(delta), where=std > 0)
        ei = np.where(std > 0, delta * ndtr(z) + std * np.exp(-z*z / 2) / np.sqrt(2*np.pi),
                      np.maximum(delta, 0))
        if not all(np.isfinite(a).all() for a in (mu, std, ei)):
            raise ValueError("nonfinite surrogate predictions")
        improvement = sorted(range(len(candidates)), key=lambda i: (-ei[i], _tie(seed, candidates[i])))
        uncertainty = sorted(range(len(candidates)), key=lambda i: (-std[i], _tie(seed, candidates[i])))
        picks = []
        def add(indices, count, reason):
            for i in indices:
                if i not in [j for j, _ in picks]:
                    picks.append((i, reason))
                    count -= 1
                    if count == 0:
                        break
        add(improvement, 3, "expected_improvement")
        add(uncertainty, 2, "uncertainty")
        if incumbent:
            add([i for i in improvement if len(changed_parameters(incumbent["config"], candidates[i])) == 1],
                1, "single_parameter_comparison")
        if len(picks) < 6:
            add(improvement, 6 - len(picks), "expected_improvement")
        return {**meta, "candidates": [row(candidates[i], reason, float(mu[i]), float(std[i]), float(ei[i]))
                                      for i, reason in picks[:6]]}
    except (ValueError, TypeError, KeyError, np.linalg.LinAlgError) as exc:
        meta["fallback_reason"] = f"surrogate unavailable: {type(exc).__name__}: {exc}"[:250]
        return diversity("surrogate_fallback_diversity")


def proposal_metadata(packet, config):
    research = packet["research"]
    candidate = next(c for c in research["candidates"] if c["config"] == config)
    reference = research["reference_experiment_id"] if research["phase"] != "initialization" else None
    inc = packet.get("incumbent")
    prediction = candidate["predicted_accuracy"]
    return {"candidate_id": candidate["candidate_id"],
            "hypothesis": {"kind": "comparison" if reference else "exploration",
                           "reference_experiment_id": reference, "threshold": THRESHOLD,
                           "changed_parameters": candidate["changed_parameters"],
                           "predicted_improvement": prediction - inc["val_balanced_accuracy"]
                           if prediction is not None and inc and reference else None}}
