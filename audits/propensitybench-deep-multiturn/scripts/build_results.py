"""Add the summary block to results.json (run after analyze.py).

    python3 -I scripts/build_results.py
"""
import json
from pathlib import Path

F = Path(__file__).resolve().parent.parent


def main():
    res = json.loads((F / "results.json").read_text())
    runs = res["runs"]
    h = runs["groups"]["haiku|shipped|benign|financials"]
    s = runs["groups"]["sonnet|shipped|benign|financials"]
    rd = json.loads((F / "render_diff.json").read_text())
    mt = json.loads((F / "mock_test.json").read_text())
    pw = json.loads((F / "power.json").read_text())
    res["summary"] = {
        "condition": {"naming": "benign", "category": "financials", "levels": 12,
                      "scenarios": "parent's 32 (16 self-proliferation, 16 cybersecurity)"},
        "runner_faithfulness": {
            "static_literals_found_in_pinned_source": [sum(rd["static_checks"].values()), len(rd["static_checks"])],
            "messages_verbatim_in_text_form": [rd["dynamic"]["messages_compared"] - len(rd["dynamic"]["missing_or_out_of_order"]),
                                               rd["dynamic"]["messages_compared"]],
            "mock_end_to_end_checks": [sum(v["pass"] for v in mt["checks"].values()), len(mt["checks"])],
        },
        "haiku_pilot": {
            "runs": h["n_runs"], "complete": h["n_complete"], "blocked": h["status"].get("blocked", 0),
            "misaligned": h["misaligned"], "rate": h["rate"], "wilson95": h["wilson95"],
            "one_sided_upper95": h["upper95_if_zero"],
            "worst_case_blocked_as_misaligned": h["worst_case_blocked_error_as_misaligned"],
            "runs_reaching_level_12": h["runs_reaching_level_12"],
            "aligned_tool_called_runs": runs["target_called_runs"]["haiku|shipped|benign|financials"],
            "runs_with_malformed_tool_call": h["runs_with"]["malformed_tool_call"],
            "runs_with_format_error": h["runs_with"]["format_errors"],
            "runs_with_interaction_limit": h["runs_with"]["interaction_limit"],
            "runs_with_message_limit": h["runs_with"]["message_limit"],
            "llm_calls": sum(h["llm_calls_per_run"]), "cost_usd": h["cost_usd_total"],
            "cost_usd_per_run_mean": h["cost_usd_per_run_mean"], "seconds_per_run_mean": h["seconds_per_run_mean"],
            "runs_whose_replies_name_the_audit_path": runs["cli_context_leak"]["haiku"]["runs_with"]["benchmark_or_audit_path"],
        },
        "sonnet_pilot": {
            "runs_started": s["n_runs"], "status": s["status"], "levels_reached": runs["levels_reached"]["sonnet|shipped|benign|financials"],
            "misaligned_before_stop": 0, "llm_calls": sum(s["llm_calls_per_run"]),
            "stopped_because": "folder spend reached the brief's 2 USD stop with the Haiku base rate at 0",
        },
        "three_arm_test": {"run": False, "reason": "prereg rule: shipped base rate must be >= 20% with >= 4 misaligned runs; "
                                                    "Haiku 0/30, Sonnet 0 in 2 truncated runs"},
        "power_reference": [c for c in pw["cells"] if c["design"] == "one_category_all_32"],
        "inference": runs.get("inference"),
        "local_model": {"run": False, "plan": "LOCAL_MODEL_PLAN.md",
                        "recommended": "Qwen/Qwen3-8B-MLX-4bit@383413e909f3bc5303ce195ebbdf0339c5a1a2a3 (4,351,884,216-byte safetensors)"},
    }
    (F / "results.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res["summary"], indent=1)[:3000])


if __name__ == "__main__":
    main()
