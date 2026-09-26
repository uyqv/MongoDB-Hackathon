import json
import os
from types import SimpleNamespace as NS

import pytest

from harness import contracts as C
from harness import planner

PID = C.protocol_id({"test": True})
INC_CFG = {"method": "csp_lda", "band": "broad_8_30", "window": "w1.0_3.0", "channels": "central9", "n_components": 4}
NEW_CFG = {"method": "csp_lda", "band": "mu_8_12", "window": "w1.0_3.0", "channels": "central9", "n_components": 2}
BIG_CFG = {"method": "csp_lda", "band": "mu_8_12", "window": "w1.0_3.0", "channels": "all64", "n_components": 2}


def make_packet(max_channels=9, tried=(INC_CFG,)):
    inc_id = C.experiment_doc_id("camp_test0001", C.experiment_key(PID, INC_CFG))
    return {
        "campaign_id": "camp_test0001", "protocol_id": PID, "strategy": "evidence",
        "goal": {"objective": "test", "goal_version": 1, "constraints": {"max_channels": max_channels},
                 "budget": {"max_experiments": 10, "used": len(tried), "remaining": 10 - len(tried)}},
        "incumbent": {"experiment_id": inc_id, "label": C.config_label(INC_CFG), "config": INC_CFG,
                      "val_balanced_accuracy": 0.61},
        "pending": [], "recent": [],
        "retrieved": [{"memory_id": "m_000000000001", "kind": "verified_result", "text": "x",
                       "source_ids": [inc_id], "score": 0.9, "verified": True, "retrieval": "vector"}],
        "tried_keys": [C.experiment_key(PID, c) for c in tried],
        "surface": C.surface_summary(), "token_estimate": 100, "budget_tokens": 4000,
    }


def tool_resp(name, args, i=0):
    call = NS(id=f"call_{i}", type="function", function=NS(name=name, arguments=json.dumps(args)))
    return NS(id=f"gen-{i}", model="anthropic/claude-sonnet-5",
              choices=[NS(message=NS(content="", tool_calls=[call]))],
              usage=NS(prompt_tokens=1000, completion_tokens=50, cost=0.004, model_extra={}))


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **kw):
        self.calls.append(kw)
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


@pytest.fixture
def fake(monkeypatch):
    def install(*responses):
        client = FakeClient(responses)
        monkeypatch.setattr(planner, "client_factory", lambda: client)
        return client
    return install


def propose(cfg, ev=()):
    return {"config": cfg, "rationale": "Try mu band.", "evidence_ids": list(ev)}


def test_valid_proposal_accepted(fake):
    p = make_packet()
    client = fake(tool_resp("propose_experiment", propose(NEW_CFG, [p["incumbent"]["experiment_id"]])))
    r = planner.plan(p)
    assert r["action"] == "propose" and r["config"] == C.normalize_config(NEW_CFG)
    assert not r["fallback_used"] and r["request_id"] == "gen-0"
    assert r["usage"] == {"input_tokens": 1000, "output_tokens": 50, "cost_usd": 0.004, "source": "provider"}
    assert len(client.calls) == 1
    assert client.calls[0]["tool_choice"] == "required"
    assert client.calls[0]["extra_body"] == {"usage": {"include": True}}


def test_invalid_config_repaired(fake):
    bad = {**NEW_CFG, "band": "gamma"}
    client = fake(tool_resp("propose_experiment", propose(bad), 0),
                  tool_resp("propose_experiment", propose(NEW_CFG), 1))
    r = planner.plan(make_packet())
    assert r["action"] == "propose" and not r["fallback_used"]
    assert len(client.calls) == 2
    repair = client.calls[1]["messages"][-1]
    assert repair["role"] == "tool" and "outside the allowed surface" in repair["content"]
    assert r["usage"]["input_tokens"] == 2000 and r["usage"]["cost_usd"] == pytest.approx(0.008)


def test_repeat_of_tried_key_falls_back(fake):
    client = fake(tool_resp("propose_experiment", propose(INC_CFG), 0),
                  tool_resp("propose_experiment", propose(INC_CFG), 1))
    p = make_packet()
    r = planner.plan(p)
    assert r["fallback_used"] and "already tried" in r["fallback_reason"]
    assert r["model"] == planner.FALLBACK_MODEL
    assert C.is_eligible(r["config"], p["goal"]["constraints"])
    assert C.experiment_key(PID, r["config"]) not in p["tried_keys"]
    assert r["config"] == planner.fallback_config(p)
    assert len(client.calls) == 2


def test_ineligible_rejected():
    cfg, err = planner.validate(make_packet(9), "propose_experiment", propose(BIG_CFG))
    assert cfg is None and "max_channels=9" in err
    cfg, err = planner.validate(make_packet(64), "propose_experiment", propose(BIG_CFG))
    assert err is None


def test_unknown_evidence_id_rejected(fake):
    p = make_packet()
    cfg, err = planner.validate(p, "propose_experiment", propose(NEW_CFG, ["m_made_up"]))
    assert err and "m_made_up" in err
    # source_ids of retrieved memories and memory ids are both citable
    cfg, err = planner.validate(p, "propose_experiment", propose(NEW_CFG, ["m_000000000001"]))
    assert err is None


def test_zero_evidence_ids_valid():
    cfg, err = planner.validate(make_packet(), "propose_experiment", propose(NEW_CFG, []))
    assert err is None and cfg


def test_nothing_left_stops_without_call(fake):
    eligible = [c for c in C.all_configs() if C.is_eligible(c, {"max_channels": 9})]
    client = fake()
    r = planner.plan(make_packet(9, tried=eligible))
    assert r["action"] == "stop" and r["config"] is None
    assert client.calls == []


def test_provider_error_falls_back(fake):
    fake(RuntimeError("boom"))
    r = planner.plan(make_packet())
    assert r["fallback_used"] and "boom" in r["fallback_reason"]
    assert r["usage"]["source"] == "estimate"


def test_premature_stop_repaired_into_proposal(fake):
    client = fake(tool_resp("stop", {"rationale": "nothing beats the incumbent", "evidence_ids": []}, 0),
                  tool_resp("propose_experiment", propose(NEW_CFG), 1))
    r = planner.plan(make_packet())
    assert r["action"] == "propose" and not r["fallback_used"]
    assert "stop is not allowed" in client.calls[1]["messages"][-1]["content"]
    assert "different method, band, or window" in client.calls[1]["messages"][-1]["content"]


def test_repeated_premature_stop_falls_back_to_proposal(fake):
    fake(tool_resp("stop", {"rationale": "done", "evidence_ids": []}, 0),
         tool_resp("stop", {"rationale": "still done", "evidence_ids": []}, 1))
    r = planner.plan(make_packet())
    assert r["action"] == "propose" and r["fallback_used"] and "stop is not allowed" in r["fallback_reason"]


def test_stop_accepted_when_budget_spent():
    p = make_packet()
    p["goal"]["budget"]["remaining"] = 0
    assert planner.validate(p, "stop", {"rationale": "budget spent", "evidence_ids": []}) == (None, None)


def test_budget_spent_stops_without_call(fake):
    client = fake()
    p = make_packet()
    p["goal"]["budget"]["remaining"] = 0
    r = planner.plan(p)
    assert r["action"] == "stop" and client.calls == []


def test_user_message_sends_every_field_but_tried_keys_and_packet_id(fake):
    p = make_packet()
    lead = {"experiment_id": "camp_test0001:x_lead", "label": "lead", "status": "done",
            "val_balanced_accuracy": 0.7, "eligible": True}
    lag = {"experiment_id": "camp_test0001:x_lag", "label": "lag", "status": "failed",
           "val_balanced_accuracy": None, "eligible": True}
    p.update(packet_id="pk_000000000001", tried=[C.config_label(INC_CFG)], leaders=[lead], laggards=[lag])
    client = fake(tool_resp("propose_experiment", propose(NEW_CFG, ["camp_test0001:x_lead", "camp_test0001:x_lag"])))
    r = planner.plan(p)
    user = client.calls[0]["messages"][1]["content"]
    sent = json.loads(user.split("\n", 1)[1])
    assert set(sent) == set(p) - {"tried_keys", "packet_id"}
    assert sent["tried"] == [C.config_label(INC_CFG)] and sent["leaders"] == [lead] and sent["laggards"] == [lag]
    assert "tried_keys" not in user and "pk_000000000001" not in user
    # leaders and laggards are citable evidence
    assert r["action"] == "propose" and not r["fallback_used"]


def test_system_prompt_points_at_tried():
    assert "Every tried config is listed in tried; never propose one of those." in planner.SYSTEM_PROMPT
    assert "Tried configs appear in incumbent, pending and recent" not in planner.SYSTEM_PROMPT


def test_system_prompt_forbids_early_stop():
    assert "ONLY valid when goal.budget.remaining is 0" in planner.SYSTEM_PROMPT


@pytest.mark.skipif(os.environ.get("LIVE") != "1", reason="live OpenRouter call; set LIVE=1")
def test_live_planner():
    p = make_packet()
    r = planner.plan(p)
    print("\nLIVE planner:", json.dumps({k: r[k] for k in
          ("action", "model", "request_id", "usage", "fallback_used", "fallback_reason", "evidence_ids")}))
    assert r["action"] in ("propose", "stop")
    assert not r["fallback_used"], r["fallback_reason"]
    assert r["usage"]["source"] == "provider"
    if r["action"] == "propose":
        cfg, err = planner.validate(p, "propose_experiment", {"config": r["config"], "evidence_ids": r["evidence_ids"]})
        assert err is None
