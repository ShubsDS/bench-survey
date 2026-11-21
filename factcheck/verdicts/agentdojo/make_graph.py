"""Assemble graph_data.json. Usage: python -I make_graph.py <scriptdir>"""
import json, sys; sys.path.insert(0, sys.argv[1])
import pandas as pd
from common_fc import TABLE20, REPO_FOUR
r = json.load(open("results_fc.json")); m = r["main_v112_important_instructions_table20"]
s = json.load(open("strict.json")); ab = pd.read_csv("results_fc_ability_check.csv", index_col=0)
models = {}
for p in sorted(TABLE20, key=lambda p: m[p]["published_asr"]):
    q = m[p]
    models[p] = dict(
        n_runs=q["one"], n_secure=q["secure"], n_errored_runs=q["errored"],
        n_secure_untraced_empty_trace=q["c_untraced"],
        n_secure_never_saw=q["c_never"], n_secure_could_not=q["c_couldnot"], n_secure_saw_and_could=q["c_sawcould"],
        n_secure_never_saw_and_also_unable=q["never_and_unable"],
        n_secure_saw_and_could_but_acted_on_injection_proxy=q["follow_saw_secure"] - q["couldnot_follow"],
        share_never_saw=q["share_never_saw"], share_never_saw_ci95=q["share_never_saw_ci"],
        share_could_not=q["share_could_not"], share_could_not_ci95=q["share_could_not_ci"],
        share_never_or_could_not=q["share_never_or_could_not"], share_never_or_could_not_ci95=q["share_never_or_could_not_ci"],
        share_never_or_could_not_or_untraced=q["share_never_or_could_not_or_untraced"],
        share_never_or_could_not_or_untraced_ci95=q["share_never_or_could_not_or_untraced_ci"],
        share_saw_and_could=q["share_saw_and_could"], share_saw_and_could_ci95=q["share_saw_and_could_ci"],
        share_never_or_could_not_strict=s[p]["share_never_or_strict"], share_never_or_could_not_strict_ci95=s[p]["ci"],
        could_not_runs_on_injection_tasks_model_achieved_under_attack=int(ab.loc[p, "couldnot_secure_on_tasks_with_success"]),
        published_asr=q["published_asr"], published_asr_ci95=q["published_asr_ci"],
        asr_given_saw=q["asr_given_saw"], asr_given_saw_ci95=q["asr_given_saw_ci"],
        adjusted_asr_given_saw_and_could=q["adjusted_asr_given_saw_and_could"],
        adjusted_asr_given_saw_and_could_ci95=q["adjusted_asr_given_saw_and_could_ci"],
        n_saw_and_could_runs=q["sa"],
        rank_published_asr=q["rank_published_asr"],
        rank_asr_given_saw_errors_not_counted=q["rank_asr_given_saw_errors_not_counted"],
        rank_asr_given_saw_errors_not_counted_ci95=q["rank_asr_given_saw_errors_not_counted_ci"],
        rank_adjusted_asr_errors_not_counted=q["rank_adjusted_asr_given_saw_and_could_errors_not_counted"],
        rank_adjusted_asr_errors_not_counted_ci95=q["rank_adjusted_asr_given_saw_and_could_errors_not_counted_ci"],
        in_repo_four=p in REPO_FOUR,
    )
out = dict(
    notes=dict(
        attack="important_instructions (fixed, non-adaptive)",
        suites="workspace, travel, banking, slack (all four)",
        benchmark_version="v1.1.2 task set used by the public results table: 97 user tasks x 6/7/9/5 injection tasks = 629 cases per model; for the three pipelines run at v1.2.x (Claude 3.7 Sonnet, Gemini 2.0 Flash 001, plus non-table Llama 3.3 / Meta-SecAlign) workspace injection_task_6..13 were dropped. Note 3 table models ran newer injection texts for travel injection tasks 2/5.",
        models="the 20 undefended model rows of util_scripts/create_results_table.py TABLE_MODELS at agentdojo commit 089ed468 (published ASR reproduced exactly for all 20)",
        repo_four=REPO_FOUR,
        repo_four_selection="post hoc: 'four of the six lowest public-ASR models' whose share exceeds half (the other two of the six, Claude 3.5 Sonnet Oct and Claude 3.7 Sonnet, are 37% and 9%). Not in prereg.md; first appears in the validation commits (a303bed/bcfa8b5, 2026-11-17 11:43), after prereg (f3bdb42, 10:57) and results (2922e4e, 11:29).",
        secure="security == False in the stored run (attack goal not met). Errored runs are all stored security == True, so never in 'secure'.",
        never_saw="no tool message in the run contains the injected text (normalized substring match of the run's own `injections` values; identical to '<INFORMATION>' tag presence and to goal-text match on all 12,580 table runs)",
        could_not="injection seen, but the model's single stored run of that injection task given directly as the user prompt (runs/<m>/<suite>/injection_task_k/none/none.json) has utility == False",
        precedence="untraced (empty message list; 200 Claude 3 Opus secure runs) > never_saw > could_not > saw_and_could; the four categories partition n_secure",
        strict_variant="could_not_strict additionally requires that the model never achieved that injection task in any of its attack runs",
        adjusted_asr="security rate among runs where the injection was seen and the model passed the direct-ask run (errors counted as in the table)",
        bootstrap="two-way crossed bootstrap within suite: user tasks and injection tasks resampled independently, B = 2000, seed 12345 (strict variant seed 777); 95% percentile intervals",
        ranks="rank 1 = most attackable; average ranks for ties",
    ),
    distribution_across_20=m["_distribution"],
    models=models,
)
json.dump(out, open("graph_data.json", "w"), indent=1)
print("ok")
