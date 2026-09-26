import pytest

from harness.contracts import (
    all_configs, experiment_key, is_eligible, normalize_config, protocol_id,
)

CSP = {"method": "csp_lda", "band": "broad_8_30", "window": "w1.0_3.0", "channels": "central9", "n_components": 4}


def test_surface_size():
    configs = all_configs()
    assert len(configs) == 225
    assert len({str(sorted(c.items())) for c in configs}) == 225


def test_unused_param_does_not_change_key():
    pid = protocol_id({"files": {"a": "1"}})
    assert experiment_key(pid, CSP) == experiment_key(pid, {**CSP, "C": 1.0, "foo": "bar"})


def test_key_changes_with_protocol():
    assert experiment_key(protocol_id({"v": 1}), CSP) != experiment_key(protocol_id({"v": 2}), CSP)


def test_hash_is_order_independent():
    assert protocol_id({"a": 1, "b": 2}) == protocol_id({"b": 2, "a": 1})


@pytest.mark.parametrize("bad", [
    {**CSP, "method": "transformer"},
    {**CSP, "band": "gamma"},
    {**CSP, "n_components": 8},
    {"method": "bandpower_lr", "band": "mu_8_12", "window": "w1.0_3.0", "channels": "all64"},
])
def test_outside_surface_rejected(bad):
    with pytest.raises(ValueError):
        normalize_config(bad)


def test_eligibility_follows_current_constraint():
    assert is_eligible(CSP, {"max_channels": 9})
    assert not is_eligible({**CSP, "channels": "all64"}, {"max_channels": 9})
    assert is_eligible({**CSP, "channels": "all64"}, {"max_channels": 64})
