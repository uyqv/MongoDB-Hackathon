"""Durable campaign state in Atlas. OWNER: Andrew.

create_campaign, ensure_indexes, enqueue (dedup by experiment _id; a done
duplicate is reused, not recomputed), claim_next (atomic, leased), commit_result
(fenced by lease token), fail_job, reclaim_expired_leases, eligible_results,
incumbent.
"""
