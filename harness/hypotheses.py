"""Idempotent projections of pre-execution claims and committed trial evidence."""
from __future__ import annotations

from harness.db import now_iso
from harness.uncertainty import THRESHOLD, summarize, validate_result


def register(db, campaign, experiment):
    proposal = experiment.get("proposed_by") or {}
    claim = proposal.get("hypothesis")
    if not claim:
        return
    eid = experiment["_id"]
    db.hypotheses.update_one({"_id": "h_" + eid}, {"$setOnInsert": {
        "campaign_id": campaign["_id"], "protocol_id": experiment["protocol_id"],
        "experiment_id": eid, "candidate_id": proposal["candidate_id"],
        "packet_id": proposal.get("packet_id"), "policy_version": "research_v1",
        "goal_version": experiment["goal_version_at_proposal"], **claim,
        "rationale": proposal.get("rationale", ""), "evidence_ids": proposal.get("evidence_ids", []),
        "claim": "Candidate improves reference validation balanced accuracy by at least 0.02"
                 if claim["kind"] == "comparison" else "Seeded or unreferenced exploration",
        "status": "pending", "created_at": experiment["created_at"],
        "scope": "specific_configuration_pair_exploratory_validation",
    }}, upsert=True)


def assessment(experiment, reference):
    if experiment["status"] in ("failed", "cancelled"):
        return {"status": "execution_failed" if experiment["status"] == "failed" else "cancelled",
                "reason": experiment.get("error")}
    claim = experiment["proposed_by"]["hypothesis"]
    if claim["kind"] == "exploration":
        return {"status": "exploration", "comparison": None}
    try:
        if (not reference or reference["protocol_id"] != experiment["protocol_id"]
                or reference["campaign_id"] != experiment["campaign_id"] or reference["status"] != "done"):
            raise ValueError("missing or incompatible reference experiment")
        comparison = summarize(validate_result(experiment["result"]), validate_result(reference["result"]))
        status = "inconclusive"
        if comparison["available"]:
            lower, upper = comparison["interval"]
            if lower > THRESHOLD + 1e-12:
                status = "supported_on_validation"
            elif upper < THRESHOLD - 1e-12:
                status = "contradicted_on_validation"
        return {"status": status, "comparison": comparison}
    except (ValueError, KeyError, TypeError) as exc:
        return {"status": "inconclusive", "comparison": None, "reason": str(exc)}


def reconcile(db, campaign):
    """The experiment's durable proposal is authoritative even if registration crashed."""
    for exp in db.experiments.find({"campaign_id": campaign["_id"], "protocol_id": campaign["protocol_id"]}):
        if not (exp.get("proposed_by") or {}).get("hypothesis"):
            continue
        register(db, campaign, exp)
        if exp["status"] not in ("done", "failed", "cancelled"):
            continue
        reference_id = exp["proposed_by"]["hypothesis"].get("reference_experiment_id")
        reference = db.experiments.find_one({"_id": reference_id, "campaign_id": campaign["_id"],
                                            "protocol_id": campaign["protocol_id"]}) if reference_id else None
        db.hypotheses.update_one({"_id": "h_" + exp["_id"], "status": "pending"},
                                 {"$set": {**assessment(exp, reference), "assessed_at": now_iso()}})
