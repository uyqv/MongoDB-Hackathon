"""EEG numerical runner (PhysioNet eegmmidb, runs 6/10/14, imagined fists vs feet).

OWNER: Andrew.

No language model touches anything in this file. It computes every metric.
"""
from __future__ import annotations


def load_protocol(mode: str = "demo") -> tuple[dict, object]:
    """Download (cached) and parse the data for `mode` ("smoke" | "demo").

    Returns (protocol_dict, data). protocol_dict holds file sha256s, exact split
    ids, EVALUATOR_VERSION and SEED; pass it to contracts.protocol_id().
    """
    raise NotImplementedError


def run_experiment(cfg: dict, protocol: dict, data: object) -> dict:
    """Fit on train, score on validation. Returns a contracts.ExperimentResult dict."""
    raise NotImplementedError


def score_test_once(cfg: dict, protocol: dict, data: object) -> dict:
    """Separate evaluator capability: score the sealed test partition. Called once, at finalize."""
    raise NotImplementedError
