import os
import secrets
import time

import pytest

from harness import memory

pytestmark = pytest.mark.integration


@pytest.fixture
def db():
    from harness.db import get_db
    name = os.environ.get("DB_NAME")
    assert name == "second_shift_david", f"memory tests only run against second_shift_david, got {name!r}"
    return get_db(name)


@pytest.fixture
def ids(db):
    tag = secrets.token_hex(4)
    out = {"a": f"camp_t{tag}a", "b": f"camp_t{tag}b", "p": "p_testproto01", "p2": "p_testproto02"}
    yield out
    db.memories.delete_many({"campaign_id": {"$in": [out["a"], out["b"]]}})


def test_fallback_when_embed_fails(db, ids, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("voyage down")
    monkeypatch.setattr(memory, "embed", boom)
    m1 = memory.add_memory(db, campaign_id=ids["a"], protocol_id=ids["p"], kind="failure",
                           text="older failure", source_ids=[], verified=False)
    time.sleep(0.01)
    m2 = memory.add_memory(db, campaign_id=ids["a"], protocol_id=ids["p"], kind="hypothesis",
                           text="newer hypothesis", source_ids=[], verified=False)
    memory.add_memory(db, campaign_id=ids["b"], protocol_id=ids["p"], kind="failure",
                      text="other campaign", source_ids=[], verified=False)
    assert db.memories.find_one({"_id": m1})["embedding"] is None
    hits = memory.search_memories(db, campaign_id=ids["a"], protocol_id=ids["p"], query="anything")
    assert [h["memory_id"] for h in hits] == [m2, m1]
    assert all(h["retrieval"] == "fallback" and h["score"] is None for h in hits)
    assert "embedding" not in hits[0]
    hits = memory.search_memories(db, campaign_id=ids["a"], protocol_id=ids["p"], query="x", kinds=["failure"])
    assert [h["memory_id"] for h in hits] == [m1]
    assert memory.mark_obsolete(db, [m1]) == 1
    hits = memory.search_memories(db, campaign_id=ids["a"], protocol_id=ids["p"], query="x")
    assert [h["memory_id"] for h in hits] == [m2]


def test_verified_only_for_verified_result(db, ids):
    with pytest.raises(ValueError):
        memory.add_memory(db, campaign_id=ids["a"], protocol_id=ids["p"], kind="failure",
                          text="x", source_ids=[], verified=True)


@pytest.mark.skipif(os.environ.get("LIVE") != "1", reason="live Voyage + Atlas vector search; set LIVE=1")
def test_live_vector_search_filters_and_ranks(db, ids):
    memory.ensure_vector_index(db)
    a, b, p, p2 = ids["a"], ids["b"], ids["p"], ids["p2"]
    # One bulk embed call: a free-tier Voyage key allows 3 requests/min.
    rows = [
        dict(campaign_id=a, protocol_id=p, kind="verified_result", verified=True, source_ids=["e1"],
             text="Verified result: csp_lda broad_8_30 band (8-30 Hz) central9 channels, n=4 -> val balanced accuracy 0.712."),
        dict(campaign_id=a, protocol_id=p, kind="failure", source_ids=["e2"],
             text="Failed experiment: bandpower_lr highbeta window w0.5_2.5 raised ValueError in fit."),
        dict(campaign_id=a, protocol_id=p, kind="synthetic_stress", synthetic=True, source_ids=[],
             text="Synthetic distractor: weather in Madison was cloudy on Tuesday."),
        dict(campaign_id=b, protocol_id=p, kind="verified_result", verified=True, source_ids=[],
             text="Verified result: csp_lda broad_8_30 band central9 0.9."),
        dict(campaign_id=a, protocol_id=p2, kind="verified_result", verified=True, source_ids=[],
             text="Verified result: csp_lda broad_8_30 band central9 0.95."),
    ]
    best, _, _, other_c, other_p = memory.add_memories(db, rows)
    assert db.memories.count_documents({"_id": {"$in": [best, other_c]}, "embedding": None}) == 0
    q = "best csp_lda result with broad 8-30 Hz band on central channels"
    hits = []
    for _ in range(30):  # vector index sync is eventually consistent
        hits = memory.search_memories(db, campaign_id=a, protocol_id=p, query=q, k=5)
        if len(hits) == 3 and all(h["retrieval"] == "vector" for h in hits):
            break
        time.sleep(3)
    got = [h["memory_id"] for h in hits]
    print("\nLIVE memory hits:", [(h["memory_id"], h["kind"], round(h["score"] or 0, 3), h["retrieval"]) for h in hits])
    assert all(h["retrieval"] == "vector" for h in hits)
    assert other_c not in got and other_p not in got
    assert len(got) == 3 and got[0] == best
