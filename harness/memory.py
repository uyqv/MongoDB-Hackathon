"""Semantic memory: Voyage embeddings + Atlas Vector Search. OWNER: David.

embed(texts) -> list[list[float]]
ensure_vector_index(db) -> None
add_memory(db, *, campaign_id, protocol_id, kind, text, source_ids, verified, synthetic=False) -> str
search_memories(db, *, campaign_id, protocol_id, query, k=4, kinds=None) -> list[contracts.RetrievedMemory]
mark_obsolete(db, memory_ids) -> int
See docs/CONTRACTS.md.

Failure policy: if Voyage or vector search fails, add_memory still inserts with
embedding=None and search_memories falls back to an exact filtered find sorted
newest first (score=None, retrieval="fallback"). Nothing here raises into the worker.
"""
from __future__ import annotations

import logging
import os
import secrets
import time
from functools import lru_cache

from dotenv import load_dotenv
from pymongo.operations import SearchIndexModel

from harness import contracts as C
from harness.db import now_iso

load_dotenv()
log = logging.getLogger(__name__)

INDEX_NAME = "memories_vec"
FILTER_FIELDS = ("campaign_id", "protocol_id", "status", "kind", "synthetic")
EMBED_BATCH = 128

_client = None
_dim: int | None = None


def _voyage():
    global _client
    if _client is None:
        import voyageai
        # Retries with backoff: a Voyage key without a payment method is capped at 3 RPM / 10K TPM.
        _client = voyageai.Client(max_retries=int(os.environ.get("VOYAGE_MAX_RETRIES", "3")))
    return _client


def embed(texts: list[str], input_type: str = "document") -> list[list[float]]:
    model = os.environ.get("VOYAGE_MODEL", "voyage-3.5")
    out: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH):
        out += _voyage().embed(texts[i:i + EMBED_BATCH], model=model, input_type=input_type).embeddings
    return out


@lru_cache(maxsize=256)
def _embed_query(text: str) -> tuple[float, ...]:
    return tuple(embed([text], input_type="query")[0])


def embedding_dim() -> int:
    """Real dimension from one Voyage call, cached. Never hard-coded."""
    global _dim
    if _dim is None:
        _dim = len(embed(["dimension probe"])[0])
    return _dim


def _index_status(db) -> dict | None:
    for ix in db.memories.list_search_indexes(INDEX_NAME):
        return ix
    return None


def ensure_vector_index(db, wait_seconds: float = 180) -> None:
    """Create `memories_vec` once, then wait until it is queryable. Idempotent."""
    if "memories" not in db.list_collection_names():
        db.create_collection("memories")
    if _index_status(db) is None:
        fields = [{"type": "vector", "path": "embedding", "numDimensions": embedding_dim(), "similarity": "cosine"}]
        fields += [{"type": "filter", "path": f} for f in FILTER_FIELDS]
        db.memories.create_search_index(
            SearchIndexModel(definition={"fields": fields}, name=INDEX_NAME, type="vectorSearch"))
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        ix = _index_status(db)
        if ix and ix.get("queryable"):
            return
        time.sleep(2)
    log.warning("vector index %s not queryable after %ss; search will fall back", INDEX_NAME, wait_seconds)


def add_memory(db, *, campaign_id: str, protocol_id: str, kind: str, text: str, source_ids: list[str],
               verified: bool, synthetic: bool = False) -> str:
    if kind not in C.MEMORY_KINDS:
        raise ValueError(f"unknown memory kind {kind!r}")
    if verified and kind != "verified_result":
        raise ValueError("only verified_result memories can be verified")
    try:
        vec = embed([text])[0]
    except Exception as e:  # stored without embedding; exact-filter fallback still finds it
        log.warning("embed failed, storing memory without embedding: %s", e)
        vec = None
    doc = {
        "_id": "m_" + secrets.token_hex(6),
        "campaign_id": campaign_id, "protocol_id": protocol_id, "kind": kind, "text": text,
        "source_ids": list(source_ids), "verified": bool(verified), "status": "active",
        "synthetic": bool(synthetic), "embedding": vec, "created_at": now_iso(),
    }
    db.memories.insert_one(doc)
    return doc["_id"]


def add_memories(db, docs: list[dict]) -> list[str]:
    """Bulk variant for fixtures: one embed call per batch. Each dict has add_memory's kwargs."""
    texts = [d["text"] for d in docs]
    try:
        vecs = embed(texts)
    except Exception as e:
        log.warning("bulk embed failed, storing without embeddings: %s", e)
        vecs = [None] * len(docs)
    rows = []
    for d, vec in zip(docs, vecs):
        if d["kind"] not in C.MEMORY_KINDS:
            raise ValueError(f"unknown memory kind {d['kind']!r}")
        rows.append({
            "_id": "m_" + secrets.token_hex(6),
            "campaign_id": d["campaign_id"], "protocol_id": d["protocol_id"], "kind": d["kind"],
            "text": d["text"], "source_ids": list(d.get("source_ids", [])),
            "verified": bool(d.get("verified", False)) and d["kind"] == "verified_result",
            "status": "active", "synthetic": bool(d.get("synthetic", False)), "embedding": vec,
            "created_at": d.get("created_at") or now_iso(),
        })
    if rows:
        db.memories.insert_many(rows)
    return [r["_id"] for r in rows]


def _to_retrieved(doc: dict, score: float | None, retrieval: str) -> dict:
    return {
        "memory_id": doc["_id"], "kind": doc["kind"], "text": doc["text"],
        "source_ids": doc.get("source_ids", []), "score": score,
        "verified": bool(doc.get("verified")), "retrieval": retrieval,
    }


def search_memories(db, *, campaign_id: str, protocol_id: str, query: str, k: int = 4,
                    kinds: list[str] | None = None) -> list[dict]:
    flt: dict = {"campaign_id": campaign_id, "protocol_id": protocol_id, "status": "active"}
    if kinds:
        flt["kind"] = {"$in": list(kinds)}
    try:
        qvec = list(_embed_query(query))
        pipeline = [
            {"$vectorSearch": {"index": INDEX_NAME, "path": "embedding", "queryVector": qvec,
                               "numCandidates": max(100, k * 20), "limit": k, "filter": flt}},
            {"$project": {"embedding": 0, "score": {"$meta": "vectorSearchScore"}}},
        ]
        hits = list(db.memories.aggregate(pipeline))
        if hits:
            return [_to_retrieved(h, float(h["score"]), "vector") for h in hits]
    except Exception as e:
        log.warning("vector search failed, using filtered fallback: %s", e)
    docs = db.memories.find(flt, {"embedding": 0}).sort("created_at", -1).limit(k)
    return [_to_retrieved(d, None, "fallback") for d in docs]


def mark_obsolete(db, memory_ids: list[str]) -> int:
    if not memory_ids:
        return 0
    return db.memories.update_many({"_id": {"$in": list(memory_ids)}},
                                   {"$set": {"status": "obsolete"}}).modified_count
