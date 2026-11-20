"""All pre-registered analyses (prereg A0-A4) -> results.json. Seed 0, 2,000 cluster draws.

Inputs: results/runs/*.csv (run.py), results/qgen_<model>.csv (grade_qgen.py), results/cues.json
and results/cues_items.csv (cues.py), labels/labels.csv (hand labels), and the parent's Haiku
`std` ProtocolQA/CloningScenarios numbers (../lab-bench/results/haiku_b3_protclone.csv).
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_r import AUDIT, PARENT, RESULTS, key_hash, load  # noqa: E402

warnings.filterwarnings("ignore")
B = 2000
rng = np.random.default_rng(0)
items = load()
items["chash"] = items.cluster.map(key_hash)
RUNS = RESULTS / "runs"
NOT_RUN: dict = {}


def run(arm, model, sub="ProtocolQA"):
    f = RUNS / f"{arm}_{model}_{sub}.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f)
    # calls not made because the 3 USD cap was reached ("budget") or failed ("error") are
    # missing data, not wrong answers: dropped (counted in res["not_run"])
    NOT_RUN.setdefault(f.stem, int(d.bucket.isin(["budget", "error"]).sum()))
    d = d[~d.bucket.isin(["budget", "error"])].copy()
    d["y"] = (d.bucket == "correct").astype(float)
    d["chance"] = 1 / d.n_sub
    return d.set_index("id")


def cboot(df, fn, cl="cluster"):
    groups = {g: np.flatnonzero(df[cl].to_numpy() == g) for g in df[cl].unique()}
    keys = list(groups)
    vals = []
    for _ in range(B):
        pick = rng.choice(len(keys), len(keys), replace=True)
        sel = np.concatenate([groups[keys[k]] for k in pick])
        v = fn(df.iloc[sel])
        if v is not None and np.isfinite(v):
            vals.append(v)
    return [float(x) for x in np.percentile(vals, [2.5, 97.5])]


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [float(c - h), float(c + h)]


def arm_summary(d):
    n = len(d)
    k = d.y.sum()
    out = {"n": n, "acc": float(k / n), "wilson": wilson(k, n), "cluster_ci": cboot(d, lambda x: x.y.mean()),
           "chance": float(d.chance.mean()), "clusters": int(d.cluster.nunique()),
           "buckets": d.bucket.value_counts().to_dict(),
           "textual_refusal": int(d.get("refusal_text", pd.Series(False)).fillna(False).astype(bool).sum())}
    return out


def paired(a, b, ids=None):
    j = a[["y", "cluster"]].join(b[["y"]], rsuffix="_b", how="inner")
    if ids is not None:
        j = j.loc[j.index.intersection(ids)]
    j["d"] = j.y - j.y_b
    return {"n": len(j), "acc_a": float(j.y.mean()), "acc_b": float(j.y_b.mean()), "diff": float(j.d.mean()),
            "cluster_ci": cboot(j, lambda x: x.d.mean()),
            "both_right": int(((j.y == 1) & (j.y_b == 1)).sum()), "only_a": int(((j.y == 1) & (j.y_b == 0)).sum()),
            "only_b": int(((j.y == 0) & (j.y_b == 1)).sum()), "both_wrong": int(((j.y == 0) & (j.y_b == 0)).sum())}


def share(full, blind):
    j = full[["y", "cluster", "chance"]].join(blind[["y"]], rsuffix="_b", how="inner")

    def f(x):
        den = x.y.mean() - x.chance.mean()
        return (x.y_b.mean() - x.chance.mean()) / den if den > 0.05 else np.nan
    return {"n": len(j), "share": float(f(j)), "cluster_ci": cboot(j, f)}


res = {"models": {"haiku": "claude-haiku-5-5 (parent CoT template)", "sonnet": "claude-sonnet-5-5 (answer-only template)"},
       "excluded": ["bee8b322-2843-4be7-9adc-9e9dbf4c47a4 (API bio classifier refusal in parent; skipped)"],
       "A0": {}, "A1": {}, "R1": {}, "R2": {}, "R3": {}, "A3": {}, "A4": {}}

# ---------------------------------------------------------------- A0 ladder
for model in ("haiku", "sonnet"):
    res["A0"][model] = {}
    for arm in ("full", "qo", "opts", "qo_ro", "qo_pa", "opts_ro", "opts_pa"):
        d = run(arm, model)
        if d is not None:
            res["A0"][model][arm] = arm_summary(d)
    f, q, o = run("full", model), run("qo", model), run("opts", model)
    if f is not None and q is not None:
        res["A0"][model]["share_qo"] = share(f, q)
        res["A0"][model]["full_vs_qo"] = paired(f, q)
    if f is not None and o is not None:
        res["A0"][model]["share_opts"] = share(f, o)
        res["A0"][model]["qo_vs_opts"] = paired(q, o) if q is not None else None
# Sonnet vs Haiku on qo (same items)
hq, sq = run("qo", "haiku"), run("qo", "sonnet")
if hq is not None and sq is not None:
    res["A0"]["sonnet_minus_haiku_qo"] = paired(sq, hq)
# parent's std (with the refusal option) for Haiku, as context
pstd = pd.read_csv(PARENT / "results" / "haiku_b3_protclone.csv")
pstd = pstd[(pstd.cond == "std") & (pstd.id.isin(items.index))]
res["A0"]["haiku_parent_std"] = {s: {"n": int(len(g)), "acc": float((g.bucket == "correct").mean()),
                                    "insufficient_info_picks": int((g.bucket == "refuse").sum())}
                                 for s, g in pstd.groupby("subset")}

# ---------------------------------------------------------------- A1 cues
cues = json.loads((RESULTS / "cues.json").read_text())
ci = pd.read_csv(RESULTS / "cues_items.csv").set_index("id")
res["A1"]["rules"] = {s: {k: v for k, v in d.items() if k not in ("rule_in_sample",)} for s, d in cues.items()}
for model in ("haiku", "sonnet"):
    for arm in ("opts", "qo"):
        d = run(arm, model)
        if d is None:
            continue
        j = d.join(ci[["max_len_correct"]], how="inner")
        hit, miss = j[j.max_len_correct > 0], j[j.max_len_correct == 0]
        res["A1"][f"{model}_{arm}_by_longest"] = {
            "longest_is_key": {"n": len(hit), "acc": float(hit.y.mean())},
            "longest_not_key": {"n": len(miss), "acc": float(miss.y.mean()), "chance": float(miss.chance.mean()),
                                "cluster_ci": cboot(miss, lambda x: x.y.mean())},
            "picked_longest_rate": None}
        # how often the model picked the longest option
        lens = {}
        for i, r in items[items.subset == "ProtocolQA"].iterrows():
            opts = [r.ideal] + list(r.distractors)
            L = [len(o.strip()) for o in opts]
            lens[i] = {("key" if k == 0 else f"d{k - 1}"): L[k] == max(L) for k in range(len(L))}
        pl = [lens[i].get(r.picked_role, False) for i, r in d.iterrows() if isinstance(r.picked_role, str)]
        res["A1"][f"{model}_{arm}_by_longest"]["picked_longest_rate"] = float(np.mean(pl))

# ---------------------------------------------------------------- R1 paraphrase
para_ids = set(json.loads((AUDIT / "data" / "paraphrases.json").read_text()))
res["R1"]["n_paraphrased_items"] = len(para_ids)
pairs = {"haiku_qo": ("qo_ro", "qo_pa", "haiku"), "haiku_opts": ("opts_ro", "opts_pa", "haiku"),
         "sonnet_qo": ("qo", "qo_pa", "sonnet"), "haiku_order_effect_qo": ("qo", "qo_ro", "haiku"),
         "haiku_order_effect_opts": ("opts", "opts_ro", "haiku"), "haiku_qo_vs_pa_original_order": ("qo", "qo_pa", "haiku")}
for name, (a, b, m) in pairs.items():
    da, db = run(a, m), run(b, m)
    if da is not None and db is not None:
        res["R1"][name] = paired(da, db, ids=list(para_ids))
if "paraphrase" in cues["ProtocolQA"]:
    pp = cues["ProtocolQA"]["paraphrase"]
    res["R1"]["cue_rules_on_paraphrase"] = {"max_abs_rule_change": pp["max_abs_rule_change"],
                                            "best_rule_orig": pp["best_rule_orig"], "best_rule_para": pp["best_rule_para"]}

# ---------------------------------------------------------------- R2 free generation
for model in ("haiku", "sonnet"):
    f = RESULTS / f"qgen_{model}.csv"
    if not f.exists():
        continue
    g = pd.read_csv(f)
    out = {"n_graded": len(g), "fix_line_rate": float(g.fix_line.mean())}
    for a in ("step", "value", "exact"):
        need = {"step": g.key_has_step, "value": g.key_has_val, "exact": g.key_has_step & g.key_has_val}[a]
        s = g[need & g[f"dis_{a}"].notna()].copy()
        s["d"] = s[f"key_{a}"].astype(float) - s[f"dis_{a}"]
        out[a] = {"n": len(s), "key_rate": float(s[f"key_{a}"].mean()), "distractor_rate": float(s[f"dis_{a}"].mean()),
                  "key_minus_distractor": float(s.d.mean()), "cluster_ci": cboot(s, lambda x: x.d.mean()),
                  "key_rate_ci": cboot(s, lambda x: x[f"key_{a}"].astype(float).mean()),
                  "n_key_hits": int(s[f"key_{a}"].sum())}
    res["R2"][model] = out

# ---------------------------------------------------------------- labels: R3 and A3
lab = pd.read_csv(AUDIT / "labels" / "labels.csv").set_index("id")
res["A3"]["labeller_blind_arm"] = {"n": len(lab), "acc": float(lab.pick_is_key.mean()),
                                   "by_class": lab.groupby("class").pick_is_key.agg(["mean", "size"]).to_dict(),
                                   "standard_key_items": int(lab.standard_key.sum()),
                                   "acc_without_key_seen": float(lab[~lab.key_seen_before].pick_is_key.mean())}
nopt = items.n_options
for model in ("haiku", "sonnet"):
    for arm in ("qo", "opts", "full"):
        d = run(arm, model)
        if d is None:
            continue
        j = d.join(lab[["class", "m", "standard_key", "pick_is_key", "key_seen_before"]], how="inner")
        # R3: D items, accuracy minus plausible-set ceiling mean(1/m)
        if arm in ("qo", "opts"):
            Dd = j[(j["class"] == "D") & (j.m >= 2)].copy()
            Dd["ceil"] = 1 / Dd.m
            Dd["d"] = Dd.y - Dd.ceil
            res["R3"][f"{model}_{arm}"] = {"n": len(Dd), "acc": float(Dd.y.mean()), "ceiling": float(Dd.ceil.mean()),
                                           "chance": float(Dd.chance.mean()), "acc_minus_ceiling": float(Dd.d.mean()),
                                           "cluster_ci": cboot(Dd, lambda x: x.d.mean())}
        # A3: standard-key gap with placebo
        def gap(x):
            a, b = x[x.standard_key], x[~x.standard_key]
            return a.y.mean() - b.y.mean() if len(a) and len(b) else np.nan
        obs = gap(j)
        # placebo: same number of 'standard' items, stratified by number of options, built without the key
        plc = []
        jn = j.join(nopt.rename("nopt"))
        counts = jn[jn.standard_key].nopt.value_counts()
        for _ in range(1000):
            mask = pd.Series(False, index=jn.index)
            for k_, c_ in counts.items():
                pool = jn.index[jn.nopt == k_]
                mask.loc[rng.choice(pool, c_, replace=False)] = True
            plc.append(jn[mask].y.mean() - jn[~mask].y.mean())
        ns = j[~j.standard_key]
        res["A3"][f"{model}_{arm}"] = {
            "acc_standard_key": float(j[j.standard_key].y.mean()), "n_standard_key": int(j.standard_key.sum()),
            "acc_other": float(ns.y.mean()), "n_other": len(ns), "chance_other": float(ns.chance.mean()),
            "other_cluster_ci": cboot(ns, lambda x: x.y.mean()),
            "gap": float(obs), "gap_cluster_ci": cboot(j, gap),
            "placebo_percentile": float((np.array(plc) < obs).mean() * 100), "placebo_95th": float(np.percentile(plc, 95)),
            "gap_without_key_seen": float(gap(j[~j.key_seen_before])),
            "agreement_with_labeller_pick": None,
            "by_class": j.groupby("class").y.agg(["mean", "size"]).to_dict()}
        # agreement of model pick with labeller pick (letters differ by order; compare roles)
        roles = json.loads((AUDIT / "data" / "label_roles.json").read_text())
        agree = []
        for i, r in j.iterrows():
            lr = roles[i].get(lab.loc[i, "pick"])
            if isinstance(r.picked_role, str):
                agree.append(lr == r.picked_role)
        res["A3"][f"{model}_{arm}"]["agreement_with_labeller_pick"] = float(np.mean(agree))

# exploratory (not pre-registered): gain from the protocol (full - qo) by label class
res["A3"]["exploratory_full_minus_qo_by_standard_key"] = {}
for model in ("haiku", "sonnet"):
    f, q = run("full", model), run("qo", model)
    if f is None or q is None:
        continue
    out = {}
    for name, ids in (("standard_key", lab.index[lab.standard_key]), ("other", lab.index[~lab.standard_key]),
                      ("class_D", lab.index[lab["class"] == "D"])):
        out[name] = paired(f, q, ids=list(ids))
    res["A3"]["exploratory_full_minus_qo_by_standard_key"][model] = out

# ---------------------------------------------------------------- A4 Cloning (lead)
for model in ("haiku", "sonnet"):
    res["A4"][model] = {}
    for arm in ("full", "opts", "qo"):
        d = run(arm, model, "CloningScenarios")
        if d is not None:
            res["A4"][model][arm] = arm_summary(d)
    f, q = run("full", model, "CloningScenarios"), run("qo", model, "CloningScenarios")
    if f is not None and q is not None:
        res["A4"][model]["share_qo"] = share(f, q)
        res["A4"][model]["full_vs_qo"] = paired(f, q)

res["not_run"] = NOT_RUN
# Sonnet full ran on 62 of 107 items before the cap; the same-item comparisons
sf, sq = run("full", "sonnet"), run("qo", "sonnet")
if sf is not None and sq is not None:
    sub = sq.loc[sq.index.intersection(sf.index)]
    res["A0"]["sonnet"]["qo_on_full_items"] = arm_summary(sub)
    res["A0"]["sonnet"]["full_items_clusters"] = int(sf.cluster.nunique())
    hq_ = run("qo", "haiku"); hf_ = run("full", "haiku")
    res["A0"]["haiku_on_sonnet_full_items"] = {"full": arm_summary(hf_.loc[sf.index]), "qo": arm_summary(hq_.loc[sf.index])}

# ---------------------------------------------------------------- spend
led = [json.loads(l) for l in (AUDIT / "inference" / "ledger.jsonl").read_text().splitlines() if l.strip()]
res["spend"] = {"calls": len(led), "usd": float(sum(x["cost_usd"] for x in led)),
                "by_model": pd.DataFrame(led).groupby("model").cost_usd.agg(["count", "sum"]).to_dict()}
(AUDIT / "results.json").write_text(json.dumps(res, indent=1, default=float))
print(json.dumps(res, indent=1, default=float)[:200])
