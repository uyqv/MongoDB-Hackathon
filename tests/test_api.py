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


def test_controls_stubbed(client):
    assert client.post("/api/worker/kill").status_code == 501
    assert client.get("/api/eeg/preview").status_code == 501
