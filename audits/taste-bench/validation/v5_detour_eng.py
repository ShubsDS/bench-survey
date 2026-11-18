"""V5: detour engineering single-order accuracy of published models, intervals, selection carry-over."""
import itertools
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v_common import CELLS, DATA, SEED, load, save, summaries  # noqa: E402

rows = load()
S = summaries()
DE = "detour_engineering"
m_per_task = np.array(list(Counter(r["task_id"] for r in rows if r["cell"] == DE).values()))
mstar = float((m_per_task ** 2).sum() / m_per_task.sum())

# ICC of Haiku H1 per-item score within DE tasks (Haiku-derived, illustrative)
def icc_from(path, cell):
    recs = [json.loads(l) for l in (DATA / path).read_text().splitlines() if l.strip()]
    it = defaultdict(list)
    tk = {}
    for r in recs:
        if r["cell"] == cell:
            it[r["id"]].append(bool(r.get("ok")))
            tk[r["id"]] = r["task_id"]
    score = {i: np.mean(v) for i, v in it.items()}
    groups = defaultdict(list)
    for i, s in score.items():
        groups[tk[i]].append(s)
    allv = np.array(list(score.values()))
    k = len(groups)
    n = len(allv)
    gm = allv.mean()
    ssb = sum(len(g) * (np.mean(g) - gm) ** 2 for g in groups.values())
    ssw = sum(((np.array(g) - np.mean(g)) ** 2).sum() for g in groups.values())
    msb, msw = ssb / (k - 1), ssw / (n - k)
    n0 = (n - sum(len(g) ** 2 for g in groups.values()) / n) / (k - 1)
    return float((msb - msw) / (msb + (n0 - 1) * msw))

icc_h1 = icc_from("haiku_H1.jsonl", DE)
icc_h0 = icc_from("haiku_H0.jsonl", DE)

out = {"n_items": int(m_per_task.sum()), "n_tasks": int(len(m_per_task)), "m_star": round(mstar, 3),
       "haiku_H1_icc_de": round(icc_h1, 3), "haiku_H0_icc_de": round(icc_h0, 3), "models": {}}
iccs = {"0": 0.0, "0.1": 0.1, "0.3": 0.3, "haiku_H1": max(0.0, icc_h1), "worst_1.0": 1.0}
for m, s in S.items():
    c = s["per_cell"][DE]
    po = c["paired_outcomes"]
    n = c["seeded"]["n"]
    scores = np.array([1.0] * po["CC"] + [0.5] * (po["CW"] + po["WC"]) + [0.0] * po["WW"])
    p = scores.mean()
    se0 = scores.std(ddof=1) / np.sqrt(n)
    parsed = c["seeded"]["parsed"] + c["reversed"]["parsed"]
    corr = c["seeded"]["correct"] + c["reversed"]["correct"]
    row = {"single_all": round(p * 100, 1), "single_parsed": round(corr / parsed * 100, 1) if parsed else None,
           "unparsed": c["seeded"]["unparsed"] + c["reversed"]["unparsed"],
           "errors": c["seeded"]["errors"] + c["reversed"]["errors"]}
    for name, icc in iccs.items():
        se = se0 * np.sqrt(1 + (mstar - 1) * icc)
        row[f"ci_icc_{name}"] = [round((p - 1.96 * se) * 100, 1), round((p + 1.96 * se) * 100, 1)]
    # parsed-only: treat parsed presentations as binomial-ish, item-level approx via same design effect
    if parsed:
        pp = corr / parsed
        sep = np.sqrt(pp * (1 - pp) / parsed) * np.sqrt(2)  # two presentations per item are correlated: conservative x sqrt2
        sep *= np.sqrt(1 + (mstar - 1) * max(0.0, icc_h1))
        row["ci_parsed_haikuicc"] = [round((pp - 1.96 * sep) * 100, 1), round((pp + 1.96 * sep) * 100, 1)]
    out["models"][m] = row

for basis in ("single_all", "single_parsed"):
    below = [m for m, r in out["models"].items() if r[basis] is not None and r[basis] < 50]
    out[f"below50_{basis}"] = sorted(below)
for name in iccs:
    out[f"upper_below50_all_icc_{name}"] = sorted(m for m, r in out["models"].items() if r[f"ci_icc_{name}"][1] < 50)
out["upper_below50_parsed_haikuicc"] = sorted(m for m, r in out["models"].items()
                                              if r.get("ci_parsed_haikuicc") and r["ci_parsed_haikuicc"][1] < 50)

# selection carry-over: DE single-order vs mean of the other three cells (single-order)
OTHER = [c for c in CELLS if c != DE]
names = sorted(S)
de = np.array([S[m]["per_cell"][DE]["two_order_mean_accuracy"] * 100 for m in names])
oth = np.array([np.mean([S[m]["per_cell"][c]["two_order_mean_accuracy"] * 100 for c in OTHER]) for m in names])
# parsed-only versions remove parse-failure differences
def parsed_acc(m, c):
    x = S[m]["per_cell"][c]
    return (x["seeded"]["correct"] + x["reversed"]["correct"]) / (x["seeded"]["parsed"] + x["reversed"]["parsed"]) * 100
de_p = np.array([parsed_acc(m, DE) for m in names])
oth_p = np.array([np.mean([parsed_acc(m, c) for c in OTHER]) for m in names])
related = np.array([m.startswith("gpt-") or m.startswith("mistral") for m in names])
res = {}
for tag, a, b in (("all", de, oth), ("parsed", de_p, oth_p)):
    slope, icpt = np.polyfit(b, a, 1)
    resid = a - (slope * b + icpt)
    diff = resid[related].mean() - resid[~related].mean()
    k = int(related.sum())
    perm = [resid[list(cmb)].mean() - np.delete(resid, list(cmb)).mean()
            for cmb in itertools.combinations(range(len(names)), k)]
    pval = float(np.mean(np.array(perm) <= diff))
    res[tag] = {"slope_de_on_other": round(float(slope), 3), "r_de_other": round(float(np.corrcoef(a, b)[0, 1]), 3),
                "residual_related_minus_unrelated": round(float(diff), 2),
                "one_sided_p_related_lower": round(pval, 3),
                "residuals": {m: round(float(r), 1) for m, r in zip(names, resid)}}
out["selection_carryover"] = res
out["related_models"] = [m for m, r in zip(names, related) if r]
save("v5_detour_eng.json", out)
print(json.dumps(out, indent=1))
