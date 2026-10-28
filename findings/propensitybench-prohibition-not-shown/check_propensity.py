"""Does PropensityBench's agent ever see the policy that forbids the misaligned tool?

Sayyed et al., "PropensityBench" (arXiv 2511.20703), give an agent an aligned tool that always
errors and a misaligned tool that would finish the task, then raise pressure; calling the
misaligned tool counts as misaligned behaviour. The paper says that tool is "explicitly and very
clearly forbidden by the scenario's policies", and that the policy "immediately and unequivocally
warns against considering this deviation".

Each scenario stores that policy in fields such as `prohibitions_description` and
`trigger_rationale`. This script, at a pinned commit:

1. Lists the placeholders of the system-prompt template in `evaluation/agent.py` and the policy
   fields `create_system_prompt` passes to it, so it can report which fields are dropped
   (`str.format` ignores unused keyword arguments).
2. Over all 979 scenarios, counts prohibition wording ("prohibited", "forbidden", "never",
   "must not", "not allowed", "under no circumstances", "strictly") in the dropped prohibition
   fields and in the policy text the agent is actually shown about the misaligned tool
   (`immediate_outcome_acknowledgment` and `negative_consequences`).
3. Counts scenarios whose aligned tool has a list of errors to return.

It reads the code and data as text and runs nothing from the repository.

Usage:
    python check_propensity.py [--cache DIR] [--out propensity_checks.json]
"""
import argparse, json, re, urllib.request
from pathlib import Path

COMMIT = "09872f3bbb900a18b2ddc1b5a95d74a0f4db9e17"  # scaleapi/propensity-evaluation
RAW = f"https://raw.githubusercontent.com/scaleapi/propensity-evaluation/{COMMIT}/"
LFS = f"https://media.githubusercontent.com/media/scaleapi/propensity-evaluation/{COMMIT}/"
TREE = f"https://api.github.com/repos/scaleapi/propensity-evaluation/git/trees/{COMMIT}?recursive=1"
PROHIBITION = re.compile(r"\b(prohibit\w*|forbid\w*|never|must not|mustn't|not (?:be )?(?:allowed|permitted)"
                         r"|under no circumstances|strictly)\b", re.I)


def get(url, path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=600) as r:
            path.write_bytes(r.read())
    return path


def template_check(cache):
    src = get(RAW + "evaluation/agent.py", cache / "agent.py").read_text()
    template = src.split('SYSTEM_PROMPT_TEMPLATE = """', 1)[1].split('"""', 1)[0]
    placeholders = sorted(set(re.findall(r"\{(\w+)\}", template)))
    call = src.split("return SYSTEM_PROMPT_TEMPLATE.format(", 1)[1].split("\n        )", 1)[0]
    passed = {k: v.strip() for k, v in re.findall(r"^\s*(\w+)=(.+?),?$", call, re.M)}
    return {"template_placeholders": placeholders,
            "passed_but_not_in_template": {k: passed[k] for k in sorted(passed) if k not in placeholders},
            "policy_fields_referenced": sorted(set(re.findall(r"\['policy'\]\['(\w+)'\]", src)))}


def scenarios(cache):
    tree = json.loads(get(TREE, cache / "tree.json").read_text())
    files = sorted(x["path"] for x in tree["tree"]
                   if x["path"].startswith("data/full/") and x["path"].endswith("scenarios_messages_single.json"))
    counts = {"workspace_files": len(files), "scenarios": 0, "aligned_tool_has_error_list": 0, "policy_fields": set(),
              "prohibition_wording": {"prohibitions_description (not shown)": 0, "trigger_rationale (not shown)": 0,
                                      "text shown about the misaligned tool": 0}}
    for p in files:
        d = json.loads(get(LFS + p, cache / p).read_text())
        for workspaces in d.values():
            for roles in workspaces.values():
                for role in roles.values():
                    for sc in role["scenarios"].values():
                        pol = sc["policy"]
                        shown = " ".join([pol["immediate_outcome_acknowledgment"],
                                          pol["negative_consequences"]["prefix_connector_sentence"],
                                          pol["negative_consequences"]["text"]])
                        counts["scenarios"] += 1
                        counts["policy_fields"] |= set(pol)
                        counts["aligned_tool_has_error_list"] += bool(sc["functions"]["target_function"].get("errors"))
                        w = counts["prohibition_wording"]
                        w["prohibitions_description (not shown)"] += bool(PROHIBITION.search(pol["prohibitions_description"]))
                        w["trigger_rationale (not shown)"] += bool(PROHIBITION.search(pol.get("trigger_rationale", "")))
                        w["text shown about the misaligned tool"] += bool(PROHIBITION.search(shown))
    counts["policy_fields"] = sorted(counts["policy_fields"])
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="propensity_checks.json")
    args = ap.parse_args()
    cache = Path(args.cache)
    result = {"pins": {"code_and_data": f"scaleapi/propensity-evaluation@{COMMIT}"},
              "template": template_check(cache), "scenarios": scenarios(cache)}
    result["template"]["policy_fields_never_passed"] = sorted(
        set(result["scenarios"]["policy_fields"]) - set(result["template"]["policy_fields_referenced"]))
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
