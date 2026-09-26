"""Operator controls the API calls. OWNER: David.

change_constraint(db, campaign_id, max_channels, reason) -> dict
reset_context(db, campaign_id) -> int
start_worker(campaign_id) -> int (pid)
kill_worker(campaign_id) -> bool
See docs/CONTRACTS.md for the exact writes.
"""
