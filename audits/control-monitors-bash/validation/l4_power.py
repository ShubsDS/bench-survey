"""Validator: how large an effect could the L4 Haiku intervention detect?

Uses the auditor's stored Haiku scores (data/l4_run.json, data/l4_retest.json; no new inference).
Noise between two independent draws of the *same* prompt is estimated three ways:
  1. attack items under R vs S (byte-identical prompts, drawn independently; 109 pairs);
  2. R vs R2 (trailing newline; 55 pairs), full AUROC change;
  3. R vs R2 with only the honest scores redrawn (attack held at R) - the noise relevant to the
     S edit, which changes honest items only.
Minimum detectable effect (two-sided 5%, 80% power) = 2.8 x the noise SD of an AUROC difference.

Usage: python -I l4_power.py <l4_run.json> <l4_retest.json> <out.json>
"""
import json, sys
import numpy as np

run, ret, OUT = sys.argv[1:4]
rng = np.random.default_rng(20261117)


def auc(a, h):
    return float(((a[:, None] > h[None, :]).sum() + 0.5 * (a[:, None] == h[None, :]).sum()) / (len(a) * len(h)))


def pairs(path, conds):
    d = json.load(open(path)); P = {}
    for r in d["items"]:
        P.setdefault(r["pair"], {})[r["cls"]] = r
    P = [p for p in P.values() if all(p[c].get(f"score_{k}") is not None for c in ("attack", "honest") for k in conds)]
    g = lambda c, k: np.array([p[c][f"score_{k}"] for p in P], float)
    return {(c, k): g(c, k) for c in ("attack", "honest") for k in conds}, len(P)


X, n1 = pairs(run, ["R", "S", "L"])
Y, n2 = pairs(ret, ["R", "R2"])
out = {"n_pairs_main": n1, "n_pairs_retest": n2}
# 1. attack redraw (identical prompts)
d1 = auc(X["attack", "S"], X["honest", "R"]) - auc(X["attack", "R"], X["honest", "R"])
# 2. full redraw
d2 = auc(Y["attack", "R2"], Y["honest", "R2"]) - auc(Y["attack", "R"], Y["honest", "R"])
# 3. honest-only redraw
d3 = auc(Y["attack", "R"], Y["honest", "R2"]) - auc(Y["attack", "R"], Y["honest", "R"])
out["auroc_change_attack_redraw_identical_prompt_n109"] = d1
out["auroc_change_full_redraw_trailing_newline_n55"] = d2
out["auroc_change_honest_only_redraw_n55"] = d3
# Simulated noise SD: resample, for each item, which of its two draws is used (draw-swap
# permutation), on the n=55 retest pairs; scale to n=109 by sqrt(55/109).
def swap_sd(attack_too):
    v = []
    for _ in range(2000):
        sa = rng.random(n2) < 0.5 if attack_too else np.zeros(n2, bool)
        sh = rng.random(n2) < 0.5
        a1 = np.where(sa, Y["attack", "R2"], Y["attack", "R"]); a2 = np.where(sa, Y["attack", "R"], Y["attack", "R2"])
        h1 = np.where(sh, Y["honest", "R2"], Y["honest", "R"]); h2 = np.where(sh, Y["honest", "R"], Y["honest", "R2"])
        if not attack_too:
            a1 = a2 = Y["attack", "R"]
        v.append(auc(a1, h1) - auc(a2, h2))
    return float(np.std(v))
sd_full55, sd_h55 = swap_sd(True), swap_sd(False)
k = np.sqrt(55 / 109)
out["noise_sd_full_redraw_n55"] = sd_full55
out["noise_sd_honest_redraw_n55"] = sd_h55
out["mde_L_condition_n109"] = 2.8 * sd_full55 * k  # L redraws both classes
out["mde_S_condition_honest_edit_n109"] = 2.8 * sd_h55 * k
json.dump(out, open(OUT, "w"), indent=1)
print(json.dumps(out, indent=1))
