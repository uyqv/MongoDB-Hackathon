"""Memory stress test: retrieval latency and quality as distractor notes grow. OWNER: David.

    python -m eval.stress [--src-campaign camp_0f8981ee] [--levels 0,1000,10000]

Copies a real campaign (read only, from second_shift) into a new campaign in
second_shift_eval, then adds synthetic distractor notes (kind synthetic_stress,
synthetic True) in batches through memory.add_memories. At each level it measures:
search_memories latency p50/p95 over 20 distinct queries (end to end, including the
Voyage query embedding), whether the real incumbent's verified_result memory is in
the top 4 for a query about the best eligible configuration, the evidence packet
token_estimate from context.build_packet vs its budget, and the memory count.
Writes eval/stress.json. Whatever it measures is what gets reported.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import time
from pathlib import Path

from harness import contracts as C
from harness import context, memory
from harness.db import get_db, now_iso
from eval import fixtures

QUERIES = [
    "best eligible configuration so far under the current channel limit",
    "which csp_lda settings gave the highest validation balanced accuracy",
    "failed experiments to avoid",
    "results for the beta 13-30 Hz band",
    "results for the mu 8-12 Hz band",
    "motor21 channel set results",
    "central9 channel set with few electrodes",
    "effect of the time window after the cue",
    "w0.5_2.5 window results",
    "bandpower logistic regression results",
    "how many CSP components worked best",
    "all64 channels compared with fewer channels",
    "verified results under the current protocol",
    "what should the next experiment be",
    "broad 8-30 Hz band results",
    "high beta 20-30 Hz",
    "lowest scoring configuration",
    "experiments that errored during fit",
    "imagined fists versus feet decoding accuracy",
    "evidence for choosing n_components 6",
]
INCUMBENT_QUERY = ("Best eligible configuration: which verified result has the highest validation balanced "
                   "accuracy under the current channel limit?")

_EXTRA = [
    "Synthetic note {i}: artifact rejection threshold of {n} microvolts considered for run {r}; not applied.",
    "Synthetic note {i}: subject {s} reported drowsiness during run {r}; left as is.",
    "Synthetic note {i}: electrode {e} impedance looked high in a pilot session, unrelated to this campaign.",
    "Synthetic note {i}: literature says {band} ERD appears over {e} during imagery; no result here.",
    "Synthetic note {i}: plan to compare {method} against a Riemannian baseline someday.",
    "Synthetic note {i}: epoch rejection would change n_train, so it is out of protocol.",
]


def distractors(n: int, start: int, seed: int) -> list[str]:
    rng = random.Random(seed + start)
    base = fixtures._distractor_texts(n, seed + start)
    out = []
    for i, text in enumerate(base, start):
        if rng.random() < 0.5:
            text = "SYNTHETIC distractor. " + rng.choice(_EXTRA).format(
                i=i, n=rng.choice([50, 75, 100, 150]), r=rng.choice([6, 10, 14]), s=rng.randint(1, 109),
                e=rng.choice(["C3", "Cz", "C4", "FC3", "CP4", "Fp1", "O2"]), band=rng.choice(list(C.BANDS)),
                method=rng.choice(list(C.METHODS)))
        out.append(text)
    return out


def copy_campaign(src, dst, src_cid: str) -> tuple[str, str]:
    """Real experiments + re-rendered verified/failure memories, no distractors. Returns (cid, incumbent memory id)."""
    sc = fixtures.build_scenario(src, dst, src_cid, "goal_changed", n_distractors=0)
    cid = sc["campaign_id"]
    camp = src.campaigns.find_one({"_id": src_cid})
    # Keep the source goal (not the fixture's 64 -> 21 change) and relabel it as a stress campaign.
    dst.campaigns.update_one({"_id": cid}, {"$set": {
        "scenario": "stress", "goal_version": 1, "constraints": camp["constraints"],
        "goal_history": [{"version": 1, "constraints": camp["constraints"], "changed_at": camp["created_at"],
                          "reason": "copied from source campaign"}]}})
    dst.memories.update_many({"campaign_id": cid}, {"$set": {"scenario": "stress"}})
    dst.experiments.update_many({"campaign_id": cid}, {"$set": {"scenario": "stress"}})
    campaign = dst.campaigns.find_one({"_id": cid})
    done = [e for e in dst.experiments.find({"campaign_id": cid, "status": "done"})
            if C.is_eligible(e["config"], campaign["constraints"])]
    inc = max(done, key=lambda e: e["result"]["val_balanced_accuracy"])
    inc_mem = dst.memories.find_one({"campaign_id": cid, "kind": "verified_result", "source_ids": inc["_id"]})
    return cid, inc_mem["_id"]


def wait_indexed(db, cid: str, pid: str, probe_text: str, timeout: float = 240) -> float:
    """Vector index sync is eventually consistent: wait until the newest note is searchable."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        memory._embed_query.cache_clear()
        hits = memory.search_memories(db, campaign_id=cid, protocol_id=pid, query=probe_text, k=3)
        if any(h["text"] == probe_text and h["retrieval"] == "vector" for h in hits):
            return time.monotonic() - t0
        time.sleep(3)
    return -1.0


def measure(db, cid: str, pid: str, inc_mem: str) -> dict:
    memory._embed_query.cache_clear()
    lat, modes = [], []
    for q in QUERIES:
        t = time.perf_counter()
        hits = memory.search_memories(db, campaign_id=cid, protocol_id=pid, query=q, k=4)
        lat.append((time.perf_counter() - t) * 1000)
        modes.append(hits[0]["retrieval"] if hits else "none")
    memory._embed_query.cache_clear()
    top = memory.search_memories(db, campaign_id=cid, protocol_id=pid, query=INCUMBENT_QUERY, k=4)
    rank = next((i + 1 for i, h in enumerate(top) if h["memory_id"] == inc_mem), None)
    packet = context.build_packet(db, cid, "evidence")
    q = statistics.quantiles(lat, n=20)
    return {
        "memories_total": db.memories.count_documents({"campaign_id": cid}),
        "distractors": db.memories.count_documents({"campaign_id": cid, "synthetic": True}),
        "search_ms_p50": round(statistics.median(lat), 1), "search_ms_p95": round(q[18], 1),
        "retrieval_modes": {m: modes.count(m) for m in set(modes)},
        "incumbent_in_top4": rank is not None, "incumbent_rank": rank,
        "top4_kinds": [h["kind"] for h in top], "top4_scores": [round(h["score"] or 0, 4) for h in top],
        "packet_token_estimate": packet["token_estimate"], "packet_budget_tokens": packet["budget_tokens"],
        "packet_under_budget": packet["token_estimate"] <= packet["budget_tokens"],
        "packet_retrieved_kinds": [m["kind"] for m in packet["retrieved"]],
        "packet_has_incumbent": bool(packet["incumbent"]),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-campaign", default="camp_0f8981ee")
    ap.add_argument("--src-db", default="second_shift")
    ap.add_argument("--dst-db", default="second_shift_eval")
    ap.add_argument("--levels", default="0,1000,10000")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="eval/stress.json")
    args = ap.parse_args()
    src, dst = get_db(args.src_db), get_db(args.dst_db)
    memory.ensure_vector_index(dst)
    cid, inc_mem = copy_campaign(src, dst, args.src_campaign)
    pid = dst.campaigns.find_one({"_id": cid})["protocol_id"]
    print(f"stress campaign {cid} in {dst.name}, incumbent memory {inc_mem}", flush=True)

    results, have = [], 0
    for level in [int(x) for x in args.levels.split(",")]:
        add = level - have
        insert_s = 0.0
        if add > 0:
            texts = distractors(add, have, args.seed)
            t = time.perf_counter()
            for i in range(0, add, 1000):
                memory.add_memories(dst, [dict(campaign_id=cid, protocol_id=pid, kind="synthetic_stress", text=x,
                                               source_ids=[], verified=False, synthetic=True,
                                               extra={"fixture": True, "scenario": "stress"})
                                          for x in texts[i:i + 1000]])
            insert_s = time.perf_counter() - t
            have = level
            sync_s = wait_indexed(dst, cid, pid, texts[-1])
        else:
            sync_s = 0.0
        row = {"level": level, "insert_embed_seconds": round(insert_s, 1), "index_sync_seconds": round(sync_s, 1),
               **measure(dst, cid, pid, inc_mem)}
        results.append(row)
        print(json.dumps(row), flush=True)

    out = {"ran_at": now_iso(), "db": dst.name, "campaign_id": cid, "src_campaign_id": args.src_campaign,
           "incumbent_memory_id": inc_mem, "queries": len(QUERIES), "k": 4,
           "latency_note": "end to end search_memories: Voyage query embedding + $vectorSearch, from this laptop",
           "results": results}
    Path(args.out).write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
