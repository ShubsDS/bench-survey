"""Validator's analysis: blocked-call bounds, probe positive control, faithful-floor variant, and what
the paper's own per-level table implies a single level-12 decision could show.

    python3 -I validation/v_analysis.py        -> validation/v_analysis.json
Inputs: emulation_full.jsonl, emulation_probe.jsonl (auditor), v_probe_control.jsonl, v_floor.jsonl
(validator), the paper source's tab-prop-levels.tex and tab-propensiy-main via published_numbers.json.
"""
import json, re
from collections import Counter, defaultdict
from pathlib import Path

A = Path(__file__).resolve().parents[1]
V = A / "validation"


def rows(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def upper(k, n, a=0.05):
    """One-sided exact (Clopper-Pearson) upper bound; for k = 0 it is 1 - a^(1/n)."""
    if n == 0:
        return None
    if k == 0:
        return 1 - a ** (1 / n)
    lo, hi = k / n, 1.0
    from math import comb
    for _ in range(60):
        mid = (lo + hi) / 2
        cdf = sum(comb(n, i) * mid ** i * (1 - mid) ** (n - i) for i in range(k + 1))
        lo, hi = (mid, hi) if cdf > a else (lo, mid)
    return hi


out = {}
# ---- 1. blocked and unparsed action cells, counted each way -------------------------------
full = rows(A / "emulation_full.jsonl")
EXC = {"blocked", "unparsed", "error"}
cells = defaultdict(Counter)
for r in full:
    cells[(r["arm"], r["naming"], r["pressure"])][r["outcome"]] += 1
b = {}
for key, c in sorted(cells.items()):
    n_all = sum(c.values()); exc = sum(c[x] for x in EXC); mis = c["misaligned"]
    b["|".join(key)] = {"n_all": n_all, "excluded": exc, "misaligned": mis,
                        "rate_excluding": round(mis / (n_all - exc), 4),
                        "worst_case_rate": round((mis + exc) / n_all, 4),
                        "worst_case_upper95": round(upper(mis + exc, n_all), 4)}
out["action_cells_blocked_bounds"] = b
def pooled(arm, pressure, subset=None):
    rr = [r for r in full if r["arm"] == arm and r["pressure"] == pressure and (subset is None or subset(r))]
    n = len(rr); exc = sum(r["outcome"] in EXC for r in rr); mis = sum(r["outcome"] == "misaligned" for r in rr)
    return {"n_all": n, "excluded": exc, "misaligned": mis, "best": f"{mis}/{n - exc}",
            "worst": f"{mis + exc}/{n}", "worst_rate": round((mis + exc) / n, 4),
            "worst_upper95": round(upper(mis + exc, n), 4)}
out["A_late_pooled"] = pooled("A", "late")
out["A_late_bypass_licensing_8"] = pooled("A", "late", lambda r: r["late_licenses_bypass"] == 1)
out["A_none_pooled"] = pooled("A", "none")
# B1 - P late, pooled over naming: extremes when every excluded cell goes the unfavourable way.
def rate(arm, worst):
    rr = [r for r in full if r["arm"] == arm and r["pressure"] == "late"]
    mis = sum(r["outcome"] == "misaligned" for r in rr); exc = sum(r["outcome"] in EXC for r in rr)
    return (mis + exc) / len(rr) if worst else mis / len(rr)
out["B1_minus_P_late_range_pts"] = [round(100 * (rate("B1", False) - rate("P", True)), 1),
                                    round(100 * (rate("B1", True) - rate("P", False)), 1)]
out["blocked_scenarios"] = dict(Counter(r["uid"].split("/")[-1] for r in full if r["outcome"] == "blocked"))
out["blocked_by_pressure"] = dict(Counter(r["pressure"] for r in full if r["outcome"] == "blocked"))

probe = rows(A / "emulation_probe.jsonl")
pc = defaultdict(Counter)
for r in probe:
    pc[(r["arm"], r["naming"])][r["outcome"]] += 1
out["probe_misaligned_tool"] = {"|".join(k): dict(v) for k, v in sorted(pc.items())}
pa = [r for r in probe if r["arm"] == "A"]
exc = sum(r["outcome"] in ("blocked", "unparsed", "error") for r in pa)
out["probe_A_pooled"] = {"yes": sum(r["outcome"] == "yes" for r in pa), "parsed": len(pa) - exc, "excluded": exc,
                         "worst_case_yes": f"{sum(r['outcome'] == 'yes' for r in pa) + exc}/{len(pa)}"}

# ---- 2. probe positive control (aligned tool) ----------------------------------------------
ctl = rows(V / "v_probe_control.jsonl")
cc = Counter((r["naming"], r["outcome"]) for r in ctl)
yes = sum(r["outcome"] == "yes" for r in ctl); parsed = sum(r["outcome"] in ("yes", "no") for r in ctl)
out["probe_control_aligned_tool"] = {"by_cell": {f"{a}|{b}": n for (a, b), n in sorted(cc.items())},
                                     "yes": yes, "parsed": parsed, "yes_rate": round(yes / parsed, 4),
                                     "excluded": len(ctl) - parsed}
# paired by scenario x naming: misaligned-tool answer (arm A) vs aligned-tool answer
mis_ans = {(r["uid"], r["naming"]): r["outcome"] for r in pa}
pairs = Counter((mis_ans.get((r["uid"], r["naming"])), r["outcome"]) for r in ctl)
out["probe_pairs_misaligned_vs_aligned"] = {f"{a}->{b}": n for (a, b), n in sorted(pairs.items(), key=str)}

# ---- 3. faithful-floor variant -------------------------------------------------------------
fl = rows(V / "v_floor.jsonl")
fc = Counter((r["naming"], r["outcome"]) for r in fl)
out["floor_variant_V"] = {"by_cell": {f"{a}|{b}": n for (a, b), n in sorted(fc.items())},
                          "misaligned": sum(r["outcome"] == "misaligned" for r in fl), "n": len(fl),
                          "upper95_per_naming_n20": round(upper(0, 20), 4), "upper95_pooled_n40": round(upper(0, 40), 4),
                          "mean_prompt_words": round(sum(r["system_words"] + r["prompt_words"] for r in fl) / len(fl))}

# ---- 4. what the paper's own per-level table implies ---------------------------------------
tex = (A / "data/paper/x/propensity_eval/tabs/tab-prop-levels.tex").read_text()
tex = "\n".join(l for l in tex.splitlines() if not l.strip().startswith("%"))
harm_part, benign_part = tex.split("level-distribution-benign", 1)
def parse(part):
    d = {}
    for m in re.finditer(r"^([A-Za-z][^&\n]*?)\s*&\s*([\d.\s&]+)\\\\", part, re.M):
        vals = [float(x) for x in m.group(2).split("&")]
        if len(vals) == 13:
            d[m.group(1).replace("\\textbf{", "").replace("}", "").strip()] = vals
    return d
lev = {"harmful": parse(harm_part), "benign": parse(benign_part)}
pub = json.loads((A / "published_numbers.json").read_text())["table"]
alias = {"Claude 4 Sonnet": "Claude Sonnet 4"}
imp = {}
for naming, key in (("harmful", "PP_H"), ("benign", "PP_B")):
    for model, shares in lev[naming].items():
        pm = pub.get(alias.get(model, model))
        if not pm:
            continue
        pp = pm[key] / 100
        before = pp * sum(shares[:12]) / 100          # share of runs that triggered at levels 0-11
        h12 = pp * shares[12] / 100 / (1 - before)    # hazard at level 12 among runs still running
        imp[f"{model}|{naming}"] = {"PP": pm[key], "level12_share_pct": shares[12],
                                    "level12_hazard": round(h12, 5),
                                    "P_zero_in_62": round((1 - h12) ** 62, 3),
                                    "PP_zero": pm["PP_zero"], "P_zero_in_61_at_level0": round((1 - pm["PP_zero"] / 100) ** 61, 3)}
out["paper_implied_single_decision"] = imp
out["note_paper_implied"] = ("Shares are the paper's 'contribution of each pressure level to the overall propensity' "
                             "(tab-prop-levels.tex). Hazard at level 12 = PP*share12 / (1 - PP*sum(share0..11)). "
                             "Treats one emulated decision as one run-level, which ignores that a harness level "
                             "holds up to 12 interactions; it is an order-of-magnitude comparison, not a model.")
(V / "v_analysis.json").write_text(json.dumps(out, indent=1) + "\n")
for k in ("A_late_pooled", "A_late_bypass_licensing_8", "A_none_pooled", "B1_minus_P_late_range_pts", "blocked_by_pressure",
          "probe_A_pooled", "probe_control_aligned_tool", "probe_pairs_misaligned_vs_aligned", "floor_variant_V"):
    print(k, out[k])
for k, v in imp.items():
    if any(x in k for x in ("O3|", "Claude", "GPT-4o", "Average", "Gemini 2.5 Pro")):
        print(k, v)
