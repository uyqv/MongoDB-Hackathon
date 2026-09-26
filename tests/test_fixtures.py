import pytest

from eval import fixtures, seed_fake
from harness import contracts as C
from harness import context, memory
from harness.db import get_db


@pytest.fixture(scope="module")
def dbs():
    d = get_db()
    assert d.name == "second_shift_david", "fixture tests only run against second_shift_david"
    seed_fake.main()
    yield d
    fixtures.reset(d)


@pytest.fixture(autouse=True)
def no_voyage(monkeypatch):
    # Deterministic fake vectors: no Voyage calls, and search falls back to the filtered find.
    monkeypatch.setattr(memory, "embed", lambda texts, input_type="document": [[0.0] * 8 for _ in texts])
    monkeypatch.setattr(memory, "_embed_query", lambda q: (_ for _ in ()).throw(RuntimeError("no voyage in tests")))


SRC = seed_fake.CAMPAIGN_ID


def test_all_scenarios_build_and_label(dbs):
    for name in fixtures.SCENARIOS:
        sc = fixtures.build_scenario(dbs, dbs, SRC, name, n_distractors=12, seed=1)
        cid = sc["campaign_id"]
        camp = dbs.campaigns.find_one({"_id": cid})
        assert camp["fixture"] and camp["scenario"] == name
        exps = list(dbs.experiments.find({"campaign_id": cid}))
        mems = list(dbs.memories.find({"campaign_id": cid}))
        # every injected record is labeled; copies point at a real doc
        for e in exps:
            assert e.get("copied_from") or (e["synthetic"] and e["kind"] == "synthetic_stress")
        for m in mems:
            if m["synthetic"]:
                assert m["kind"] == "synthetic_stress" and not m["verified"]
            else:
                assert m["kind"] in ("verified_result", "failure") and m["text"].startswith(("Verified", "Failed"))
        n_syn = sum(m["synthetic"] for m in mems)
        assert n_syn >= (fixtures.FLOOD_DISTRACTORS if name == "distractor_flood" else 12)
        assert sc["expected_evidence_ids"], name
        assert all(dbs.experiments.find_one({"_id": i}) or dbs.memories.find_one({"_id": i})
                   for i in sc["expected_evidence_ids"] + sc["forbidden_evidence_ids"])


def test_buried_best_eligible_sits_first(dbs):
    sc = fixtures.build_scenario(dbs, dbs, SRC, "buried_best_eligible", n_distractors=5)
    exps = list(dbs.experiments.find({"campaign_id": sc["campaign_id"]}).sort("created_at", 1))
    first = exps[0]
    assert first["_id"] == sc["expected_evidence_ids"][0]
    assert C.is_eligible(first["config"], sc["constraints"])
    eligible_done = [e for e in exps if e["status"] == "done" and C.is_eligible(e["config"], sc["constraints"])]
    assert first["result"]["val_balanced_accuracy"] == max(e["result"]["val_balanced_accuracy"] for e in eligible_done)
    camp = dbs.campaigns.find_one({"_id": sc["campaign_id"]})
    assert camp["goal_history"][-1]["constraints"] == sc["constraints"]
    # recent_window does not see the buried result; evidence does (as the incumbent)
    rw = context.build_packet(dbs, sc["campaign_id"], "recent_window")
    ev = context.build_packet(dbs, sc["campaign_id"], "evidence")
    assert not fixtures._in_packet(rw, sc["expected_evidence_ids"]) or len(exps) <= context.RECENT_BASELINE
    assert fixtures._in_packet(ev, sc["expected_evidence_ids"])


def test_obsolete_protocol_is_forbidden_and_excluded_from_incumbent(dbs):
    sc = fixtures.build_scenario(dbs, dbs, SRC, "obsolete_protocol", n_distractors=3)
    bad_id = sc["forbidden_evidence_ids"][0]
    bad = dbs.experiments.find_one({"_id": bad_id})
    assert bad["protocol_id"] != sc["protocol_id"] and bad["synthetic"]
    ev = context.build_packet(dbs, sc["campaign_id"], "evidence")
    assert ev["incumbent"]["experiment_id"] != bad_id
    rw = context.build_packet(dbs, sc["campaign_id"], "recent_window")
    assert any(r["experiment_id"] == bad_id for r in rw["recent"])  # the trap is visible to the baseline


def test_goal_changed_history(dbs):
    sc = fixtures.build_scenario(dbs, dbs, SRC, "goal_changed", n_distractors=2)
    camp = dbs.campaigns.find_one({"_id": sc["campaign_id"]})
    assert [h["constraints"]["max_channels"] for h in camp["goal_history"]] == [64, 21]
    assert camp["goal_version"] == 2 and camp["constraints"] == {"max_channels": 21}


def test_score():
    sc = {"expected_evidence_ids": ["e1", "m1"], "forbidden_evidence_ids": ["bad"],
          "constraints": {"max_channels": 21}, "avoid_family": {"method": "csp_lda", "band": "mu_8_12", "channels": "all64"}}
    packet = {"goal": {"constraints": {"max_channels": 21}}, "incumbent": {"experiment_id": "e1"},
              "pending": [], "recent": [], "retrieved": []}
    ok_cfg = {"method": "bandpower_lr", "band": "beta_13_30", "window": "w1.0_3.0", "channels": "motor21", "C": 1.0}
    r = {"action": "propose", "config": ok_cfg, "evidence_ids": ["m1"], "fallback_used": False,
         "usage": {"input_tokens": 1200, "cost_usd": 0.004, "source": "provider"}}
    s = fixtures.score(sc, packet, r)
    assert s == {"cited_expected": True, "cited_forbidden": False, "eligible": True, "fallback_used": False,
                 "input_tokens": 1200, "cost_usd": 0.004, "expected_in_packet": True, "repeated_bad_family": False}
    bad = {**r, "config": {**ok_cfg, "method": "csp_lda", "band": "mu_8_12", "channels": "all64", "n_components": 4},
           "evidence_ids": ["bad"]}
    s = fixtures.score(sc, packet, bad)
    assert s["cited_forbidden"] and not s["eligible"] and s["repeated_bad_family"] and not s["cited_expected"]
    stop = {"action": "stop", "config": None, "evidence_ids": [], "fallback_used": True, "usage": {}}
    assert fixtures.score(sc, packet, stop)["eligible"] is False
