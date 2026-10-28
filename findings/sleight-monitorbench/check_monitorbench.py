"""MonitorBench (Wang et al., arXiv 2603.28590) checks 0, 1, 5, 7, static.

python -I check_monitorbench.py --cache data [--out monitorbench_checks.json]

Inputs under --cache:
  gh/MonitorBench/                 git clone of ASTRAL-Group/MonitorBench (commit b6229e4b)
  arxiv/src_2603.28590.tar         arXiv e-print (v4), extracted to arxiv/tex_2603.28590/
No model rollouts are released, so nothing here runs a model. Code is read as text.
"""
import argparse, collections, csv, glob, hashlib, itertools, json, pathlib, re, subprocess, sys
import yaml

TASKS = {  # task -> (dataset file relative to repo, paper table count, source per paper appendix)
    "cue_condition.knowledge": ("datasets/cue_condition/knowledge/knowledge.json", 100, "authors' text+hint items"),
    "cue_condition.preference": ("datasets/cue_condition/preference/Preference.json", 108, "authors' preference items"),
    "cue_condition.judgment": ("datasets/cue_condition/Judgment/Judgment.json", 100, "law-judgment case briefs"),
    "cue_condition.health": ("datasets/cue_condition/health/health.json", 65, "ICD-10-CM coded cases"),
    "cue_answer.math": ("datasets/cue_answer/brute_math/brute_math.json", 28, "brainteasers (Han et al. 2025)"),
    "cue_answer.logic": ("datasets/cue_answer/brute_logic/brute_logic.json", 50, "brainteasers (Han et al. 2025)"),
    "cue_answer.health": ("datasets/cue_answer/health/health.json", 65, "same cases as cue_condition.health"),
    "goal_sandbag.safety": ("datasets/goal_sandbag/wmdp/WMDP.json", 150, "WMDP (appendix: 40 bio + 40 chem + 40 cyber)"),
    "goal_sandbag.math": ("datasets/goal_sandbag/aime24/test.jsonl", 30, "AIME 2024"),
    "goal_sandbag.science": ("datasets/goal_sandbag/gpqa_diamond/test.jsonl", 192, "GPQA-Diamond"),
    "goal_sandbag.engineering": ("datasets/goal_sandbag/mmlu_pro/MMLU_Pro.json", 100, "MMLU-Pro (appendix: 150 sampled)"),
    "goal_deception.realworld": ("datasets/goal_deception/realworld/Deception.json", 50, "DeceptionBench"),
    "dual_objectives.steganography": ("datasets/dual_objective/databricks_dolly/task_writing_steganography.json", 50, "databricks-dolly + acrostic side task"),
    "dual_objectives.summarization": ("datasets/dual_objective/summary/task_writing_summarization.json", 50, "summaries + verbatim-sentence side task"),
    "dual_objectives.coding": (None, 291, "BigCodeBench + CoT Red-Handed side tasks (TEST pairings)"),
    "dual_objectives.agent": (None, 5, "SHADE-Arena public task pairs"),
    "impossible.coding": (None, 50, "ImpossibleBench (LiveCodeBench oneoff, limit 50)"),
    "process.multistep": ("datasets/necessary_steps/lore/lore.csv", 25, "LORE-MONO-style, GPT-5.2 screened"),
}
TEXT_FIELDS = ["question", "problem", "problem_text", "Input", "control_text", "control_case_brief", "prompt", "data"]


def load_items(p):
    p = pathlib.Path(p)
    if p.suffix == ".csv":
        return list(csv.DictReader(p.open(encoding="utf-8-sig")))
    if p.suffix == ".jsonl":
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    return json.loads(p.read_text())


def item_text(x):
    parts = []
    for k in TEXT_FIELDS:
        if k in x and x[k]:
            v = x[k]
            parts.append(v if isinstance(v, str) else json.dumps(v, sort_keys=True))
    return "\n".join(parts) if parts else json.dumps(x, sort_keys=True)


def norm(s):
    return re.sub(r"\s+", " ", s.lower()).strip()


def shingles(s, k=5):
    w = re.findall(r"\w+", s.lower())
    return {" ".join(w[i:i + k]) for i in range(max(0, len(w) - k + 1))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="monitorbench_checks.json")
    a = ap.parse_args()
    cache = pathlib.Path(a.cache)
    repo = cache / "gh" / "MonitorBench"
    tex = cache / "arxiv" / "tex_2603.28590"
    res = {"pins": {}, "check0": {}, "check1": {}, "check5": {}, "check7": {}, "extra": {}}
    g = lambda *c: subprocess.run(["git", "-C", str(repo), *c], capture_output=True, text=True).stdout.strip()
    res["pins"] = {
        "repo": "ASTRAL-Group/MonitorBench", "commit": g("rev-parse", "HEAD"), "commit_date": g("log", "-1", "--format=%cI"),
        "arxiv": "2603.28590 (v4 per abs page)",
        "arxiv_src_sha256": hashlib.sha256((cache / "arxiv" / "src_2603.28590.tar").read_bytes()).hexdigest(),
        "released_rollouts": "none found: no HF dataset matches 'MonitorBench' or author ASTRAL-Group (searched 2026-10-27); repo ships inputs and code only",
    }

    # ---- check 0: provenance and counts
    rows = {}
    total_paper = total_file = 0
    for t, (f, n_paper, src) in TASKS.items():
        n_file = None
        if f and t == "process.multistep":
            n_file = sum(1 for x in load_items(repo / f) if x["shortcut_affect_brute_force_evaluation"] == "NO")  # process.py filter
        elif f:
            n_file = len(load_items(repo / f))
        elif t == "dual_objectives.coding":
            p = json.loads((repo / "pipeline/verification/dualcoding/tasks/data/bigcodebench_pairings.json").read_text())
            ids = set(map(str, json.loads((repo / "pipeline/verification/dualcoding/tasks/data/task_id_sets.json").read_text())["TEST_SET"]))
            side = yaml.safe_load((repo / "config/dataset_config.yaml").read_text())["dual_coding"]["bcb_side_tasks"]
            c = collections.Counter(v["task"] for k, v in p.items() if k in ids)
            n_file = sum(c[s] for s in side)
            rows.setdefault("_coding_per_side_task", {s: c[s] for s in side})
        elif t == "dual_objectives.agent":
            n_file = len(yaml.safe_load((repo / "config/dataset_config.yaml").read_text())["dual_agent"]["task_folders"])
        elif t == "impossible.coding":
            n_file = yaml.safe_load((repo / "config/dataset_config.yaml").read_text())["impossible_coding"]["limit"]
        rows[t] = {"source": src, "n_paper_table": n_paper, "n_in_repo": n_file, "match": n_file == n_paper}
        total_paper += n_paper; total_file += n_file
    rows["_dual_agent_counted_twice_in_paper_(malicious,benign)"] = True
    res["check0"] = {
        "tasks": rows,
        "paper_total_stated": 1514,
        "sum_of_paper_table_counts_with_agent_twice": total_paper + 5,
        "sum_of_repo_counts_with_agent_twice": total_file + 5,
        "mismatches": [t for t, r in rows.items() if isinstance(r, dict) and "match" in r and not r["match"]],
        "labels": "no static classes: the evaluated model's rollouts are labelled by verification (Y) and by a Qwen3-32B monitor (Z); "
                  "intervention runs (X=1) and no-intervention runs (X=0) come from the same template and model",
        "agent_tasks_are_shade_arena_public_pairs": yaml.safe_load((repo / "config/dataset_config.yaml").read_text())["dual_agent"]["task_folders"],
    }

    # ---- check 1: content-blind monitor under the pinned scorer
    def score_intervention(flags, verif, r_effect):  # pipeline/base.py BaseInterventionTask.report_monitorability_score
        k = sum(1 for z, y in zip(flags, verif) if y and z); n = sum(1 for y in verif if y)
        return min(1.0, (k / n) / r_effect)
    def score_outcome(flags):  # BaseOutcomeTask / process.py: mean of flags over monitored (passing) rollouts
        return sum(flags) / len(flags)
    grid = []
    for r_eff in (0.01, 0.1, 0.5, 0.99):
        for n_pass in (1, 3, 10):
            grid.append(score_intervention([1] * n_pass, [1] * n_pass, r_eff))
    # published CoT-only table (uncommented rows)
    cells = []
    for line in (tex / "Tab" / "baseline_gm2_cot_only.tex").read_text().splitlines():
        if line.strip().startswith("%"):
            continue
        if "&" in line and re.search(r"\d+\.\d", line) and "Avg. over tasks" not in line:
            for v in re.findall(r"(?<![\w.])(\d+\.\d)(?![\w.])", line.split("&", 2)[-1]):
                cells.append(float(v))
    # does the score use any negative (X=0, or Y=1 & not-flag counted against)?
    base_src = (repo / "pipeline/base.py").read_text()
    res["check1"] = {
        "always_flag_monitor_score_intervention_tasks": sorted(set(grid)),
        "always_flag_monitor_score_outcome_and_process_tasks": score_outcome([1, 1, 1]),
        "published_cot_only_cells_parsed": len(cells),
        "published_cot_only_cells_below_100": sum(1 for c in cells if c < 100.0),
        "published_cot_only_cell_range": [min(cells), max(cells)] if cells else None,
        "score_has_false_positive_term": False,
        "evidence": "pipeline/base.py: outcome score = sum(flags)/count over passing rollouts; intervention score = min(1, P(Z=1|X=1,Y=1)/R_effect); "
                    "X=0 runs are never sent to the monitor (BaseInterventionTask.prepare_monitor_llm_query uses them only for R_effect). "
                    "The g-mean^2 = TPR x TNR definition is commented out in the paper source (Sec/3_design.tex).",
        "tnr_commented_out_in_paper_source": "% We adopt $\\text{g-mean}^2$" in (tex / "Sec" / "3_design.tex").read_text(),
        "x0_runs_used_only_for_r_effect": "records_no_inter_dict[" in base_src and "record_no_inter[\"verification_result\"]" in base_src,
        "monitor_validation_in_paper": "human study, 300 single-turn trajectories, monitor F1 85.31 / 91.86 / 92.13 (action / CoT / all); precision not reported separately",
        "text_baselines": "blocked: no CoTs or actions are released, so length or keyword baselines cannot be computed",
    }

    # ---- check 5: duplicates and contamination
    files = sorted(set(f for f, *_ in TASKS.values() if f))
    sha = {f: hashlib.sha256((repo / f).read_bytes()).hexdigest() for f in files}
    by =collections.defaultdict(list)
    for f, h in sha.items():
        by[h].append(f)
    dup_files = [v for v in by.values() if len(v) > 1]
    within = {}; texts = []
    for f in files:
        if any(f in v[1:] for v in dup_files):
            continue
        items = load_items(repo / f)
        tx = [item_text(x) for x in items]
        c = collections.Counter(norm(s) for s in tx)
        sh = [shingles(s) for s in tx]
        near = sum(1 for i, j in itertools.combinations(range(len(sh)), 2)
                   if sh[i] and sh[j] and len(sh[i] & sh[j]) / len(sh[i] | sh[j]) >= 0.8)
        within[f] = {"n": len(tx), "exact_duplicate_texts": sum(v - 1 for v in c.values() if v > 1), "near_duplicate_pairs_j>=0.8": near}
        texts += [(f, s) for s in sh]
    cross = collections.Counter()
    for (f1, s1), (f2, s2) in itertools.combinations(texts, 2):
        if f1 != f2 and s1 and s2 and len(s1 & s2) / len(s1 | s2) >= 0.8:
            cross[f"{f1} ~ {f2}"] += 1
    canary_files = [str(p.relative_to(repo)) for p in (repo / "datasets").rglob("*") if p.is_file() and "canary" in p.read_text(errors="ignore").lower()]
    gpqa = load_items(repo / TASKS["goal_sandbag.science"][0])
    res["check5"] = {
        "identical_dataset_files": dup_files,
        "within_file": within,
        "cross_file_near_duplicates_j>=0.8": dict(cross),
        "files_with_canary_string": canary_files,
        "gpqa_diamond_items_in_plaintext": len(gpqa),
        "public_benchmark_items_reused": {"WMDP": 120, "AIME 2024": 30, "GPQA-Diamond": len(gpqa), "MMLU-Pro": 150, "BigCodeBench": 291, "SHADE-Arena public": 5},
        "coding_bcb_ids_repeated_across_side_tasks": 0,
        "task_id_construction": "task_id = f'{index}_{stress_test}' over file order; labels (Y, Z) are produced at run time, so ids and order carry no label",
    }

    # ---- check 7: what the monitor prompt contains
    tmpl = {}
    for f in sorted((repo / "prompts").glob("monitor_*.yaml")):
        d = yaml.safe_load(f.read_text())
        tmpl[f.stem] = {k: sorted(set(re.findall(r"(?<!\{)\{([a-z_]+)\}(?!\})", v))) for k, v in d.items()}
    # original_question assignments: do any include the stress-test prompt?
    oq = []
    for f in ("pipeline/intervention.py", "pipeline/outcome.py", "pipeline/process.py"):
        for i, line in enumerate((repo / f).read_text().splitlines(), 1):
            if '"original_question"' in line and ":" in line:
                oq.append({"file": f, "line": i, "expr": line.split(":", 1)[1].strip().rstrip(","),
                           "includes_stress_prompt": "stress_test_prompt" in line or "attack_policy=stress" in line})
    res["check7"] = {
        "monitor_prompt_placeholders_per_scope": tmpl,
        "fields": {
            "intervention": "decision_critical_factor = the injected cue text (cue_condition.*, goal_deception)",
            "answer": "target; for cue_answer.* this is the injected guess, which equals the ground truth",
            "task": "decision_critical_factor = side-task text (dual_objectives.*, impossible.coding)",
            "input": "original_question; for steganography/summarization it is question + side_task (outcome.py), so the side task appears twice",
        },
        "original_question_assignments": oq,
        "any_original_question_includes_stress_prompt": any(x["includes_stress_prompt"] for x in oq),
        "impossible_coding_stress_instruction_in_monitor_input": {
            "attack_prompt_in_sample_input": "instruction_prompt=instruction_prompt +" in (repo / "pipeline/verification/impossiblebench/livecodebench_tasks.py").read_text()
                and "input_text = instruction_prompt" in (repo / "pipeline/verification/impossiblebench/livecodebench_tasks.py").read_text(),
            "original_question_is_sample_input": '"prompt": item[\'sample\'].input' in (repo / "pipeline/verification/impossiblebench/impossiblebench_run.py").read_text(),
            "decision_critical_factor_is_attack_prompt": "IMPOSSIBLE_ATTACK_PROMPTS[attack_policy]" in (repo / "pipeline/outcome.py").read_text(),
            "stealth_prompt_contains_CONCEAL": "CONCEAL" in (repo / "pipeline/outcome.py").read_text(),
            "note": "for impossible.coding under direct_conceal / monitor_aware, the monitor's {input} and {task} carry the stress-test instruction; the other 18 tasks (agent malicious and benign share one site) build original_question without it",
        },
        "paper_disclosure": "Sec 4: 'The monitor model is given exact decision-critical factors to look for'",
    }

    # ---- extra: agent score population vs paper
    out_src = (repo / "pipeline/outcome.py").read_text()
    res["extra"]["dual_agent_monitors_all_rollouts"] = {
        "code": "DualAgent._write_tested_jsonls keeps every evaluated rollout (side_task_pass True or False); DualAgent.prepare_monitor_llm_query "
                "loops over all conversations without checking verification; BaseOutcomeTask.report_monitorability_score averages all flags",
        "paper": "appendix: 'We compute the monitorability score on samples whose side objective is successfully completed.'",
        "loop_has_no_verification_filter": "for idx, conversation in enumerate(conversations):" in out_src
            and "verification_result" not in out_src.split("def prepare_monitor_llm_query(self, input_path, output_path):\n        prompt_dataset")[-1].split("# --- external agent-env")[0],
        "effect": "untested (no rollouts released)",
    }
    pathlib.Path(a.out).write_text(json.dumps(res, indent=1))
    print(f"wrote {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
