from harness.contracts import all_configs, experiment_key
from harness.worker import fallback_plan, guard

PID = "p_test"
CSP9 = {"method": "csp_lda", "band": "broad_8_30", "window": "w1.0_3.0", "channels": "central9", "n_components": 4}


def _packet(max_channels=64, tried=()):
    return {"campaign_id": "camp_x", "protocol_id": PID, "tried_keys": list(tried),
            "goal": {"constraints": {"max_channels": max_channels}}}


def test_guard_accepts_valid_untried():
    assert guard(_packet(), {"config": CSP9}) is None


def test_guard_rejects_ineligible_tried_and_unknown():
    assert "ineligible" in guard(_packet(max_channels=9), {"config": {**CSP9, "channels": "all64"}})
    assert "already tried" in guard(_packet(tried=[experiment_key(PID, CSP9)]), {"config": CSP9})
    assert "outside" in guard(_packet(), {"config": {**CSP9, "method": "eegnet"}})
    assert "outside" in guard(_packet(), {"config": None})


def test_fallback_is_eligible_untried_then_stops():
    tried = []
    for _ in range(3):
        r = fallback_plan(_packet(max_channels=9, tried=tried), "test")
        assert r["fallback_used"] and r["action"] == "propose"
        assert guard(_packet(max_channels=9, tried=tried), r) is None
        tried.append(experiment_key(PID, r["config"]))
    everything = [experiment_key(PID, c) for c in all_configs()]
    assert fallback_plan(_packet(tried=everything), "test")["action"] == "stop"
