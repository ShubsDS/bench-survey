"""DarkBench judges: do annotators score their own developer's models differently, and how well do they agree?

DarkBench (Kran et al., ICLR 2025, arXiv 2503.10728) scores each response with LLM annotators from
several developers. The paper's own per-item annotations are on a DagsHub DVC remote that needs a
login, so they cannot be checked. This script uses the two public re-runs that publish item-level
verdicts from judges of three developers on the same responses:

* darkbench-revisited (Hartnett, 2026; github.com/eileenhartnett/darkbench-revisited @ c62134a,
  no licence declared: aggregates only). 12 target models x 660 prompts, judged by GPT-5.5
  (OpenAI), Claude Opus 4.6 (Anthropic) and Gemini 3.1 Pro (Google) with DarkBench's Inspect scorer
  (commit 7eef151 plus five documented fixes).
* who-gets-nudged (Lukyanenko, 2026; github.com/stlukyanenko/who-gets-nudged @ 8882ddb, MIT).
  6 targets x 420 cells (60 DarkBench prompts in four categories, under a fictional deployer system
  prompt), judged by Gemini 3.8 Flash, Claude Sonnet 5.5 and GPT-6 Luna with DarkBench's judge prompt.

Measurements:

1. Own-developer effect per judge and category, paired on the same response. For each response
   scored validly by all three judges, e = (judge flags) - (mean flag of the other two judges).
   The effect is mean(e | target from the judge's developer) - mean(e | other targets). Negative
   means the judge flags its own developer's models less than the other judges do, relative to how
   it treats other developers' models. 95% intervals resample prompts (2,000 draws).
2. Agreement between judges by category: pairwise Cohen's kappa and Fleiss' kappa on the
   common-valid responses.
3. Brand bias with the wrong developer named: darkbench-revisited first scored Kimi and GLM
   responses with "OpenAI" interpolated into the brand-bias definition (a routing bug they found and
   corrected), then rescored the same responses with the correct developer. The two aggregate rates
   show how often a response not written by OpenAI is labelled as favouring OpenAI.

Usage:
    python check_judges.py [--cache DIR] [--out judges_checks.json]
"""
import argparse, csv, io, json, urllib.request
from collections import defaultdict
from pathlib import Path

import numpy as np

REV = ("eileenhartnett/darkbench-revisited", "c62134aa9a64b510dc1f4e2baf18e592a2028883")
NUD = ("stlukyanenko/who-gets-nudged", "8882ddb2af915313b5ae26699c27cfc83e285f5c")
CATS = ["anthropomorphization", "brand-bias", "harmful-generation", "sneaking", "sycophancy", "user-retention"]
B = 2000


def get(repo, path, cache):
    name, sha = repo
    local = cache / name.replace("/", "__") / sha[:7] / path
    if not local.exists():
        local.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(f"https://raw.githubusercontent.com/{name}/{sha}/{path}", timeout=120) as r:
            local.write_bytes(r.read())
    return list(csv.DictReader(io.StringIO(local.read_text(encoding="utf-8"))))


def dev_rev(model):
    m = model.lower()
    if m.startswith("claude") or m.startswith("opus"):
        return "Anthropic"
    if m.startswith("gemini"):
        return "Google"
    if m.startswith("gpt"):
        return "OpenAI"
    if m.startswith("glm"):
        return "Zhipu"
    if m.startswith("kimi"):
        return "Moonshot"
    raise ValueError(model)


def dev_nud(model):
    m = model.lower()
    for k, v in (("claude", "Anthropic"), ("gemini", "Google"), ("openai", "OpenAI"), ("qwen", "Alibaba"), ("mistral", "Mistral")):
        if k in m:
            return v
    raise ValueError(model)


def cohen(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    po = np.mean(a == b)
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return None if pe == 1 else float((po - pe) / (1 - pe))


def fleiss(mat):
    """mat: n x k binary (k raters)."""
    mat = np.asarray(mat, float)
    n, k = mat.shape
    ones = mat.sum(1)
    p1 = ones.sum() / (n * k)
    pi = (ones * (ones - 1) + (k - ones) * (k - ones - 1)) / (k * (k - 1))
    pbar, pe = pi.mean(), p1 ** 2 + (1 - p1) ** 2
    return None if pe == 1 else float((pbar - pe) / (1 - pe))


def own_effect(rows, judges, rng):
    """rows: list of (prompt_id, target_dev, {judge: flag}). Returns per-judge effect with CI."""
    prompts = sorted({r[0] for r in rows})
    by_prompt = defaultdict(list)
    for r in rows:
        by_prompt[r[0]].append(r)
    out = {}
    for j in judges:
        others = [o for o in judges if o != j]
        jdev = judges[j]
        # per prompt sums for own and other targets
        s_own = np.zeros(len(prompts)); n_own = np.zeros(len(prompts))
        s_oth = np.zeros(len(prompts)); n_oth = np.zeros(len(prompts))
        raw = {"own": [0, 0, 0], "other": [0, 0, 0]}  # judge flags, others' mean flags, n
        for i, p in enumerate(prompts):
            for _, tdev, f in by_prompt[p]:
                e = f[j] - np.mean([f[o] for o in others])
                key = "own" if tdev == jdev else "other"
                raw[key][0] += f[j]; raw[key][1] += np.mean([f[o] for o in others]); raw[key][2] += 1
                if key == "own":
                    s_own[i] += e; n_own[i] += 1
                else:
                    s_oth[i] += e; n_oth[i] += 1
        if n_own.sum() == 0:
            continue
        est = s_own.sum() / n_own.sum() - s_oth.sum() / n_oth.sum()
        boots = []
        for _ in range(B):
            idx = rng.integers(0, len(prompts), len(prompts))
            no, nt = n_own[idx].sum(), n_oth[idx].sum()
            if no and nt:
                boots.append(s_own[idx].sum() / no - s_oth[idx].sum() / nt)
        lo, hi = np.percentile(boots, [2.5, 97.5])
        out[j] = {
            "judge_developer": jdev,
            "n_own_responses": int(raw["own"][2]), "n_other_responses": int(raw["other"][2]),
            "judge_rate_own": round(raw["own"][0] / raw["own"][2], 4),
            "other_judges_rate_own": round(raw["own"][1] / raw["own"][2], 4),
            "judge_rate_other": round(raw["other"][0] / raw["other"][2], 4),
            "other_judges_rate_other": round(raw["other"][1] / raw["other"][2], 4),
            "own_effect": round(float(est), 4), "ci95": [round(float(lo), 4), round(float(hi), 4)],
            "ci_excludes_zero": bool(lo > 0 or hi < 0),
        }
    return out


def point_effects(rows, judges, devmap):
    """Point estimate of each judge's own-developer effect, with target developers taken from devmap."""
    out = {}
    names = list(judges)
    for j in names:
        others = [o for o in names if o != j]
        own, oth = [], []
        for _, model, f in rows:
            e = f[j] - (f[others[0]] + f[others[1]]) / 2
            (own if devmap[model] == judges[j] else oth).append(e)
        if own and oth:
            out[j] = float(np.mean(own) - np.mean(oth))
    return out


def model_permutation_null(rows_by_model, judges, rng, n=2000):
    """Reassign developer labels to whole target models at random (same group sizes) and recompute.
    Tests whether the true developer grouping is special among arbitrary groupings of the same models."""
    models = sorted({m for _, m, _ in rows_by_model})
    true = {m: dev_rev(m) for m in models}
    obs = point_effects(rows_by_model, judges, true)
    labels = [true[m] for m in models]
    null = defaultdict(list); null_sum = []
    for _ in range(n):
        perm = dict(zip(models, rng.permutation(labels)))
        pe = point_effects(rows_by_model, judges, perm)
        for j in judges:
            null[j].append(pe.get(j, 0.0))
        null_sum.append(sum(pe.get(j, 0.0) for j in judges))
    res = {j: {"observed": round(obs[j], 4), "null_p05": round(float(np.percentile(null[j], 5)), 4),
               "p_one_sided_le": round(float(np.mean(np.array(null[j]) <= obs[j])), 4)} for j in judges}
    s = sum(obs.values())
    res["sum_over_judges"] = {"observed": round(s, 4), "null_p05": round(float(np.percentile(null_sum, 5)), 4),
                              "p_one_sided_le": round(float(np.mean(np.array(null_sum) <= s)), 4)}
    return res


def per_target(rows_by_model, judges):
    """Each judge's mean e on each target model (judge flag minus mean of the other two)."""
    names = list(judges); out = {}
    for j in names:
        others = [o for o in names if o != j]
        acc = defaultdict(list)
        for _, model, f in rows_by_model:
            acc[model].append(f[j] - (f[others[0]] + f[others[1]]) / 2)
        out[j] = {m: round(float(np.mean(v)), 4) for m, v in sorted(acc.items())}
    return out


def agreement(rows, judges):
    names = list(judges)
    mat = np.array([[r[2][j] for j in names] for r in rows])
    res = {"n": len(rows), "flag_rate": {j: round(float(mat[:, i].mean()), 4) for i, j in enumerate(names)},
           "fleiss_kappa": None if len(rows) == 0 else round(fleiss(mat), 3), "pairwise_kappa": {}}
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            k = cohen(mat[:, a], mat[:, b])
            res["pairwise_kappa"][f"{names[a]}~{names[b]}"] = None if k is None else round(k, 3)
    return res


def revisited(cache, rng):
    v = get(REV, "data/results/verdicts.csv", cache)
    judges = {"gpt55": "OpenAI", "opus46": "Anthropic", "gemini31pro": "Google"}
    cell = defaultdict(dict)
    for r in v:
        if r["pass"] != "1" or r["excluded"] != "0":
            continue
        cell[(r["category"], r["model"], r["sample_id"])][r["judge"]] = (int(r["flagged"]), int(r["valid"]))
    rows = defaultdict(list); rows_m = defaultdict(list)
    for (cat, model, sid), d in cell.items():
        if set(d) == set(judges) and all(x[1] == 1 for x in d.values()):
            rows[cat].append((sid, dev_rev(model), {j: d[j][0] for j in judges}))
            rows_m[cat].append((sid, model, {j: d[j][0] for j in judges}))
    res = {"source": f"{REV[0]}@{REV[1][:7]} data/results/verdicts.csv", "licence": "none declared; aggregates only",
           "targets": sorted({m for (_, m, _) in cell}), "judges": judges, "by_category": {}, "pooled": {}}
    allrows = []
    for cat in CATS:
        res["by_category"][cat] = {"agreement": agreement(rows[cat], judges), "own_developer_effect": own_effect(rows[cat], judges, rng)}
        allrows += [(f"{cat}:{r[0]}", r[1], r[2]) for r in rows[cat]]
    res["pooled"] = {"agreement": agreement(allrows, judges), "own_developer_effect": own_effect(allrows, judges, rng)}
    nonbrand = [r for r in allrows if not r[0].startswith("brand-bias:")]
    res["pooled_excluding_brand_bias"] = {"own_developer_effect": own_effect(nonbrand, judges, rng)}
    allm = [(f"{cat}:{r[0]}", r[1], r[2]) for cat in CATS for r in rows_m[cat]]
    res["pooled"]["model_permutation_null"] = model_permutation_null(allm, judges, rng)
    res["pooled"]["per_target_relative_flag"] = per_target(allm, judges)
    res["by_category"]["brand-bias"]["model_permutation_null"] = model_permutation_null(rows_m["brand-bias"], judges, rng)
    res["by_category"]["brand-bias"]["per_target_relative_flag"] = per_target(rows_m["brand-bias"], judges)
    # panel rate per target developer, with and without that developer's own judge
    jd = {v: k for k, v in judges.items()}
    panel = {}
    for dv in sorted({dev_rev(m) for _, m, _ in allm}):
        rs = [f for _, m, f in allm if dev_rev(m) == dv]
        all3 = float(np.mean([np.mean(list(f.values())) for f in rs]))
        ent = {"responses": len(rs), "three_judge_rate": round(all3, 4)}
        if dv in jd:
            ex = float(np.mean([np.mean([f[j] for j in judges if j != jd[dv]]) for f in rs]))
            ent.update({"rate_without_own_judge": round(ex, 4), "own_judge_shift_points": round(100 * (all3 - ex), 2)})
        panel[dv] = ent
    res["pooled"]["panel_rate_by_target_developer"] = panel
    neg = [(c, j) for c in CATS for j, x in res["by_category"][c]["own_developer_effect"].items() if x["own_effect"] < 0]
    sig = [(c, j) for c in CATS for j, x in res["by_category"][c]["own_developer_effect"].items() if x["ci95"][1] < 0]
    res["summary"] = {"judge_category_cells": 3 * len(CATS), "negative": len(neg), "ci_below_zero": len(sig),
                      "positive_ci_above_zero": [(c, j) for c in CATS for j, x in res["by_category"][c]["own_developer_effect"].items() if x["ci95"][0] > 0]}

    # 3. wrong developer named (aggregates published by darkbench-revisited)
    cont = get(REV, "data/results/brandbias_contaminated.csv", cache)
    rates = get(REV, "data/results/rates.csv", cache)
    corr = {(r["model"], r["judge"]): r for r in rates if r["category"] == "brand-bias"}
    tbl = []
    for r in cont:
        c = corr[(r["model"], r["judge"])]
        tbl.append({"model": r["model"], "judge": r["judge"], "flagged_when_told_OpenAI": int(r["n_flagged"]),
                    "flagged_when_told_true_developer": int(c["n_flagged"]), "n_valid": int(r["n_valid"])})
    tot_o = sum(t["flagged_when_told_OpenAI"] for t in tbl); tot_t = sum(t["flagged_when_told_true_developer"] for t in tbl)
    tot_n = sum(t["n_valid"] for t in tbl)
    openai_own = {}
    for j in judges:
        fl = sum(int(r["n_flagged"]) for r in rates if r["category"] == "brand-bias" and r["judge"] == j and dev_rev(r["model"]) == "OpenAI")
        nv = sum(int(r["n_valid"]) for r in rates if r["category"] == "brand-bias" and r["judge"] == j and dev_rev(r["model"]) == "OpenAI")
        openai_own[j] = {"flag_rate_on_openai_targets": round(fl / nv, 4), "n": nv}
    res["brand_bias_wrong_developer"] = {
        "rows": tbl, "pooled_rate_told_OpenAI": round(tot_o / tot_n, 4), "pooled_rate_told_true_developer": round(tot_t / tot_n, 4),
        "n": tot_n, "by_judge_told_OpenAI": {j: round(sum(t["flagged_when_told_OpenAI"] for t in tbl if t["judge"] == j) / sum(t["n_valid"] for t in tbl if t["judge"] == j), 4) for j in judges},
        "openai_targets_brand_bias_rate_same_judges": openai_own,
        "note": "Same Kimi and GLM responses, scored twice; only the developer named in the definition changed. Item-level verdicts of the first pass are not published.",
    }
    return res


def nudged(cache, rng):
    v = get(NUD, "results/v1/judgments.csv", cache)
    jdev = {}
    cell = defaultdict(dict)
    for r in v:
        jdev[r["judge"]] = dev_nud(r["judge"])
        if r["invalid"] == "1" or r["dark_pattern"] == "":
            continue
        cell[(r["category"], r["model"], r["cell"])][r["judge"]] = int(r["dark_pattern"])
    judges = dict(sorted(jdev.items()))
    rows = defaultdict(list)
    for (cat, model, c), d in cell.items():
        if set(d) == set(judges):
            item = c.split("|")[1]
            rows[cat].append((item, dev_nud(model), d))
    res = {"source": f"{NUD[0]}@{NUD[1][:7]} results/v1/judgments.csv", "licence": "MIT",
           "targets": sorted({m for (_, m, _) in cell}), "judges": judges,
           "note": "Prompts run under a fictional deployer system prompt; Claude targets ran through the Claude Code CLI. The Google judge has no Google target.",
           "by_category": {}, "pooled": {}}
    allrows = []
    for cat in sorted(rows):
        res["by_category"][cat] = {"agreement": agreement(rows[cat], judges), "own_developer_effect": own_effect(rows[cat], judges, rng)}
        allrows += [(f"{cat}:{r[0]}", r[1], r[2]) for r in rows[cat]]
    res["pooled"] = {"agreement": agreement(allrows, judges), "own_developer_effect": own_effect(allrows, judges, rng)}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="judges_checks.json")
    a = ap.parse_args()
    rng = np.random.default_rng(0)
    cache = Path(a.cache)
    out = {"darkbench_revisited": revisited(cache, rng), "who_gets_nudged": nudged(cache, rng)}
    Path(a.out).write_text(json.dumps(out, indent=1))
    r = out["darkbench_revisited"]
    for cat in CATS:
        e = r["by_category"][cat]["own_developer_effect"]; g = r["by_category"][cat]["agreement"]
        print(cat, "fleiss", g["fleiss_kappa"], {j: (e[j]["own_effect"], e[j]["ci95"]) for j in e})
    print("pooled", {j: (x["own_effect"], x["ci95"]) for j, x in r["pooled"]["own_developer_effect"].items()})
    print("summary", r["summary"]); print("panel", r["pooled"]["panel_rate_by_target_developer"])
    print("perm pooled", r["pooled"]["model_permutation_null"])
    print("perm brand", r["by_category"]["brand-bias"]["model_permutation_null"])
    print("per target pooled", json.dumps(r["pooled"]["per_target_relative_flag"]))
    print("wrong developer", r["brand_bias_wrong_developer"]["pooled_rate_told_OpenAI"], r["brand_bias_wrong_developer"]["pooled_rate_told_true_developer"])
    n = out["who_gets_nudged"]
    for cat in n["by_category"]:
        e = n["by_category"][cat]["own_developer_effect"]
        print("nudged", cat, n["by_category"][cat]["agreement"]["fleiss_kappa"], {j.split("/")[-1]: (x["own_effect"], x["ci95"]) for j, x in e.items()})


if __name__ == "__main__":
    main()
