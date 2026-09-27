"""Integration boundaries in a uniquely named disposable Atlas database."""
import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import main
from harness import store, hypotheses, control
from harness.context import assemble_packet
from harness.db import get_db
from harness.worker import Worker, fallback_plan
from tests.test_research import measurement, predictions

pytestmark = pytest.mark.integration


@pytest.fixture
def db():
    database = get_db("second_shift_research_test_" + uuid.uuid4().hex[:8])
    store.ensure_indexes(database)
    yield database
    database.client.drop_database(database.name)


def create(db, policy="research_v1"):
    protocol = {"fixture": 1, **({"validation_evidence_version": 1} if policy == "research_v1" else {})}
    cid = store.create_campaign(db, protocol=protocol, objective="test", max_channels=64,
                                max_experiments=10, policy=policy)
    return store.get_campaign(db, cid)


def queue(db, camp):
    packet = assemble_packet(camp, store.experiments(db, camp["_id"]))
    proposal = fallback_plan(packet, "test")
    eid, outcome = store.enqueue(db, camp, proposal["config"], proposal)
    assert outcome == "queued"
    return eid, proposal


def test_projection_recovers_result_commit_gap_once_and_rebuilds_ranking(db):
    camp = create(db)
    for _ in range(4):
        eid, proposal = queue(db, camp)
        job = store.claim_next(db, camp["_id"], "worker")
        assert store.commit_result(db, eid, job["lease"]["token"], measurement(predictions()))
    assert db.hypotheses.count_documents({}) == 0  # simulated crash before all projection writes
    before = assemble_packet(camp, store.experiments(db, camp["_id"]))["research"]
    hypotheses.reconcile(db, camp)
    first = list(db.hypotheses.find({}).sort("_id", 1))
    assert len(first) == 4 and all(h["status"] != "pending" for h in first)
    hypotheses.reconcile(db, camp)
    assert first == list(db.hypotheses.find({}).sort("_id", 1))
    assert before == assemble_packet(camp, store.experiments(db, camp["_id"]))["research"]


def test_current_goal_is_checked_at_acceptance_and_before_execution(db, monkeypatch):
    camp = create(db)
    eid, _ = queue(db, camp)
    # Pick an explicit legal 64-channel proposal to guarantee it becomes ineligible.
    from harness.contracts import all_configs
    cfg = next(c for c in all_configs() if c["channels"] == "all64")
    other, _ = store.enqueue(db, camp, cfg, {"model": "fixture"})
    db.experiments.update_one({"_id": eid}, {"$set": {"status": "failed"}})
    control.change_constraint(db, camp["_id"], 9, "test")
    assert store.enqueue(db, camp, cfg, {})[1] == "stale_goal"
    def must_not_run(*args):
        raise AssertionError("an ineligible job reached numerical execution")
    monkeypatch.setattr("harness.eeg.run_experiment", must_not_run)
    Worker(db, camp["_id"]).execute(camp)
    assert db.experiments.find_one({"_id": other})["status"] == "cancelled"


def test_protocol_evidence_version_and_commit_guard(db):
    with pytest.raises(ValueError, match="requires"):
        store.create_campaign(db, protocol={}, objective="test", max_channels=9, max_experiments=1,
                              policy="research_v1")
    camp = create(db)
    eid, _ = queue(db, camp)
    job = store.claim_next(db, camp["_id"], "worker")
    with pytest.raises(ValueError, match="version"):
        store.commit_result(db, eid, job["lease"]["token"], {"val_balanced_accuracy": 0.8})
    assert db.experiments.find_one({"_id": eid})["status"] == "running"


def test_hypotheses_endpoint_scoping_and_legacy_empty(db, monkeypatch):
    camp = create(db)
    eid, _ = queue(db, camp)
    hypotheses.reconcile(db, camp)
    legacy = create(db, "legacy")
    monkeypatch.setattr(main, "db", lambda: db)
    client = TestClient(main.app)
    own = client.get(f"/api/campaigns/{camp['_id']}/hypotheses")
    assert own.status_code == 200 and own.json()[0]["experiment_id"] == eid
    assert client.get(f"/api/campaigns/{legacy['_id']}/hypotheses").json() == []
    assert client.get("/api/campaigns/absent/hypotheses").status_code == 404
