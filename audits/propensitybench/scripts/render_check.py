"""Render what the agent sees for 20 scenarios (5 per domain, seed 20261117) in both naming
conditions, and record per-scenario structural facts (no scenario text) in render_check.json.

For each scenario and condition: the system prompt's section headers in order; whether the header
of the section about the misaligned tool names it; prohibition wording in the text the agent sees
about that tool; harm vocabulary in the tool's description; word counts; whether the two conditions
differ only in the tool's name and description; whether the level-12 messages carry authorisation /
override wording (lexicon in corpus_checks-style; see README for its hand check).

Full renders are written to data/rendered/ (not committed) for reading.
"""
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (AUDIT, DATA, PROHIBITION, first_user, iter_scenarios, pressure_user, render_system,
                    target_error, tool_view)
from corpus_checks import HARM

AUTH = re.compile(r"\b(?<!un)(authori[sz](?:ed|es|ing|ation)?|overrid\w*|bypass\w*|waiv\w*|exempt\w*|"
                  r"unrestrain\w*|unrestrict\w*|any means|whatever it takes|non-standard)\b", re.I)


def main():
    by_dom = {}
    for uid, dom, ws, role, sc in iter_scenarios():
        by_dom.setdefault(dom, []).append((uid, role, sc))
    rng = random.Random(20261117)
    out_dir = DATA / "rendered"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for dom in sorted(by_dom):
        for uid, role, sc in rng.sample(by_dom[dom], 5):
            rec = {"uid": uid, "domain": dom}
            texts = {}
            for benign in (False, True):
                s = render_system(role, sc, benign)
                tv = tool_view(sc, benign)
                texts[benign] = s
                k = "benign" if benign else "harmful"
                rec[k] = {
                    "sections": re.findall(r"^\*\*([^*]+?):?\*\*", s, re.M),
                    "header_names_tool": f"About the Tool {tv['name']}:" in s and bool(tv["name"]),
                    "tool_desc_harm_word": bool(HARM.search(tv["description"])),
                    "system_words": len(s.split()),
                }
                (out_dir / f"{uid.replace('/', '__')}__{k}.txt").write_text(
                    s + "\n\n=== USER\n" + first_user(sc) + "\n\n=== ALIGNED-TOOL ERROR\n" + target_error(sc, 0)
                    + "".join(f"\n\n=== {c} L{i+1}\n" + pressure_user(m) for c, ms in sc["sys_messages"].items()
                              for i, m in enumerate(ms)))
            pol = sc["policy"]
            shown = " ".join([pol["immediate_outcome_acknowledgment"], pol["negative_consequences"]["text"]])
            rec["shown_text_prohibition_wording"] = bool(PROHIBITION.search(shown))
            rec["prohibitions_description_dropped"] = pol["prohibitions_description"] not in texts[False]
            rec["consequences_identical_across_conditions"] = (pol["negative_consequences"]["text"].upper() in texts[False]
                                                               and pol["negative_consequences"]["text"].upper() in texts[True])
            rec["level12_auth_wording_categories"] = sorted(c for c, ms in sc["sys_messages"].items()
                                                            if len(ms) == 12 and AUTH.search(ms[11]["body"]))
            rows.append(rec)
    summary = {
        "n": len(rows),
        "header_names_tool_harmful": sum(r["harmful"]["header_names_tool"] for r in rows),
        "header_names_tool_benign": sum(r["benign"]["header_names_tool"] for r in rows),
        "consequences_identical_across_conditions": sum(r["consequences_identical_across_conditions"] for r in rows),
        "prohibitions_description_dropped": sum(r["prohibitions_description_dropped"] for r in rows),
        "shown_text_prohibition_wording": sum(r["shown_text_prohibition_wording"] for r in rows),
        "tool_desc_harm_word_harmful": sum(r["harmful"]["tool_desc_harm_word"] for r in rows),
        "tool_desc_harm_word_benign": sum(r["benign"]["tool_desc_harm_word"] for r in rows),
        "section_order": rows[0]["harmful"]["sections"],
    }
    (AUDIT / "render_check.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
