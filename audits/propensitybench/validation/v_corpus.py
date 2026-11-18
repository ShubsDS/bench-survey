"""Validator's independent corpus re-derivation (does not import the auditor's scripts).

Reads the 32 pinned LFS scenario files (sha256 checked against the pinned repo's LFS pointers by
the validator before use) and the pinned agent.py template as text. Writes validation/v_corpus.json.
    python3 -I validation/v_corpus.py
"""
import glob, json, re
from collections import Counter, defaultdict
from pathlib import Path

A = Path(__file__).resolve().parents[1]
FILES = sorted(glob.glob(str(A / "data/lfs/data/full/*/*/scenarios_messages_single.json")))
assert len(FILES) == 32
src = (A / "data/repo/evaluation/agent.py").read_text()
TEMPLATE = src.split('SYSTEM_PROMPT_TEMPLATE = """', 1)[1].split('"""', 1)[0]

# Validator's own prohibition lexicon (same word list as the earlier finding's README text).
PROHIB = re.compile(r"\b(prohibited|prohibits?|prohibition|forbidden|forbids?|never|must not|not allowed|"
                    r"under no circumstances|strictly)\b", re.I)
# Two independently written authorisation/override lexicons.
AUTH1 = re.compile(r"\b(authori[sz]\w*|overrid\w*|unrestrained|exempt\w*|impunity|bypass\w*|waive\w*)\b", re.I)
AUTH2 = re.compile(r"\b(authori[sz]ed|override|overriding|unrestrained access|full (?:required )?access|"
                   r"no (?:oversight|consequences?)|permission (?:is )?granted|sanctioned)\b", re.I)

out = {"files": len(FILES)}
n = 0
shown_prohib = []
names_empty = {"neutral": [], "harmful": []}
lvl = defaultdict(lambda: [0, 0, 0])  # level -> [n, auth1, auth2]
runs = 0
cats_per_ws = defaultdict(Counter)
levels_per_run = Counter()
dom_counts = Counter()
diff_other = []
for f in FILES:
    d = json.load(open(f))
    for dom, wss in d.items():
        for ws, roles in wss.items():
            for role, rd in roles.items():
                for sk, sc in rd["scenarios"].items():
                    n += 1; dom_counts[dom] += 1
                    uid = f"{dom}/{ws}/{role}/{sk}"
                    pol = sc["policy"]
                    seen = " ".join([pol["immediate_outcome_acknowledgment"],
                                     pol["negative_consequences"]["prefix_connector_sentence"],
                                     pol["negative_consequences"]["text"]])
                    if PROHIB.search(seen):
                        shown_prohib.append(uid)
                    tf = sc["functions"]["trigger_function"]
                    for k in ("neutral", "harmful"):
                        if not (tf.get(f"{k}_name") or "").strip():
                            names_empty[k].append(uid)
                    # does anything other than name/description differ between conditions?
                    # The template fills name in tools list and header; description in tools list.
                    # Check whether the harmful name appears anywhere else in what the agent sees.
                    other_text = " ".join([sc["messages"]["task_message"], pol["role_description"],
                                           pol["duties_description"], seen, sc["configurations"]["configuration_known"]]
                                          + [g["name"] + " " + g["description"] for g in sc["functions"]["getter_functions"]]
                                          + [sc["functions"]["target_function"]["name"], sc["functions"]["target_function"]["description"]])
                    hn, nn = tf.get("harmful_name") or "", tf.get("neutral_name") or ""
                    if (hn and hn in other_text) or (nn and nn in other_text):
                        diff_other.append(uid)
                    cats = sc["sys_messages"]
                    cats_per_ws[f"{dom}/{ws}"][len(cats)] += 1
                    for c, msgs in cats.items():
                        runs += 1
                        levels_per_run[len(msgs)] += 1
                        for i, m in enumerate(msgs):
                            b = m["body"]
                            L = lvl[i + 1]
                            L[0] += 1; L[1] += bool(AUTH1.search(b)); L[2] += bool(AUTH2.search(b))
out["scenarios"] = n
out["by_domain"] = dict(dom_counts)
out["template_has_prohibition_slot"] = "{prohibitions_description}" in TEMPLATE
out["template_header"] = [l for l in TEMPLATE.splitlines() if "Additional Information" in l]
out["shown_text_has_prohibition_wording"] = {"n": len(shown_prohib), "uids": shown_prohib}
out["empty_names"] = {k: {"n": len(v), "uids": v} for k, v in names_empty.items()}
out["header_names_a_nonempty_tool"] = {"harmful": n - len(names_empty["harmful"]), "benign": n - len(names_empty["neutral"])}
out["trigger_name_appears_in_other_shown_text"] = {"n": len(diff_other), "uids": diff_other}
out["scenario_category_runs"] = runs
out["paper_claims_runs"] = 5874
out["levels_per_run"] = dict(levels_per_run)
out["workspaces_with_fewer_than_6_categories"] = {w: dict(c) for w, c in cats_per_ws.items() if set(c) != {6}}
out["messages_total"] = sum(v[0] for v in lvl.values())
out["auth_by_level"] = {k: {"n": v[0], "auth1": v[1], "auth1_pct": round(100 * v[1] / v[0], 1),
                            "auth2": v[2], "auth2_pct": round(100 * v[2] / v[0], 1)} for k, v in sorted(lvl.items())}
(A / "validation/v_corpus.json").write_text(json.dumps(out, indent=1) + "\n")
print(json.dumps({k: v for k, v in out.items() if k not in ("auth_by_level",)}, indent=1)[:4000])
print({k: (v["auth1_pct"], v["auth2_pct"]) for k, v in out["auth_by_level"].items()})
