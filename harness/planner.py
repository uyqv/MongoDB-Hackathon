"""LLM planner over OpenRouter. OWNER: David.

plan(packet, *, model=None) -> contracts.PlannerResult

The model chooses an allowed config + rationale citing evidence ids from the
packet. It never computes or reports metrics. See docs/CONTRACTS.md.
"""


def plan(packet: dict, *, model: str | None = None) -> dict:
    raise NotImplementedError
