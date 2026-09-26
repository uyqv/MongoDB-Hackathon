"""Semantic memory: Voyage embeddings + Atlas Vector Search. OWNER: David.

embed(texts) -> list[list[float]]
ensure_vector_index(db) -> None
add_memory(db, *, campaign_id, protocol_id, kind, text, source_ids, verified, synthetic=False) -> str
search_memories(db, *, campaign_id, protocol_id, query, k=4, kinds=None) -> list[contracts.RetrievedMemory]
mark_obsolete(db, memory_ids) -> int
See docs/CONTRACTS.md.
"""
