from eval.research_benchmark import run_rollout, summarize_runs
from harness import contracts as C
from harness.worker import fallback_plan
from tests.test_research import measurement, predictions


def oracle():
    outcomes = {}
    for i, cfg in enumerate(C.all_configs()):
        outcomes[C.experiment_key("p", cfg)] = {"config": cfg, "status": "done",
                                                "result": measurement(predictions(correct=5 + i % 6))}
    return {"protocol_id": "p", "outcomes": outcomes}


def test_replay_equal_initialization_budget_and_no_oracle_leak():
    data = oracle()
    calls = []
    def selector(packet):
        calls.append(packet)
        # Only accepted measurements can appear as observed evidence.
        assert len(packet["tried_keys"]) == packet["goal"]["budget"]["used"]
        assert "outcomes" not in packet and "eligible_validation_optimum" not in packet
        for row in packet["recent"] + packet["leaders"] + packet["laggards"]:
            assert row["experiment_id"].rsplit(":", 1)[1] in packet["tried_keys"]
        return fallback_plan(packet, "test")
    runs = [run_rollout(data, arm, "reduce_to9_after5", 1, planner=selector)
            for arm in ("current_planner", "hybrid", "optimizer", "random")]
    assert len(calls) == 14
    assert all([s["key"] for s in r["steps"][:3]] == [s["key"] for s in runs[0]["steps"][:3]] for r in runs)
    for run in runs:
        assert len(run["steps"]) == len({s["key"] for s in run["steps"]}) == 10
        assert all(s["config"]["channels"] == "central9" for s in run["steps"][5:])
        assert all(s["regret"] >= 0 for s in run["steps"])
    assert len(summarize_runs(runs)) == 4


def test_random_and_optimizer_are_reproducible():
    data = oracle()
    for arm in ("optimizer", "random"):
        a = run_rollout(data, arm, "constant64", 3)
        b = run_rollout(data, arm, "constant64", 3)
        assert [s["key"] for s in a["steps"]] == [s["key"] for s in b["steps"]]
