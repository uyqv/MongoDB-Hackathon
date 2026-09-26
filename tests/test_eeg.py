"""Offline runner tests on SYNTHETIC signals. Real-data checks live in `python -m harness.eeg`."""
import numpy as np
import pytest

from harness.contracts import CHANNEL_SETS
from harness.eeg import EEGData, Recording, check_splits, run_experiment, validate_recording

SFREQ = 160.0
CH = CHANNEL_SETS["motor21"] + [f"X{i}" for i in range(43)]  # 64 names incl. every central/motor channel


def _recording(subject, run, seed):
    rng = np.random.default_rng(seed)
    n_trials, n_times = 20, 20 * 4 * int(SFREQ) + 1000
    onsets = np.arange(n_trials) * 4 * int(SFREQ) + 200
    labels = np.array([i % 2 for i in range(n_trials)])
    sig = rng.normal(0, 1e-6, (len(CH), n_times))
    t = np.arange(int(3.5 * SFREQ)) / SFREQ
    c3, cz = CH.index("C3"), CH.index("Cz")
    for o, y in zip(onsets, labels):
        sig[c3 if y == 0 else cz, o:o + len(t)] += 4e-6 * np.sin(2 * np.pi * 10 * t)
    return Recording(subject, run, CH, SFREQ, sig, onsets, labels,
                     [f"S{subject:03d}R{run:02d}T{i:02d}" for i in range(n_trials)])


def _data():
    return EEGData({(1, 6): _recording(1, 6, 0), (1, 10): _recording(1, 10, 1)})


PROTOCOL = {"subjects": [1]}


@pytest.mark.parametrize("cfg", [
    {"method": "csp_lda", "band": "mu_8_12", "window": "w1.0_3.0", "channels": "central9", "n_components": 2},
    {"method": "bandpower_lr", "band": "mu_8_12", "window": "w1.0_3.0", "channels": "motor21", "C": 1.0},
])
def test_pipelines_learn_synthetic_signal(cfg):
    r = run_experiment(cfg, PROTOCOL, _data())
    assert r["val_balanced_accuracy"] > 0.9
    assert r["n_train"] == 20 and r["n_val"] == 20


def test_missing_channel_blocked():
    data = _data()
    for rec in data.recordings.values():
        rec.ch_names = [c if c != "Cz" else "Cz_missing" for c in rec.ch_names]
    with pytest.raises(ValueError, match="missing channels"):
        run_experiment({"method": "csp_lda", "band": "mu_8_12", "window": "w1.0_3.0",
                        "channels": "central9", "n_components": 2}, PROTOCOL, data)


def test_unknown_method_blocked():
    with pytest.raises(ValueError):
        run_experiment({"method": "eegnet", "band": "mu_8_12", "window": "w1.0_3.0", "channels": "all64"},
                       PROTOCOL, _data())


def test_nonfinite_blocked():
    sig = np.zeros((2, 100))
    sig[0, 5] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        validate_recording(sig, np.array([1, 2]), "x")


def test_duplicate_epoch_blocked():
    with pytest.raises(ValueError, match="duplicate"):
        validate_recording(np.zeros((2, 100)), np.array([10, 10]), "x")


def test_split_overlap_blocked():
    with pytest.raises(ValueError, match="both"):
        check_splits({"train": ["a", "b"], "val": ["b", "c"]})
    with pytest.raises(ValueError, match="duplicate"):
        check_splits({"train": ["a", "a"]})
    check_splits({"train": ["a"], "val": ["b"]})


def test_research_evidence_is_additive_and_tracks_epoch_identity():
    from harness.uncertainty import validate_result
    cfg = {"method": "csp_lda", "band": "mu_8_12", "window": "w1.0_3.0",
           "channels": "central9", "n_components": 2}
    legacy = run_experiment(cfg, PROTOCOL, _data())
    research = run_experiment(cfg, {**PROTOCOL, "validation_evidence_version": 1}, _data())
    assert legacy["val_balanced_accuracy"] == research["val_balanced_accuracy"]
    assert "validation_predictions" not in legacy
    rows = validate_result(research)
    assert {r["trial_id"] for r in rows} == set(_data().recordings[(1, 10)].trial_ids)
    assert not research["uncertainty"]["available"]
