"""Ablation scenarios (buried evidence, obsolete protocol, distractors). OWNER: David.

Every generated record is labeled synthetic=True / kind="synthetic_stress" unless it
is a copy of a real experiment. See docs/CONTRACTS.md §8.

    python -m eval.fixtures --src-campaign <id> [--src-db second_shift] [--dst-db second_shift_eval] [--reset]

Builds all 5 scenarios from a REAL source campaign (read only) into dst_db and
writes eval/scenarios.json for eval/run_ablation.py. score() is pure code.

What a scenario contains:
- copies of the source campaign's finished experiments (done/failed), re-keyed to
  the new campaign id, with `copied_from` pointing at the real doc. Results are
  untouched; only created_at is reordered so the evidence under test sits early.
- a verified_result / failure memory per copy, re-rendered by contracts code with
  the new ids and embedded through harness.memory (never written by a model).
- injected records, all `synthetic: True, kind: "synthetic_stress"`.
"""
from __future__ import annotations

import argparse
import json
import random
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from harness import contracts as C
from harness import memory

SCENARIOS = ("buried_best_eligible", "buried_failure", "obsolete_protocol", "goal_changed", "distractor_flood")
FLOOD_DISTRACTORS = 1000

# Distractor vocabulary: plausible research chatter with NO measured results in it.
_TOPICS = [
    "Considered a {band} band sweep with {win} windows on {ch} channels; not run.",
    "Reading note: {method} is common for motor imagery, but depends on subject and montage.",
    "Idea: try {ch} with {method} and {band}; no evidence either way yet.",
    "Reminder: epochs are cut {win} after the cue; keep windows inside the task period.",
    "Synthetic stress note {i}: unrelated lab chatter about headset comfort and gel impedance.",
    "Synthetic stress note {i}: preprocessing checklist, notch filter at 60 Hz, re-reference to average.",
    "Open question: does {band} carry more discriminative power than mu for feet imagery?",
    "Synthetic stress note {i}: cluster maintenance window moved to Sunday.",
]


def _iso(t: datetime) -> str:
    return t.isoformat(timespec="milliseconds")


def _new_cid() -> str:
    return "camp_" + secrets.token_hex(4)


def _distractor_texts(n: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    out = []
    for i in range(n):
        tpl = rng.choice(_TOPICS)
        out.append("SYNTHETIC distractor. " + tpl.format(
            i=i, band=rng.choice(list(C.BANDS)), win=rng.choice(list(C.WINDOWS)),
            ch=rng.choice(list(C.CHANNEL_SETS)), method=rng.choice(list(C.METHODS))))
    return out


def _acc(e: dict) -> float:
    return (e.get("result") or {}).get("val_balanced_accuracy", -1.0)


def _family(cfg: dict) -> dict:
    """Method + band + channel set. Narrow on purpose: real campaigns often share method and band."""
    return {"method": cfg["method"], "band": cfg["band"], "channels": cfg["channels"]}


def _best_eligible(exps: list[dict], constraints: dict) -> dict | None:
    ok = [e for e in exps if e["status"] == "done" and C.is_eligible(e["config"], constraints)]
    return max(ok, key=_acc, default=None)


def build_scenario(src_db, dst_db, src_campaign_id: str, name: str, *, n_distractors: int = 200,
                   seed: int = 0) -> dict:
    if name not in SCENARIOS:
        raise ValueError(f"unknown scenario {name!r}; one of {SCENARIOS}")
    src = src_db.campaigns.find_one({"_id": src_campaign_id})
    if src is None:
        raise KeyError(f"no source campaign {src_campaign_id} in {src_db.name}")
    real = [e for e in src_db.experiments.find({"campaign_id": src_campaign_id, "protocol_id": src["protocol_id"],
                                                "status": {"$in": ["done", "failed"]}}).sort("created_at", 1)]
    if not real:
        raise ValueError(f"source campaign {src_campaign_id} has no finished experiments")
    if name == "distractor_flood":
        n_distractors = max(n_distractors, FLOOD_DISTRACTORS)

    pid = src["protocol_id"]
    cid = _new_cid()
    goal_history = [{"version": 1, "constraints": {"max_channels": 64}, "changed_at": src["created_at"],
                     "reason": "initial goal (fixture)"}]
    constraints = {"max_channels": 64}
    description = ""
    front: dict | None = None          # the real experiment that must sit early
    forbidden_exp: dict | None = None  # injected obsolete-protocol experiment
    avoid_family: dict | None = None

    if name == "buried_best_eligible":
        for mc in (9, 21):
            front = _best_eligible(real, {"max_channels": mc})
            if front:
                constraints = {"max_channels": mc}
                break
        if front is None:
            raise ValueError("no done 9- or 21-channel result in the source campaign")
        description = (f"Constraint lowered to {constraints['max_channels']} channels. The best eligible result "
                       f"sits first, followed by {n_distractors} synthetic notes and every later experiment.")
    elif name == "buried_failure":
        failed = [e for e in real if e["status"] == "failed"]
        front = failed[0] if failed else min((e for e in real if e["status"] == "done"), key=_acc)
        avoid_family = _family(front["config"])
        description = (f"A real {'failed' if failed else 'worst-scoring'} config ({front['label']}) sits first and "
                       f"is buried under {n_distractors} synthetic notes. Correct move: avoid its "
                       f"{avoid_family['method']} · {avoid_family['band']} · {avoid_family['channels']} family.")
    elif name == "goal_changed":
        constraints = {"max_channels": 21}
        description = "History crosses a 64 -> 21 channel change. The proposal must be eligible under 21."
    elif name == "obsolete_protocol":
        description = ("A SYNTHETIC higher-scoring record under a different protocol_id is the most recent "
                       "experiment. Citing it is a mistake.")
    elif name == "distractor_flood":
        description = f"{n_distractors} synthetic notes flood memory. Correct move: retrieve the real incumbent."

    if name == "goal_changed":
        goal_history.append({"version": 2, "constraints": constraints, "changed_at": _iso(datetime.now(timezone.utc)),
                             "reason": "fixture: channel budget cut to 21"})
    elif constraints["max_channels"] != 64:
        goal_history.append({"version": 2, "constraints": constraints, "changed_at": _iso(datetime.now(timezone.utc)),
                             "reason": f"fixture: channel budget cut to {constraints['max_channels']}"})

    # ---- ordering: `front` first, then distractor notes, then the other real experiments
    t = datetime.now(timezone.utc) - timedelta(hours=2)
    ordered = ([front] if front else []) + [e for e in real if front is None or e["_id"] != front["_id"]]

    def tick(seconds: float = 1.0) -> str:
        nonlocal t
        t += timedelta(seconds=seconds)
        return _iso(t)

    copies, mem_rows = [], []
    distractors = _distractor_texts(n_distractors, seed)
    fixture_tag = {"fixture": True, "scenario": name}

    def copy_exp(e: dict) -> dict:
        key = C.experiment_key(pid, e["config"])
        created = tick(30)
        doc = {**{k: v for k, v in e.items() if k not in ("_id", "lease")},
               "_id": C.experiment_doc_id(cid, key), "key": key, "campaign_id": cid, "lease": None,
               "created_at": created, "finished_at": created, "copied_from": e["_id"], **fixture_tag}
        copies.append(doc)
        done = doc["status"] == "done"
        mem_rows.append(dict(
            campaign_id=cid, protocol_id=pid, kind="verified_result" if done else "failure",
            text=C.render_result_text(doc) if done else C.render_failure_text(doc),
            source_ids=[doc["_id"]], verified=done, created_at=tick(), extra=fixture_tag))
        return doc

    front_copy = copy_exp(ordered[0]) if front else None
    for text in distractors:
        mem_rows.append(dict(campaign_id=cid, protocol_id=pid, kind="synthetic_stress", text=text, source_ids=[],
                             verified=False, synthetic=True, created_at=tick(0.1), extra=fixture_tag))
    for e in ordered[1:] if front else ordered:
        copy_exp(e)

    if name == "obsolete_protocol":
        inc = _best_eligible(real, constraints)
        old_protocol = {**src["protocol"], "fixture_obsolete": True, "evaluator_version": "eeg-eval-0"}
        old_pid = C.protocol_id(old_protocol)
        key = C.experiment_key(old_pid, inc["config"])
        boosted = min(0.99, round(_acc(inc) + 0.12, 4))
        created = tick(30)
        forbidden_exp = {
            **{k: v for k, v in inc.items() if k not in ("_id", "lease")},
            "_id": C.experiment_doc_id(cid, key), "key": key, "campaign_id": cid, "protocol_id": old_pid,
            "label": "SYNTHETIC obsolete protocol · " + inc["label"], "lease": None,
            "result": {**inc["result"], "val_balanced_accuracy": boosted, "evaluator_version": "eeg-eval-0"},
            "created_at": created, "finished_at": created, "synthetic": True, "kind": "synthetic_stress",
            **fixture_tag,
        }
        copies.append(forbidden_exp)
        mem_rows.append(dict(
            campaign_id=cid, protocol_id=old_pid, kind="synthetic_stress", synthetic=True, verified=False,
            source_ids=[forbidden_exp["_id"]], created_at=tick(), extra=fixture_tag,
            text=(f"SYNTHETIC record under obsolete protocol {old_pid}: {inc['label']} -> val balanced accuracy "
                  f"{boosted:.3f}. Different evaluator; not comparable with protocol {pid}.")))

    campaign = {
        "_id": cid, "objective": src["objective"], "goal_version": len(goal_history), "constraints": constraints,
        "goal_history": goal_history, "protocol": src["protocol"], "protocol_id": pid,
        "budget": {"max_experiments": len(copies) + 10}, "state": "PAUSED", "context_epoch": 0, "final": None,
        "created_at": goal_history[0]["changed_at"], "updated_at": _iso(t), "source_campaign_id": src_campaign_id,
        **fixture_tag,
    }
    dst_db.campaigns.insert_one(campaign)
    dst_db.experiments.insert_many(copies)
    mem_ids = memory.add_memories(dst_db, mem_rows)
    mem_by_source: dict[str, list[str]] = {}
    for row, mid in zip(mem_rows, mem_ids):
        for s in row["source_ids"]:
            mem_by_source.setdefault(s, []).append(mid)

    def ids_for(exp: dict | None) -> list[str]:
        return [] if exp is None else [exp["_id"], *mem_by_source.get(exp["_id"], [])]

    if name in ("buried_best_eligible", "buried_failure"):
        expected = ids_for(front_copy)
    else:
        inc_copy = _best_eligible([c for c in copies if c.get("protocol_id") == pid], constraints)
        expected = ids_for(inc_copy)
    forbidden = ids_for(forbidden_exp)

    return {"campaign_id": cid, "protocol_id": pid, "name": name, "expected_evidence_ids": expected,
            "forbidden_evidence_ids": forbidden, "description": description, "avoid_family": avoid_family,
            "constraints": constraints, "src_campaign_id": src_campaign_id, "db": dst_db.name,
            "n_distractors": n_distractors, "n_experiments": len(copies)}


def score(scenario: dict, packet: dict, planner_result: dict) -> dict:
    """Computed by code only. `eligible` is judged against the scenario campaign's current constraints."""
    cited = set(planner_result.get("evidence_ids") or [])
    cfg = planner_result.get("config") if planner_result.get("action") == "propose" else None
    constraints = scenario.get("constraints") or packet["goal"]["constraints"]
    try:
        eligible = cfg is not None and C.is_eligible(cfg, constraints)
    except (ValueError, KeyError, TypeError):
        eligible = False
    fam = scenario.get("avoid_family")
    usage = planner_result.get("usage") or {}
    out = {
        "cited_expected": bool(cited & set(scenario.get("expected_evidence_ids", []))),
        "cited_forbidden": bool(cited & set(scenario.get("forbidden_evidence_ids", []))),
        "eligible": eligible,
        "fallback_used": bool(planner_result.get("fallback_used")),
        "input_tokens": usage.get("input_tokens"),
        "cost_usd": usage.get("cost_usd"),
        "expected_in_packet": _in_packet(packet, scenario.get("expected_evidence_ids", [])),
    }
    if fam is not None:
        out["repeated_bad_family"] = cfg is not None and all(cfg.get(k) == v for k, v in fam.items())
    return out


def _in_packet(packet: dict, ids: list[str]) -> bool:
    """Did the context strategy even surface the expected evidence? (retrieval, not the planner)"""
    from harness.planner import packet_evidence_ids
    return bool(set(ids) & packet_evidence_ids(packet))


def reset(dst_db) -> dict:
    """Delete every fixture campaign plus its experiments, memories, packets and events."""
    cids = [c["_id"] for c in dst_db.campaigns.find({"fixture": True}, {"_id": 1})]
    out = {c: dst_db[c].delete_many({"fixture": True}).deleted_count for c in ("campaigns", "experiments", "memories")}
    for c in ("packets", "events"):
        out[c] = dst_db[c].delete_many({"campaign_id": {"$in": cids}}).deleted_count
    return out


def main() -> None:
    from harness.db import get_db

    ap = argparse.ArgumentParser()
    ap.add_argument("--src-campaign", required=True)
    ap.add_argument("--src-db", default="second_shift")
    ap.add_argument("--dst-db", default="second_shift_eval")
    ap.add_argument("--n-distractors", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--reset", action="store_true", help="delete earlier fixture docs in dst-db first")
    ap.add_argument("--out", default="eval/scenarios.json")
    args = ap.parse_args()
    if args.dst_db in ("second_shift", args.src_db):
        raise SystemExit("dst-db must differ from the source/demo DB")
    src, dst = get_db(args.src_db), get_db(args.dst_db)
    if args.reset:
        print("reset", reset(dst))
    if "memories" not in dst.list_collection_names():
        dst.create_collection("memories")
    memory.ensure_vector_index(dst)
    out = [build_scenario(src, dst, args.src_campaign, n, n_distractors=args.n_distractors, seed=args.seed + i)
           for i, n in enumerate(SCENARIOS)]
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(json.dumps([{k: s[k] for k in ("name", "campaign_id", "expected_evidence_ids", "forbidden_evidence_ids")}
                      for s in out], indent=2))


if __name__ == "__main__":
    main()
