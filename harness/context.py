"""Bounded context reconstruction. OWNER: Andrew.

build_packet(db, campaign_id, strategy="evidence" | "recent_window", budget_tokens=4000)
    -> contracts.EvidencePacket, and writes a copy to the `packets` collection.

evidence: latest goal + constraints, incumbent eligible result, pending jobs,
small recent window, and a few memories.search_memories() hits (filtered by
campaign/protocol/status before vector ranking).
recent_window: the same goal block plus the last N experiments only. Baseline arm.
"""


def build_packet(db, campaign_id: str, strategy: str = "evidence", budget_tokens: int = 4000) -> dict:
    raise NotImplementedError
