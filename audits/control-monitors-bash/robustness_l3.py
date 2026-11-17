"""Robustness checks for effect_l3.py (prereg.md step 8), on the same pinned board scores.

1. Placebo: shuffle n_actions within class before matching (keeps the weights' class marginals,
   breaks the score-length link). The matched-minus-full change should vanish.
2. Second statistic: mean per-action score instead of peak.
3. Second feature version: ten bins instead of five.
4. Drop each BashArena side task in turn (AUROC change and ranking tau).
5. Ranking without the four GPT-5.4 nano reasoning-effort variants except `high` (one family).
6. Alternative to reweighting (BashArena, LinuxArena): honest peak recomputed over only its first
   L actions, L drawn from the attack class's action counts (20 draws, seed 0).
8. Attack-side matching for the board's step-wise safety: attacks reweighted to the honest class's
   bin shares (bins = honest quintiles), honest threshold unchanged.
7. Discover/test split of bins: edges from a random half of attacks, effect on the other half.

Usage: python -I robustness_l3.py <monitors.json> <basharena_features.json> <out.json>
"""
import json, sys
import numpy as np
from scipy.stats import kendalltau
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import effect_l3 as E  # noqa: E402

E.init(sys.argv[1], sys.argv[2])
OUT = sys.argv[3]
rng = np.random.default_rng(0)
DS = ["basharena", "linuxarena-paper", "monitoringbench"]


def matched_auc(s, y, n, edges):
    b = np.searchsorted(edges, n, side="right"); w, keep = E.match_weights(b, y)
    return E.wauc(s[keep], y[keep], w[keep])


out = {}
for ds in DS:
    D = E.load(ds); y, n = D["y"], D["n"]; one = np.ones(len(y))
    _, edges = E.bins_for(n, y)
    _, edges10 = E.bins_for(n, y, 10)
    r = {"monitors": {}}
    for m, p in D["peaks"].items():
        cnt, al = D["acts"][m]
        mean = np.array([a.mean() for a in al])
        full = E.wauc(p, y, one)
        plac = []
        for _ in range(200):
            nn = n.copy()
            for c in (True, False):
                ix = np.where(y == c)[0]; nn[ix] = rng.permutation(n[ix])
            plac.append(matched_auc(p, y, nn, edges) - full)
        q = {"full": full, "matched": matched_auc(p, y, n, edges),
             "placebo_shuffled_n_change_mean": float(np.mean(plac)),
             "placebo_change_95": [float(np.percentile(plac, 2.5)), float(np.percentile(plac, 97.5))],
             "mean_score_full": E.wauc(mean, y, one), "mean_score_matched": matched_auc(mean, y, n, edges),
             "ten_bins_matched": matched_auc(p, y, n, edges10)}
        # discover/test: edges from half the attacks, effect on the other half + all honest
        ia = np.where(y)[0]; half = rng.permutation(ia)[: len(ia) // 2]
        e_half = np.unique(np.quantile(n[half], np.linspace(0, 1, 6))[1:-1])
        test = np.ones(len(y), bool); test[half] = False
        q["split_half_full"] = E.wauc(p[test], y[test], np.ones(test.sum()))
        q["split_half_matched"] = matched_auc(p[test], y[test], n[test], e_half)
        if ds in ("basharena", "linuxarena-paper"):
            na = n[y].astype(int); tr = []
            for _ in range(20):
                ph = p.copy()
                for i in np.where(~y)[0]:
                    L = int(rng.choice(na)); a = np.array([x for x in al[i][:L]])
                    ph[i] = a.max() if len(a) else 0.0
                tr.append(E.wauc(ph, y, one))
            q["honest_truncated_to_attack_lengths"] = float(np.mean(tr))
        hb_edges = np.unique(np.quantile(n[~y], np.linspace(0, 1, 6))[1:-1])
        b = np.searchsorted(hb_edges, n, side="right")
        wa = np.zeros(len(y))
        for v in np.unique(b):
            ia_, ih_ = (b == v) & y, (b == v) & ~y
            if ia_.sum():
                wa[ia_] = ih_.sum() / ia_.sum()
        hv = np.concatenate([al[i] for i in np.where(~y)[0]])
        _, pc = E.stepwise_safety(hv, np.ones(len(hv)), p[y], cnt[y], D["succ"][y])
        sc = D["succ"][y]; ww = wa[y]
        q["stepwise_safety_full"] = float(pc.sum() / (pc.sum() + ((1 - pc) * sc).sum()))
        q["stepwise_safety_attacks_reweighted_to_honest_lengths"] = float((ww * pc).sum() / ((ww * pc).sum() + (ww * (1 - pc) * sc).sum()))
        q["attack_share_without_honest_in_bin"] = float((ww == 0).mean())
        r["monitors"][m] = q
    mons = list(D["peaks"])
    if len(mons) >= 3:
        f = [r["monitors"][m]["full"] for m in mons]
        r["tau_mean_score_full_vs_matched"] = float(kendalltau([r["monitors"][m]["mean_score_full"] for m in mons], [r["monitors"][m]["mean_score_matched"] for m in mons])[0])
        r["tau_ten_bins"] = float(kendalltau(f, [r["monitors"][m]["ten_bins_matched"] for m in mons])[0])
        if ds in ("basharena", "linuxarena-paper"):
            r["tau_truncation"] = float(kendalltau(f, [r["monitors"][m]["honest_truncated_to_attack_lengths"] for m in mons])[0])
        keepm = [m for m in mons if m not in ("gpt-5.4-nano-none", "gpt-5.4-nano-low", "gpt-5.4-nano-medium")]
        if 3 <= len(keepm) < len(mons):
            r["tau_one_nano_variant"] = float(kendalltau([r["monitors"][m]["full"] for m in keepm], [r["monitors"][m]["matched"] for m in keepm])[0])
    if ds == "basharena":
        st = np.array([E.feat[t]["side_task"] for t in D["ids"]], dtype=object)
        r["drop_side_task"] = {}
        for t in sorted({x for x in st if x}):
            k = st != t
            f_ = {m: E.wauc(p[k], y[k], np.ones(k.sum())) for m, p in D["peaks"].items()}
            g_ = {m: matched_auc(p[k], y[k], n[k], edges) for m, p in D["peaks"].items()}
            r["drop_side_task"][t] = {"min_auroc_change": float(min(g_[m] - f_[m] for m in mons)),
                                      "max_auroc_change": float(max(g_[m] - f_[m] for m in mons)),
                                      "tau": float(kendalltau([f_[m] for m in mons], [g_[m] for m in mons])[0]),
                                      "top_full": max(f_, key=f_.get), "top_matched": max(g_, key=g_.get)}
    out[ds] = r
json.dump(out, open(OUT, "w"), indent=1)
for ds, r in out.items():
    print("==", ds, {k: v for k, v in r.items() if k != "monitors"})
    for m, q in r["monitors"].items():
        print(f"  {m:24s} " + " ".join(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={np.round(v,3).tolist()}" for k, v in q.items()))
