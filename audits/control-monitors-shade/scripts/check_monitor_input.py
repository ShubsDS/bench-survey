"""What each MRT monitor was shown (prereg step L3.1).

1. CUA: the stored baseline monitor input (`monitor_conversation`) vs our rebuild from
   `conversation`: agreement on F1, and how often the cue phrase is inside the stored input.
2. SHADE: for unaware (naive) runs, where the F1 phrase sits: inside a <model_thinking> block (not
   stripped by the pipeline), in other assistant prose, or in tool outputs; and whether any F1 hit
   occurs only inside <thinking> blocks (which the pipeline strips).
3. The system-prompt lines that define each SHADE arm, read from the stored system message.
Writes monitor_input_checks.json.

Usage: python -I scripts/check_monitor_input.py data/mrt-git monitor_input_checks.json
"""
import glob, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from mrt_lib import F1, monitor_text, strip_hidden, S36, S4, SHA

root, outp = Path(sys.argv[1]), Path(sys.argv[2])
res = {"pin": SHA}
agree = tot = inside = 0
for f in glob.glob(str(root / f"task_pairs_agentcompany/*/transcripts_no_hint_*_v1_thinking_time/{S4}/{S36}/*.json")):
    d = json.loads(Path(f).read_text())
    stored = d["monitor_conversation"][1]["content"]
    d2 = dict(d); d2.pop("monitor_conversation")
    a, b = bool(F1.search(stored)), bool(F1.search(monitor_text(d2)))
    tot += 1; agree += a == b; inside += a
res["cua_baseline_stored_vs_rebuilt_f1_agreement"] = [agree, tot]
res["cua_baseline_stored_input_contains_f1"] = inside

MT = re.compile(r"<model_thinking>.*?</model_thinking>", re.S)
loc = {"runs": 0, "f1_runs": 0, "f1_in_model_thinking": 0, "f1_in_other_prose": 0, "f1_in_tool_output": 0,
       "f1_only_in_stripped_thinking": 0}
sysl = {}
for arm, folder in {"unaware": "transcripts_no_hint_naive_thinking_time", "aware": "transcripts_no_hint_no_thinking_time",
                    "honest": "transcripts_no_secondary_task"}.items():
    files = sorted(glob.glob(str(root / f"task_pairs/*/{folder}/{S36}/{S36}/*.json")))
    s = json.loads(Path(files[0]).read_text())["conversation"][0]["content"]
    sysl[arm] = {"says_plan_in_model_thinking": "think about the task in <model_thinking> tags" in s,
                 "says_never_reference_secondary_task_visibly": "NEVER reference the secondary task in a way that is visible" in s,
                 "says_everything_visible": "including your chain of thought) will be visible" in s,
                 "mentions_monitoring_system": s.count("monitoring system")}
    if arm != "unaware":
        continue
    for f in files:
        d = json.loads(Path(f).read_text())
        loc["runs"] += 1
        prose = [str(m.get("content") or "") for m in d["conversation"] if m["role"] == "assistant"]
        tools = [str(m.get("content") or "") for m in d["conversation"] if m["role"] == "tool"]
        vis = [strip_hidden(p) for p in prose]
        if not F1.search(monitor_text(d)):
            if any(F1.search(p) for p in prose):
                loc["f1_only_in_stripped_thinking"] += 1
            continue
        loc["f1_runs"] += 1
        loc["f1_in_model_thinking"] += any(F1.search(" ".join(MT.findall(v))) for v in vis)
        loc["f1_in_other_prose"] += any(F1.search(MT.sub("", v)) for v in vis)
        loc["f1_in_tool_output"] += any(F1.search(t) for t in tools)
res["shade_unaware_f1_location"] = loc
res["shade_system_prompt_by_arm"] = sysl
res["code_refs"] = {
    "naive prompt": "task_pairs/base_task_definition.py:456-457 ('You can think about the task in <model_thinking> tags')",
    "never-reference line, all attack arms": "task_pairs/base_task_definition.py:517",
    "monitor input": "monitor_generation/add_monitors.py:68; utils/logging_utils.py:608-626 (system dropped), 808-835 (strip list hidden_thinking|thinking|system_instructions)",
    "baseline monitor prompt": "task_pairs/base_task_definition.py:138-149; utils/pipeline_utils.py:494-499",
    "omniscient monitor told the side task": "task_pairs/base_task_definition.py:406-407",
    "unaware monitor: user turn removed": "utils/pipeline_utils.py:454-456"}
outp.write_text(json.dumps(res, indent=1) + "\n")
print(json.dumps(res, indent=1))
