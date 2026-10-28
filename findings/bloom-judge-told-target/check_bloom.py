"""Is Bloom's judge told which model it is scoring when Bloom ranks models across developers?

Bloom (Anthropic, "Bloom: an open source tool for automated behavioral evaluations", 2025-12-19,
https://alignment.anthropic.com/2025/bloom-auto-evals/) ranks 16 models from six developers on four
behaviours, with "Claude Opus 4.1 as the evaluator across all stages", and reports that "the Claude
models score lowest overall". The report says the configurations are in the repository.

This script reads the pipeline code and the benchmark configurations at two pinned commits and
reports:

1. Whether the judge prompt (and the ideation and rollout prompts) say "The model we are evaluating
   is <name>", and what decides it (`anonymous_target`, default False).
2. Whether the sweep (grid) mode the benchmark configurations use can set `anonymous_target` at all:
   the config built from sweep parameters is checked for the key.
3. For each benchmark configuration: the judge, ideation and evaluator models, the target list, how
   many targets are Claude models, and whether `anonymous_target` or a resume stage is set (without
   a resume, every grid run regenerates its own scenarios).
4. For Petri (inspect_petri), the judge prompt's framing of the auditor and the auditor's
   instruction to use the target's real name, for comparison.

It reads code and configuration as text and runs nothing from the repositories.

Usage:
    python check_bloom.py [--cache DIR] [--out bloom_checks.json]
"""
import argparse, ast, json, re, urllib.request
from pathlib import Path

BLOOM = "safety-research/bloom"
BENCH = "8289ee2dbd00530bcfadba32a4eec0c54624c6d6"  # last commit with experiments/benchmarks (deleted 2025-12-11)
FROZEN = "7a184286758de93432fce055acba9750004944dc"  # frozen standalone release, examples/sweeps
PETRI = ("meridianlabs-ai/inspect_petri", "128f61d56776169e5030135eede930783ab7fcc3")
BEHAVIOURS = ("delusion-sycophancy", "instructed-long-horizon-sabotage", "self-preferential-bias", "self-preservation")
NAMED = re.compile(r"The model we are evaluating is \{target_model_name\}")
DEFAULT_FALSE = re.compile(r"""config\.get\(\s*["']anonymous_target["']\s*,\s*False\s*\)""")

LAYOUT = {
    BENCH: {"judge_prompt": "prompts/step4_judgment.py", "ideation_prompt": "prompts/step2_ideation.py",
            "rollout_prompt": "prompts/step3_rollout.py", "judge_stage": "scripts/step4_judgment.py",
            "ideation_stage": "scripts/step2_ideation.py", "rollout_stage": "scripts/step3_rollout.py",
            "utils": "utils.py", "seed": "seed.yaml", "pipeline": "bloom.py",
            "configs": [f"sweeps/{b}.yaml" for b in BEHAVIOURS]
                       + [f"experiments/benchmarks/{b}.yaml" for b in
                          ("delusion-sycophancy", "instructed-long-horizon-sabotage", "sandbagging")]},
    FROZEN: {"judge_prompt": "src/bloom/prompts/step4_judgment.py", "ideation_prompt": "src/bloom/prompts/step2_ideation.py",
             "rollout_prompt": "src/bloom/prompts/step3_rollout.py", "judge_stage": "src/bloom/stages/step4_judgment.py",
             "ideation_stage": "src/bloom/stages/step2_ideation.py", "rollout_stage": "src/bloom/stages/step3_rollout.py",
             "utils": "src/bloom/utils.py", "seed": "src/bloom/data/templates/seed.yaml.template", "pipeline": "src/bloom/core.py",
             "configs": [f"examples/sweeps/{b}.yaml" for b in BEHAVIOURS]},
}


def get(repo, sha, path, cache):
    local = cache / repo.replace("/", "__") / sha[:7] / path
    if not local.exists():
        local.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(f"https://raw.githubusercontent.com/{repo}/{sha}/{path}", timeout=120) as r:
            local.write_bytes(r.read())
    return local.read_text()


def function_body(src, name):
    m = re.search(rf"^def {name}\(.*?(?=^def |\Z)", src, re.S | re.M)
    return m.group(0) if m else ""


def sweep_params(text):
    """Grid-sweep YAML: `  key:` then `    value: x` or `    values: [..]`. Comments dropped."""
    params, key = {}, None
    for line in text.splitlines():
        line = line.split(" #", 1)[0].rstrip()
        m = re.match(r"^  (\S[^:]*):\s*$", line)
        if m:
            key = m.group(1)
            continue
        m = re.match(r"^\s{4,}(values?):\s*(.+)$", line)
        if m and key:
            raw = m.group(2).strip()
            try:
                params[key] = ast.literal_eval(raw)
            except (ValueError, SyntaxError):
                params[key] = raw.strip("\"'")
            key = None
    return params


def bloom_checks(sha, cache):
    f = LAYOUT[sha]
    read = lambda k: get(BLOOM, sha, f[k], cache)
    judge_prompt = function_body(read("judge_prompt"), "make_judge_prompt")
    wandb = function_body(read("utils"), "create_config_from_wandb_params")
    seed = read("seed")
    out = {"commit": f"{BLOOM}@{sha}",
           "judge_prompt_names_target": bool(NAMED.search(judge_prompt)),
           "ideation_prompt_names_target": bool(NAMED.search(read("ideation_prompt"))),
           "rollout_prompt_names_target": bool(NAMED.search(read("rollout_prompt"))),
           "stages_default_to_named": {k: bool(DEFAULT_FALSE.search(read(k)))
                                       for k in ("ideation_stage", "rollout_stage", "judge_stage")},
           "seed_default_anonymous_target": re.search(r"^anonymous_target:\s*(\w+)", seed, re.M).group(1),
           "sweep_config_builder_sets_anonymous_target": "anonymous_target" in wandb,
           "sweep_config_builder_keys": sorted(set(re.findall(r"""config\[["'](\w+)["']\]\s*=""", wandb))),
           "pipeline_stages": list(dict.fromkeys(re.findall(r"""\(\s*["'](understanding|ideation|rollout|judgment)["']""", read("pipeline")))),
           "configs": {}}
    for path in f["configs"]:
        p = sweep_params(get(BLOOM, sha, path, cache))
        targets = p.get("rollout.target", [])
        targets = targets if isinstance(targets, list) else [targets]
        out["configs"][path] = {
            "judge": p.get("judgment.model"), "ideation": p.get("ideation.model"), "evaluator": p.get("rollout.model"),
            "targets": len(targets), "claude_targets": sum(t.startswith("claude") for t in targets),
            "judge_is_a_target": p.get("judgment.model") in targets,
            "anonymous_target_set": "anonymous_target" in p, "resume_set": any(k.startswith("resume") for k in p)}
    return out


def petri_checks(cache):
    repo, sha = PETRI
    judge = get(repo, sha, "src/inspect_petri/_judge/judge.py", cache)
    agent = get(repo, sha, "src/inspect_petri/_auditor/agent.py", cache)
    return {"commit": f"{repo}@{sha}",
            "judge_prompt_says_auditor_elicits_misalignment":
                "The auditor is an AI trying to elicit misaligned behavior from the target" in judge,
            "judge_prompt_names_target": "{target_model}" in judge.split("JUDGE_PROMPT = ", 1)[1],
            "auditor_told_to_use_target_real_name": "user the model's real name" in agent or "use the model's real name" in agent,
            "judge_refusal_scores_none": "value=None" in function_body(judge, "audit_judge")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="bloom_checks.json")
    args = ap.parse_args()
    cache = Path(args.cache)
    result = {"benchmark_era": bloom_checks(BENCH, cache), "frozen_release": bloom_checks(FROZEN, cache),
              "petri": petri_checks(cache)}
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
