import os

import pytest
from fastapi.testclient import TestClient

from api.main import app
from eval import seed_fake
from harness import contracts as C

CID = seed_fake.CAMPAIGN_ID


@pytest.fixture(scope="module")
def client():
    assert os.environ.get("DB_NAME") == "second_shift_david", "API tests only run against second_shift_david"
    seed_fake.main()
    return TestClient(app)


def _no_embedding(obj):
    if isinstance(obj, dict):
        assert "embedding" not in obj
        for v in obj.values():
            _no_embedding(v)
    elif isinstance(obj, list):
        for v in obj:
            _no_embedding(v)


def test_index_and_static(client):
    assert client.get("/").status_code == 200
    assert "Second Shift" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200


def test_health(client):
    assert client.get("/api/health").json() == {"ok": True, "db": "second_shift_david"}


def test_campaign_list_and_detail(client):
    lst = client.get("/api/campaigns").json()
    assert any(c["_id"] == CID for c in lst)
    c = client.get(f"/api/campaigns/{CID}").json()
    assert c["goal_version"] == 2 and c["constraints"] == {"max_channels": 9}
    assert c["used"] == 8 and c["remaining"] == 2
    exps = client.get(f"/api/campaigns/{CID}/experiments").json()
    eligible_done = [e for e in exps if e["status"] == "done" and e["eligible"]]
    best = max(eligible_done, key=lambda e: e["result"]["val_balanced_accuracy"])
    assert c["incumbent"]["experiment_id"] == best["_id"]
    assert C.is_eligible(c["incumbent"]["config"], c["constraints"])
    assert client.get("/api/campaigns/camp_nope0000").status_code == 404


def test_experiments_eligibility_and_reuse(client):
    exps = client.get(f"/api/campaigns/{CID}/experiments").json()
    assert len(exps) == 8
    assert [e["created_at"] for e in exps] == sorted(e["created_at"] for e in exps)
    for e in exps:
        assert e["eligible"] == (C.CHANNEL_COUNTS[e["config"]["channels"]] <= 9)
    assert any(not e["eligible"] for e in exps)
    assert sum(e["reused"] for e in exps) == 1


def test_events_ordering_and_after(client):
    evs = client.get(f"/api/campaigns/{CID}/events").json()
    ts = [e["ts"] for e in evs]
    assert ts == sorted(ts) and len(evs) == 31
    assert all(isinstance(e["_id"], str) for e in evs)
    later = client.get(f"/api/campaigns/{CID}/events", params={"after": ts[10]}).json()
    assert [e["ts"] for e in later] == ts[11:]
    last5 = client.get(f"/api/campaigns/{CID}/events", params={"limit": 5}).json()
    assert [e["ts"] for e in last5] == ts[-5:]


def test_packet_and_memories_never_embedding(client):
    p = client.get(f"/api/campaigns/{CID}/packets/latest").json()
    assert p["strategy"] == "evidence" and p["retrieved"]
    assert client.get(f"/api/campaigns/{CID}/packets/latest", params={"strategy": "recent_window"}).status_code == 404
    mems = client.get(f"/api/campaigns/{CID}/memories").json()
    assert len(mems) == 4 and not any(m["synthetic"] for m in mems)
    all_mems = client.get(f"/api/campaigns/{CID}/memories", params={"include_synthetic": True}).json()
    assert len(all_mems) == 6
    only = client.get(f"/api/campaigns/{CID}/memories", params={"kind": "verified_result"}).json()
    assert {m["kind"] for m in only} == {"verified_result"}
    for body in (p, mems, all_mems):
        _no_embedding(body)




# ------------------------------------------------------------------ D5: control.py + POST endpoints
# control.py tests live here because CONTRACTS §1 gives David no test_control.py.

import sys
import time

from harness import control
from harness.db import get_db


@pytest.fixture
def camp():
    d = get_db()
    assert d.name == "second_shift_david"
    cid = "camp_c0ffee" + os.urandom(1).hex()
    d.campaigns.insert_one({"_id": cid, "objective": "control test", "goal_version": 1,
                            "constraints": {"max_channels": 64},
                            "goal_history": [{"version": 1, "constraints": {"max_channels": 64},
                                              "changed_at": "2026-09-26T00:00:00Z", "reason": "initial goal"}],
                            "protocol_id": "p_test", "budget": {"max_experiments": 10}, "state": "PLAN",
                            "context_epoch": 0, "final": None, "created_at": "2026-09-26T00:00:00Z", "fake": True})
    yield cid
    d.campaigns.delete_one({"_id": cid})
    d.events.delete_many({"campaign_id": cid})


def test_change_constraint(camp):
    d = get_db()
    after = control.change_constraint(d, camp, 9, "headset budget cut")
    assert after["goal_version"] == 2 and after["constraints"] == {"max_channels": 9}
    assert after["goal_history"][-1]["version"] == 2 and after["goal_history"][-1]["reason"] == "headset budget cut"
    ev = d.events.find_one({"campaign_id": camp, "type": "goal_changed"})
    assert ev["payload"]["from_version"] == 1 and ev["payload"]["to_version"] == 2
    assert ev["payload"]["old_constraints"] == {"max_channels": 64}
    with pytest.raises(ValueError):
        control.change_constraint(d, camp, 32, "no")


def test_reset_context(camp):
    d = get_db()
    assert control.reset_context(d, camp) == 1
    assert control.reset_context(d, camp) == 2
    assert d.events.count_documents({"campaign_id": camp, "type": "context_reset"}) == 2


def test_start_kill_status_on_dummy_process(camp, tmp_path, monkeypatch):
    monkeypatch.setattr(control, "RUN_DIR", tmp_path)
    monkeypatch.setattr(control, "worker_cmd", lambda cid: [sys.executable, "-c", "import time; time.sleep(60)"])
    assert control.worker_status()["running"] is False
    pid = control.start_worker(camp)
    st = control.worker_status()
    assert st == {**st, "running": True, "pid": pid, "campaign_id": camp}
    with pytest.raises(RuntimeError):
        control.start_worker(camp)
    out = control.kill_worker()
    assert out == {"killed": True, "pid": pid}
    assert control.worker_status()["running"] is False
    ev = get_db().events.find_one({"campaign_id": camp, "type": "worker_killed"})
    assert ev["payload"] == {"pid": pid, "signal": "SIGKILL"}
    assert control.kill_worker()["killed"] is False


def test_control_endpoints(client, camp, tmp_path, monkeypatch):
    monkeypatch.setattr(control, "RUN_DIR", tmp_path)
    monkeypatch.setattr(control, "worker_cmd", lambda cid: [sys.executable, "-c", "import time; time.sleep(60)"])
    r = client.post(f"/api/campaigns/{camp}/constraint", json={"max_channels": 21, "reason": "ui test"})
    assert r.status_code == 200 and r.json()["constraints"] == {"max_channels": 21}
    assert client.post(f"/api/campaigns/{camp}/constraint", json={"max_channels": 5, "reason": ""}).status_code == 400
    assert client.post(f"/api/campaigns/{camp}/context-reset").json() == {"context_epoch": 1}
    assert client.post("/api/campaigns/camp_nope0000/context-reset").status_code == 404
    pid = client.post("/api/worker/start", json={"campaign_id": camp}).json()["pid"]
    assert client.get("/api/worker/status").json()["running"] is True
    assert client.post("/api/worker/start", json={"campaign_id": camp}).status_code == 409
    assert client.post("/api/worker/kill").json() == {"killed": True, "pid": pid}
    assert client.get("/api/worker/status").json()["running"] is False
