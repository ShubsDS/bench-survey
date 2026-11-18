"""H3: validator's own null models (N0 no lean; N1t one lean per template), and a pair-level
dispersion test, from the released per-question counts. 10 simulated responses per question,
500 replicates, seed 7. The rule is v_core.flag (thresholds 0.5 / bias 0.05)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from scipy.stats import spearmanr
from v_core import *

R = 500
rng = np.random.default_rng(7)
df = load_main(); W = pairs_table(df)
res = {}
for m in MODELS:
    x = W[W.model_id == m].reset_index(drop=True)
    g = x.grp.to_numpy(); G = np.unique(g); gi = np.searchsorted(G, g)
    yY, nY, uY, tY = (x[c].to_numpy(float) for c in ["yes_count_Y", "no_count_Y", "unknown_count_Y", "total_count_Y"])
    yN, nN, uN, tN = (x[c].to_numpy(float) for c in ["yes_count_N", "no_count_N", "unknown_count_N", "total_count_N"])
    kY, kN = yY + nY, yN + nN
    wY = np.divide(nY, kY, out=np.zeros_like(kY), where=kY > 0)  # wrong rate among known, YES-keyed
    wN = np.divide(yN, kN, out=np.zeros_like(kN), where=kN > 0)
    ruY, ruN = uY / tY, uN / tN
    # N0: both questions wrong at the pooled pair rate
    e0 = np.divide(nY + yN, kY + kN, out=np.zeros_like(kY), where=(kY + kN) > 0)
    # N1t: 1-kappa = wY + wN; lean per template fitted to the observed template mean p_yes
    ik = np.clip(wY + wN, 0, 1)
    py_obs = np.concatenate([(yY + .5 * uY) / tY, (yN + .5 * uN) / tN])
    gg = np.concatenate([gi, gi])
    kfY, kfN = 1 - ruY, 1 - ruN  # known fraction
    A = np.concatenate([.5 * ruY + kfY * (1 - ik), .5 * ruN])
    B = np.concatenate([kfY * ik, kfN * ik])
    lean = np.zeros(len(G))
    for j in range(len(G)):
        s = gg == j
        lean[j] = np.clip((py_obs[s].mean() - A[s].mean()) / B[s].mean(), 0, 1) if B[s].mean() > 0 else .5
    l = lean[gi]
    pwY1, pwN1 = ik * (1 - l), ik * l  # wrong prob per known answer under N1t
    T = 10
    out = {}
    for name, (pwY, pwN) in {"N0": (e0, e0), "N1t": (pwY1, pwN1)}.items():
        cnt = []
        for r in range(R):
            UY = rng.binomial(T, ruY); UN = rng.binomial(T, ruN)
            WYs = rng.binomial(T - UY, pwY); WNs = rng.binomial(T - UN, pwN)
            pyY = ((T - UY - WYs) + .5 * UY) / T; pyN = (WNs + .5 * UN) / T
            gm = np.bincount(np.concatenate([gi, gi]), np.concatenate([pyY, pyN]), len(G)) / np.bincount(np.concatenate([gi, gi]), minlength=len(G))
            f = flag(x, pcY=pyY, pcN=1 - pyN, gbias=gm[gi], totY=np.full(len(x), T), totN=np.full(len(x), T))
            cnt.append(f.sum())
        cnt = np.array(cnt)
        out[name] = dict(mean=float(cnt.mean()), lo=float(np.percentile(cnt, 2.5)), hi=float(np.percentile(cnt, 97.5)))
    # dispersion: among pairs with >= 2 wrong known answers, split of wrong answers between questions
    Wt = nY + yN
    s = Wt >= 2
    p = np.divide(kY * pwY1, kY * pwY1 + kN * pwN1, out=np.full_like(kY, .5), where=(kY * pwY1 + kN * pwN1) > 0)
    def disp(wy, wt, pp):
        v = wt * pp * (1 - pp); ok = v > 0
        return float(np.mean((wy[ok] - wt[ok] * pp[ok]) ** 2 / v[ok]))
    obs = disp(nY[s], Wt[s], p[s])
    sims = [disp(rng.binomial(Wt[s].astype(int), p[s]).astype(float), Wt[s], p[s]) for _ in range(R)]
    pub = int(round(PUB[SHORT[m]] * 48.92))
    res[SHORT[m]] = dict(published=pub, **{k: v for k, v in out.items()}, dispersion_obs=obs,
                         dispersion_null_975=float(np.percentile(sims, 97.5)), n_pairs_disp=int(s.sum()))
    print(SHORT[m], pub, {k: (round(v["mean"], 1), v["lo"], v["hi"]) for k, v in out.items()},
          "disp", round(obs, 2), round(float(np.percentile(sims, 97.5)), 2))
pubs = [res[k]["published"] for k in res]; n1 = [res[k]["N1t"]["mean"] for k in res]
rho = spearmanr(pubs, n1).correlation
within = sum(abs(b / a - 1) <= .2 for a, b in zip(pubs, n1))
res["_summary"] = dict(spearman_pub_vs_N1t=float(rho), within_20pct=int(within),
                       N0_max=max(res[k]["N0"]["mean"] for k in res if k != "_summary"),
                       disp_rejects=sum(res[k]["dispersion_obs"] > res[k]["dispersion_null_975"] for k in res if k != "_summary"))
print(res["_summary"])
json.dump(res, open(os.path.join(os.path.dirname(__file__), "v_nulls.json"), "w"), indent=1)
