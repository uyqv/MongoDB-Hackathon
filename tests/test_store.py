"""Store tests against a throwaway database on the real Atlas cluster."""
import os

import pytest

from harness import store
from harness.db import get_db

pytestmark = pytest.mark.skipif(not os.environ.get("MONGODB_URI") and not os.path.exists(".env"),
                                reason="needs Atlas")

CSP9 = {"method": "csp_lda", "band": "broad_8_30", "window": "w1.0_3.0", "channels": "central9", "n_components": 4}
CSP64 = {**CSP9, "channels": "all64"}
RESULT = {"val_balanced_accuracy": 0.8, "val_f1": 0.79, "n_train": 75, "n_val": 75, "n_channels": 9,
          "fit_seconds": 0.1, "evaluator_version": "eeg-eval-1"}


@pytest.fixture
def db():
    d = get_db("second_shift_test_andrew")
    for c in ("campaigns", "experiments", "events", "memories", "packets"):
        d[c].delete_many({})
    yield d
    d.client.drop_database("second_shift_test_andrew")


def _campaign(db, max_channels=64):
    cid = store.create_campaign(db, protocol={"v": 1}, objective="test", max_channels=max_channels,
                                max_experiments=10)
    return store.get_campaign(db, cid)


def test_dedup_claim_fence_and_reuse(db):
    camp = _campaign(db)
    eid, outcome = store.enqueue(db, camp, CSP9, {"model": "test"})
    assert outcome == "queued"
    assert store.enqueue(db, camp, {**CSP9, "C": 1.0}, {"model": "test"}) == (eid, "queued")  # unused param
    job = store.claim_next(db, camp["_id"], "w1")
    assert job["_id"] == eid and job["attempt"] == 1
    assert store.claim_next(db, camp["_id"], "w1") is None
    assert not store.commit_result(db, eid, "wrong-token", RESULT)
    assert store.commit_result(db, eid, job["lease"]["token"], RESULT)
    assert store.enqueue(db, camp, CSP9, {"model": "test"}) == (eid, "reused")
    assert store.budget_used(db, camp["_id"]) == 1


def test_expired_lease_reclaimed_and_old_attempt_fenced(db):
    camp = _campaign(db)
    eid, _ = store.enqueue(db, camp, CSP9, {"model": "test"})
    first = store.claim_next(db, camp["_id"], "dead-worker")
    db.experiments.update_one({"_id": eid}, {"$set": {"lease.expires_at": "2000-01-01T00:00:00.000+00:00"}})
    assert store.reclaim_expired(db, camp["_id"], "w2") == [eid]
    second = store.claim_next(db, camp["_id"], "w2")
    assert second["attempt"] == 2
    assert not store.commit_result(db, eid, first["lease"]["token"], RESULT)   # zombie attempt rejected
    assert store.commit_result(db, eid, second["lease"]["token"], RESULT)


def test_incumbent_follows_current_constraint(db):
    camp = _campaign(db, max_channels=64)
    for cfg, acc in ((CSP64, 0.9), (CSP9, 0.8)):
        eid, _ = store.enqueue(db, camp, cfg, {"model": "test"})
        job = store.claim_next(db, camp["_id"], "w1")
        store.commit_result(db, eid, job["lease"]["token"], {**RESULT, "val_balanced_accuracy": acc})
    assert store.incumbent(db, camp)["config"]["channels"] == "all64"
    db.campaigns.update_one({"_id": camp["_id"]}, {"$set": {"constraints": {"max_channels": 9}}})
    camp = store.get_campaign(db, camp["_id"])
    assert store.incumbent(db, camp)["config"]["channels"] == "central9"
    assert len(store.eligible_done(db, camp)) == 1


def test_test_set_scored_once(db):
    camp = _campaign(db)
    assert store.begin_finalize(db, camp["_id"], "w1")
    assert not store.begin_finalize(db, camp["_id"], "w2")
