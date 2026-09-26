"""STRETCH, optional. Jev note routing via OpenRouter Decisions API. OWNER: David.

route_note(text) -> {"label": "failure_memory"|"research_note"|"ignore"|"review",
                     "provider", "model", "request_id", "usage", "fallback_used", "fallback_reason"}
Never computes scores, compares numbers, or certifies a result.
"""
