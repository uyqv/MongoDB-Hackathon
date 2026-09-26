"""Numerical invariants and policy boundaries, with no network calls."""
import copy
import json

import numpy as np
import pytest

from harness import contracts as C, research, planner
from harness.context import assemble_packet, estimate_tokens, planner_view
from harness.hypotheses import assessment
from harness.uncertainty import summarize, validate_result
from harness.worker import fallback_plan, guard
from tests.test_planner import FakeClient, tool_resp


def predictions(subjects=5, correct=7):
    return [{"trial_id": f"S{s}T{i}", "subject": s, "run": 10, "y_true": i % 2,
             "y_pred": i % 2 if i < correct else 1 - i % 2}
            for s in range(1, subjects + 1) for i in range(10)]


def measurement(rows):
    u = summarize(rows)
    return {"validation_evidence_version": 1, "validation_predictions": rows, "uncertainty": u,
            "val_balanced_accuracy": round(u["estimate"], 4), "val_f1": round(u["estimate"], 4),
            "n_val": len(rows), "fit_seconds": 0.1}


def campaign():
    return {"_id": "c", "protocol_id": "p", "objective": "test", "policy": "research_v1",
            "research_seed": 42, "goal_version": 1, "constraints": {"max_channels": 64},
            "budget": {"max_experiments": 10}}


def history(n=3):
    camp = campaign()
    exps = []
    for i in range(n):
        cfg = C.all_configs()[i]
        key = C.experiment_key("p", cfg)
        exps.append({"_id": C.experiment_doc_id("c", key), "key": key, "protocol_id": "p",
                     "campaign_id": "c", "config": cfg, "label": C.config_label(cfg),
                     "status": "done", "result": measurement(predictions(correct=6 + i % 4)),
                     "created_at": str(i)})
    return camp, exps


def test_cluster_bootstrap_determinism_and_pair_alignment():
    rows = predictions()
    rows[0]["y_pred"] = 1
    first = summarize(rows)
    assert first == summarize(list(reversed(rows)))
    assert first["available"] and first["n_resamples"] == 2000 and first["variance"] > 0
    same = summarize(rows, list(reversed(rows)))
    assert same["estimate"] == 0 and same["interval"] == [0, 0] and same["variance"] == 0
    shifted = copy.deepcopy(rows)
    shifted[0]["trial_id"] = "different"
    with pytest.raises(ValueError, match="identities"):
        summarize(rows, shifted)
    shifted = copy.deepcopy(rows)
    shifted[0]["y_true"] = 1
    with pytest.raises(ValueError, match="identities"):
        summarize(rows, shifted)


def test_smoke_has_no_subject_interval():
    u = summarize(predictions(subjects=1))
    assert not u["available"] and u["interval"] is None and u["variance"] is None


@pytest.mark.parametrize("mutation", [
    lambda r: r.append(r[0]), lambda r: r[0].update(y_pred=float("nan")),
    lambda r: r[0].update(run=14), lambda r: r[0].update(subject=None),
])
def test_invalid_evidence_is_rejected(mutation):
    rows = predictions()
    mutation(rows)
    with pytest.raises(ValueError):
        summarize(rows)


def test_result_must_match_predictions_and_version():
    result = measurement(predictions())
    validate_result(result)
    for bad in ({**result, "n_val": 1}, {**result, "val_balanced_accuracy": 0.99},
                {**result, "validation_evidence_version": 0}):
        with pytest.raises(ValueError):
            validate_result(bad)


def test_three_initializations_are_seeded_diverse_and_counted():
    camp, exps = history(0)
    configs = []
    for i in range(3):
        ranking = research.rank(camp, exps)
        assert ranking["phase"] == "initialization" and len(ranking["candidates"]) == 1
        cfg = ranking["candidates"][0]["config"]
        assert cfg not in configs
        if i == 1:
            chosen_distance = np.sum((research.encode([cfg])[0] - research.encode([configs[0]])[0]) ** 2)
            all_distances = np.sum((research.encode(C.all_configs()) - research.encode([configs[0]])[0]) ** 2, axis=1)
            assert chosen_distance == max(all_distances)
        configs.append(cfg)
        key = C.experiment_key("p", cfg)
        exps.append({"_id": key, "key": key, "protocol_id": "p", "config": cfg, "status": "failed"})
    assert research.rank(camp, exps)["phase"] == "optimization"


def test_rank_replay_membership_constraints_and_neighbor():
    camp, exps = history()
    ranking = research.rank(camp, exps)
    assert ranking == research.rank(camp, list(reversed(exps)))
    assert ranking["fallback_reason"] is None
    candidates = ranking["candidates"]
    assert len({c["candidate_id"] for c in candidates}) == 6
    assert candidates[0]["expected_improvement"] == max(c["expected_improvement"] for c in candidates)
    assert any(c["selection_reason"] == "single_parameter_comparison" for c in candidates)
    camp["constraints"] = {"max_channels": 9}
    camp["goal_version"] = 2
    restricted = research.rank(camp, exps)
    assert restricted["goal_version"] == 2
    assert all(C.is_eligible(c["config"], camp["constraints"]) for c in restricted["candidates"])
    assert not {c["candidate_id"] for c in candidates} & {e["key"] for e in exps}


def test_numerical_failure_uses_logged_diversity(monkeypatch):
    camp, exps = history()
    def broken(*a, **kw):
        raise np.linalg.LinAlgError("fixture singularity")
    monkeypatch.setattr(research.GaussianProcessRegressor, "fit", broken)
    result = research.rank(camp, exps)
    assert "singularity" in result["fallback_reason"]
    assert result["candidates"][0]["predicted_accuracy"] is None
    assert result == research.rank(camp, exps)


def test_research_packet_is_bounded_after_long_history():
    camp, exps = history(220)
    camp["budget"]["max_experiments"] = 225
    packet = assemble_packet(camp, exps, notes=[{"text": "huge" * 10000}])
    assert estimate_tokens(planner_view(packet)) <= 4000
    assert len(packet["tried_keys"]) == 220
    assert "tried_keys" not in planner_view(packet) and "tried" not in planner_view(packet)
    assert len(packet["research_audit"]["source_experiment_ids"]) == 220
    assert packet["research"]["candidates"] and packet["incumbent"]
    with pytest.raises(ValueError, match="budget"):
        assemble_packet(camp, exps, budget_tokens=10)


def test_llm_candidate_repair_and_numerical_fallback(monkeypatch):
    camp, exps = history()
    packet = assemble_packet(camp, exps)
    candidate = packet["research"]["candidates"][1]
    invalid = {"candidate_id": "invented", "rationale": "test", "evidence_ids": []}
    valid = {**invalid, "candidate_id": candidate["candidate_id"]}
    fake = FakeClient([tool_resp("propose_experiment", invalid), tool_resp("propose_experiment", valid)])
    monkeypatch.setattr(planner, "client_factory", lambda: fake)
    result = planner.plan(packet)
    assert result["candidate_id"] == candidate["candidate_id"] and not result["fallback_used"]
    assert result["hypothesis"]["threshold"] == 0.02 and guard(packet, result) is None
    assert len(fake.calls) == 2
    fake = FakeClient([RuntimeError("offline")])
    result = planner.plan(packet)
    assert result["fallback_used"] and result["candidate_id"] == packet["research"]["candidates"][0]["candidate_id"]
    assert guard(packet, {**result, "candidate_id": "invented"})
    assert guard(packet, fallback_plan(packet, "offline")) is None


def test_initialization_never_calls_the_provider(monkeypatch):
    from harness.worker import call_planner
    def forbidden(*args):
        raise AssertionError("seeded initialization must not call an LLM")
    monkeypatch.setattr(planner, "client_factory", forbidden)
    result = call_planner(assemble_packet(*history(0)))
    assert result["model"] == "research_v1_initialization" and not result["fallback_used"]
    assert result["hypothesis"]["kind"] == "exploration"
    packet = assemble_packet(*history(0))
    packet["goal"]["budget"]["remaining"] = 0
    assert call_planner(packet)["action"] == "stop"


@pytest.mark.parametrize("candidate_correct,expected", [(10, "supported_on_validation"),
                                                         (7, "contradicted_on_validation")])
def test_hypothesis_assessment_uses_paired_measured_difference(candidate_correct, expected):
    camp, exps = history()
    reference = exps[0]
    reference["result"] = measurement(predictions(correct=7))
    experiment = {**exps[1], "result": measurement(predictions(correct=candidate_correct)),
                  "proposed_by": {"hypothesis": {"kind": "comparison"}}}
    assert assessment(experiment, reference)["status"] == expected
    experiment["result"] = measurement(predictions(subjects=1))
    assert assessment(experiment, reference)["status"] == "inconclusive"


def test_exact_two_point_boundary_is_inconclusive_despite_float_rounding():
    def rows(correct):
        return [{"trial_id": f"S{s}T{i}", "subject": s, "run": 10, "y_true": i % 2,
                 "y_pred": i % 2 if i < correct else 1 - i % 2}
                for s in range(1, 6) for i in range(50)]
    _, exps = history()
    reference, candidate = exps[:2]
    reference["result"] = measurement(rows(30))
    candidate["result"] = measurement(rows(31))
    candidate["proposed_by"] = {"hypothesis": {"kind": "comparison"}}
    assert assessment(candidate, reference)["status"] == "inconclusive"
