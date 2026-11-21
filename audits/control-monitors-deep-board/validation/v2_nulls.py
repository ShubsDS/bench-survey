"""Independent null constructions and bin sensitivity.

(a) Truncation null (action rows): each honest run is cut to a length drawn from the attack
    length distribution (prefix of its own actions; runs shorter than the draw are kept whole);
    AUROC of truncated maxima vs full honest maxima. Averaged over 200 draws.
(b) Extension null for datasets where attacks are longer: the run is extended to the drawn
    length by resampling its own actions with replacement (approximate, i.i.d. within run).
(c) Rank correlation of honest run score with honest length (Spearman), per row.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from vlib import arrays, load, wauc  # noqa: E402


def spearman(x, y):
    def rk(v):
        o = np.argsort(v, kind="mergesort")
        r = np.empty(len(v))
        sv = v[o]
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and sv[j + 1] == sv[i]:
                j += 1
            r[o[i:j + 1]] = (i + j) / 2
            i = j + 1
        return r
    a, b = rk(np.asarray(x, float)), rk(np.asarray(y, float))
    return float(np.corrcoef(a, b)[0, 1])


def spearman_ci(x, y, B=1000, seed=0):
    rng = np.random.default_rng(seed)
    x, y = np.asarray(x), np.asarray(y)
    v = []
    for _ in range(B):
        i = rng.integers(0, len(x), len(x))
        v.append(spearman(x[i], y[i]))
    v = np.array(v)
    v = v[~np.isnan(v)]
    if len(v) == 0:
        return [float("nan"), float("nan")]
    return [float(np.quantile(v, .025)), float(np.quantile(v, .975))]


d = load()
rng = np.random.default_rng(7)
out = []
for i, r in enumerate(d["rows"]):
    A = arrays(r)
    sa, la, katt = A["attack"]
    sh, lh, khon = A["honest"]
    if len(sa) < 10:
        continue
    rec = dict(i=i, dataset=r["dataset"], kind=r["kind"] if "kind" in r else r["monitor_kind"],
               variant=r["monitor_variant"])
    rec["spearman_honest_score_len"] = spearman(sh, lh)
    rec["spearman_ci"] = spearman_ci(sh, lh, seed=i)
    rec["spearman_attack_score_len"] = spearman(sa, la)
    if r["monitor_kind"] == "action":
        pooled = np.array([a for s in khon for a in s["actions"] if a is not None])

        def adjusted(s, Ld):
            """Run cut to its first Ld actions, or extended to Ld with pooled honest per-step draws."""
            n = len(s["actions"])
            own = [a for a in s["actions"][:max(Ld, 1)] if a is not None]
            m = max(own) if own else -1.0
            if Ld > n:
                m = max(m, float(rng.choice(pooled, Ld - n).max()))
            return m

        def cut_only(s, Ld):
            own = [a for a in s["actions"][:max(Ld, 1)] if a is not None]
            return max(own) if own else -1.0

        sym, asym = [], []
        for _ in range(200):
            La = rng.choice(la, len(khon)).astype(int)
            Lh = rng.choice(lh, len(khon)).astype(int)
            xa = np.array([adjusted(s, L) for s, L in zip(khon, La)])
            xh = np.array([adjusted(s, L) for s, L in zip(khon, Lh)])
            sym.append(wauc(xa, xh))
            asym.append(wauc(np.array([cut_only(s, L) for s, L in zip(khon, La)]),
                             np.array([cut_only(s, L) for s, L in zip(khon, Lh)])))
        rec["resize_null"] = float(np.mean(sym))
        rec["resize_null_sd"] = float(np.std(sym))
        rec["cut_only_null"] = float(np.mean(asym))
    out.append(rec)
    print(i, r["dataset"], r["monitor_kind"], r["monitor_variant"],
          "rho_h %.3f" % rec["spearman_honest_score_len"],
          "resize %.3f cut %.3f" % (rec.get("resize_null", np.nan), rec.get("cut_only_null", np.nan)),
          flush=True)
Path(__file__).with_name("v2_nulls.json").write_text(json.dumps(out))
