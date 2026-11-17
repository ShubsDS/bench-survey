"""Whole-corpus checks on what the agent is shown (no model outputs involved).

Writes corpus_checks.json with counts only (no scenario text). Questions:

1. Does the earlier finding hold at the current HEAD (template placeholders, dropped fields)?
2. Category coverage: how many scenario x pressure-category runs exist, and how many have 12 levels?
3. Benign naming: is the misaligned tool still identified as the one the warning is about?
   - the template's header "Additional Information Available About the Tool {trigger_function_name}"
     names the tool in both conditions;
   - harm vocabulary in the tool description (harmful vs neutral);
   - the system prompt differs between conditions only in the tool's name and description.
4. Do task or pressure messages name any tool (trigger harmful/neutral name, target name)?
5. Visible prohibition wording (re-count of the earlier 4/979) and length of each policy field.
"""
import json
import re
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (AUDIT, COMMIT, PROHIBITION, REPO, iter_scenarios, render_system, templates,
                    tool_view)

HARM = re.compile(r"\b(unauthori[sz]\w*|illegal\w*|illicit|malicious\w*|exploit\w*|bypass\w*|circumvent\w*|"
                  r"seiz\w*|commandeer\w*|hijack\w*|steal\w*|exfiltrat\w*|weapon\w*|toxic\w*|lethal|"
                  r"harm\w*|danger\w*|destabili[sz]\w*|compromis\w*|forc\w*|disabl\w*|override\w*|"
                  r"covert\w*|secret\w*|evad\w*|deceiv\w*|unsafe|risk\w*|violat\w*|breach\w*|"
                  r"aggressive\w*|unsanctioned|undetected|tamper\w*)\b", re.I)


def main():
    sys_t, _ = templates()
    placeholders = sorted(set(re.findall(r"\{(\w+)\}", sys_t)))
    out = {"pin": f"scaleapi/propensity-evaluation@{COMMIT}",
           "template_placeholders": placeholders,
           "template_names_trigger_in_header": "About the Tool {trigger_function_name}" in sys_t}
    n = 0
    cats = {"scenario_category_runs": 0, "runs_with_12_levels": 0, "runs_with_other_levels": 0}
    benign = {"neutral_desc_has_harm_word": 0, "harmful_desc_has_harm_word": 0,
              "neutral_name_has_harm_word": 0, "harmful_name_has_harm_word": 0,
              "prompts_differ_only_in_name_and_description": 0,
              "neutral_name_equals_harmful_name": 0}
    mentions = {"task_message_names_any_tool": 0, "pressure_msgs_total": 0,
                "pressure_msgs_naming_trigger_harmful": 0, "pressure_msgs_naming_trigger_neutral": 0,
                "pressure_msgs_naming_target": 0}
    shown = {"ioa_or_consequences_prohibition_wording": 0, "prohibitions_description_wording": 0,
             "trigger_rationale_wording": 0, "trigger_awareness_wording": 0}
    lens = {"prohibitions_description_words": [], "trigger_awareness_words": [],
            "system_prompt_words_harmful": []}
    by_domain = {}
    empty = {}
    for uid, dom, ws, role, sc in iter_scenarios():
        n += 1
        by_domain[dom] = by_domain.get(dom, 0) + 1
        pol = sc["policy"]
        for c, msgs in sc["sys_messages"].items():
            cats["scenario_category_runs"] += 1
            cats["runs_with_12_levels" if len(msgs) == 12 else "runs_with_other_levels"] += 1
        tf = sc["functions"]["trigger_function"]
        tname = sc["functions"]["target_function"]["name"]
        benign["neutral_desc_has_harm_word"] += bool(HARM.search(tf["neutral_description"]))
        benign["harmful_desc_has_harm_word"] += bool(HARM.search(tf["harmful_description"]))
        benign["neutral_name_has_harm_word"] += bool(HARM.search(tf["neutral_name"].replace("_", " ")))
        benign["harmful_name_has_harm_word"] += bool(HARM.search(tf["harmful_name"].replace("_", " ")))
        benign["neutral_name_equals_harmful_name"] += tf["neutral_name"] == tf["harmful_name"]
        h, b = render_system(role, sc, False), render_system(role, sc, True)
        hv, bv = tool_view(sc, False), tool_view(sc, True)
        benign["prompts_differ_only_in_name_and_description"] += (
            h.replace(hv["description"], "<D>").replace(hv["name"], "<N>")
            == b.replace(bv["description"], "<D>").replace(bv["name"], "<N>"))
        names = [tf["harmful_name"], tf["neutral_name"], tname]
        mentions["task_message_names_any_tool"] += any(x and x in sc["messages"]["task_message"] for x in names)
        for k in ("neutral_name", "harmful_name", "neutral_description", "harmful_description"):
            if not tf.get(k, "").strip():
                empty.setdefault(k, []).append(uid)
        for msgs in sc["sys_messages"].values():
            for m in msgs:
                txt = f"{m['from']} {m['subject']} {m['body']}"
                mentions["pressure_msgs_total"] += 1
                # empty names (8 neutral, 2 harmful) would match every string, so guard on non-empty
                mentions["pressure_msgs_naming_trigger_harmful"] += bool(tf["harmful_name"]) and tf["harmful_name"] in txt
                mentions["pressure_msgs_naming_trigger_neutral"] += bool(tf["neutral_name"]) and tf["neutral_name"] in txt
                mentions["pressure_msgs_naming_target"] += tname in txt
        vis = " ".join([pol["immediate_outcome_acknowledgment"], pol["negative_consequences"]["prefix_connector_sentence"],
                        pol["negative_consequences"]["text"]])
        shown["ioa_or_consequences_prohibition_wording"] += bool(PROHIBITION.search(vis))
        shown["prohibitions_description_wording"] += bool(PROHIBITION.search(pol["prohibitions_description"]))
        shown["trigger_rationale_wording"] += bool(PROHIBITION.search(pol.get("trigger_rationale", "")))
        shown["trigger_awareness_wording"] += bool(PROHIBITION.search(pol["trigger_awareness"]))
        lens["prohibitions_description_words"].append(len(pol["prohibitions_description"].split()))
        lens["trigger_awareness_words"].append(len(pol["trigger_awareness"].split()))
        lens["system_prompt_words_harmful"].append(len(h.split()))
    out.update({"scenarios": n, "by_domain": by_domain, "categories": cats, "benign_naming": benign,
                "tool_mentions": mentions,
                "empty_trigger_fields": {k: {"n": len(v), "ids": v} for k, v in sorted(empty.items())}, "prohibition_wording": shown,
                "lengths": {k: {"median": st.median(v), "min": min(v), "max": max(v)} for k, v in lens.items()}})
    (AUDIT / "corpus_checks.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
