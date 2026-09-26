"""Two-arm comparison: recent_window vs evidence packets. OWNER: Andrew.

    python -m eval.run_ablation [--scenarios eval/scenarios.json] [--repeats 3]

Same planner, model settings, tools and hard guards in both arms; only the
context strategy differs. Scenarios come from David's eval/fixtures.py and live
in DB second_shift_eval. Writes eval/results.json and prints a markdown table.
Whatever the numbers say is what gets reported.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

from harness import context
from harness.db import get_db, now_iso
from harness.worker import call_planner, guard

ARMS = ("recent_window", "evidence")


def run(scenarios: list[dict], repeats: int, db_name: str) -> dict:
    from eval.fixtures import score  # David's scorer, computed in code

    db = get_db(db_name)
    rows = []
    for sc in scenarios:
        for arm in ARMS:
            for rep in range(repeats):
                packet = context.build_packet(db, sc["campaign_id"], strategy=arm)
                result = call_planner(packet)
                s = score(sc, packet, result)
                rows.append({"scenario": sc["name"], "arm": arm, "repeat": rep, "packet_id": packet["packet_id"],
                             "token_estimate": packet["token_estimate"], "guard_problem": guard(packet, result)
                             if result["action"] == "propose" else None, "model": result["model"], **s})
    summary = {}
    for arm in ARMS:
        r = [x for x in rows if x["arm"] == arm]
        tokens = [x["input_tokens"] for x in r if x.get("input_tokens") is not None]
        summary[arm] = {
            "decisions": len(r),
            "cited_expected_evidence": sum(bool(x["cited_expected"]) for x in r),
            "cited_forbidden_evidence": sum(bool(x["cited_forbidden"]) for x in r),
            "eligible_proposals": sum(bool(x["eligible"]) for x in r),
            "fallbacks": sum(bool(x["fallback_used"]) for x in r),
            "mean_input_tokens_provider": round(mean(tokens)) if tokens else None,
            "mean_packet_tokens_estimate": round(mean(x["token_estimate"] for x in r)),
            "total_cost_usd": round(sum(x.get("cost_usd") or 0 for x in r), 4),
        }
    return {"ran_at": now_iso(), "db": db_name, "repeats": repeats, "summary": summary, "rows": rows}


def table(summary: dict) -> str:
    keys = list(next(iter(summary.values())).keys())
    lines = ["| metric | " + " | ".join(summary) + " |", "|---|" + "---|" * len(summary)]
    lines += [f"| {k} | " + " | ".join(str(summary[a][k]) for a in summary) + " |" for k in keys]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", default="eval/scenarios.json")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--db", default="second_shift_eval")
    args = ap.parse_args()
    scenarios = json.loads(Path(args.scenarios).read_text())
    if isinstance(scenarios, dict):  # tolerate {name: scenario}
        scenarios = list(scenarios.values())
    out = run(scenarios, args.repeats, args.db)
    Path("eval/results.json").write_text(json.dumps(out, indent=2, default=str))
    print(table(out["summary"]))


if __name__ == "__main__":
    main()
