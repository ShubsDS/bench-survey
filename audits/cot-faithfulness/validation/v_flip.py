"""H2: flip-dominated split, threshold variation, placebos, template bootstrap of the comparisons,
and ranks. Released flag sets (100-response sets at 0.4 for oversampled pairs), as the authors'
pattern autorater covers only these. Rates are per 4,834 pairs. Seeds fixed."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from scipy.stats import spearmanr
from v_core import *

HERE = os.path.dirname(__file__)
ext = json.load(open(os.path.join(ROOT, "data/val_extract.json")))
df = load_main(); W = pairs_table(df)
G = np.array(sorted(W.grp.unique())); NG = len(G); NP = 4834
pairs_per_g = W[W.model_id == MODELS[0]].groupby("grp").size().reindex(G).to_numpy()
M = [SHORT[m] for m in MODELS]

# released flagged pairs per model: low-question qid -> template index, wrong-answer flip labels
rel = {}
for m in MODELS:
    x = W[W.model_id == m]; f = flag(x); x = x[f]
    low = np.where(x.p_correct_Y < x.p_correct_N, x.qid_Y, x.qid_N)
    e = ext[SHORT[m]]
    assert set(low) == set(e), (m, len(set(low) ^ set(e)))
    rel[SHORT[m]] = [(np.searchsorted(G, g), [r for r in e[q]["wrong"].values() if r.get("flip") in ("YES", "NO")])
                     for q, g in zip(low, x.grp)]

def counts_by_g(pairlist, keep):
    c = np.zeros(NG)
    for (g, _), k in zip(pairlist, keep):
        if k: c[g] += 1
    return c

def dominated(labels, field, val, t):
    """labels: list of response dicts; dominated if share(field==val) >= t (t=0 means any)."""
    if not labels: return False
    s = np.mean([(val in (r.get(field) or [])) if isinstance(r.get(field), list) else (r.get(field) == val) for r in labels])
    return s > 0 if t == 0 else s >= t

COMP = [("son37", "son35v2"), ("son37", "son37_1k"), ("son37_64k", "son37_1k"), ("llama31base", "llama33inst"),
        ("dsv3", "dsr1"), ("4omini", "4o")]
rng = np.random.default_rng(3)
BIDX = rng.integers(0, NG, size=(2000, NG))
def boot_diff(ca, cb):
    d = (ca - cb)[BIDX].sum(1) / pairs_per_g[BIDX].sum(1) * 100
    return [float((ca - cb).sum() / NP * 100), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]

out = {}
C_all = {m: counts_by_g(rel[m], [True] * len(rel[m])) for m in M}
out["released_counts"] = {m: int(C_all[m].sum()) for m in M}
out["comparisons_released"] = {f"{a}-{b}": boot_diff(C_all[a], C_all[b]) for a, b in COMP}
# threshold variation for "flip-dominated"
thr = {}
for t in [0, .25, .5, .75, 1.0]:
    keep = {m: [not dominated(l, "flip", "YES", t) for _, l in rel[m]] for m in M}
    C = {m: counts_by_g(rel[m], keep[m]) for m in M}
    thr[str(t)] = dict(kept={m: int(C[m].sum()) for m in M},
                       comps={f"{a}-{b}": boot_diff(C[a], C[b]) for a, b in COMP[:2]})
out["threshold_variation"] = thr
# main split at 0.5
keep05 = {m: [not dominated(l, "flip", "YES", .5) for _, l in rel[m]] for m in M}
C05 = {m: counts_by_g(rel[m], keep05[m]) for m in M}
obs = {k: v[0] for k, v in thr["0.5"]["comps"].items()}

# P-a: random removal of the same number of flagged pairs per model
pa = []
for _ in range(1000):
    C = {}
    for m in ["son37", "son35v2", "son37_1k"]:
        n_rm = len(rel[m]) - sum(keep05[m]); k = np.ones(len(rel[m]), bool)
        k[rng.choice(len(rel[m]), n_rm, replace=False)] = False
        C[m] = counts_by_g(rel[m], k)
    pa.append([(C["son37"] - C["son35v2"]).sum() / NP * 100, (C["son37"] - C["son37_1k"]).sum() / NP * 100])
pa = np.array(pa)
# P-b: shuffle flip labels among all labelled wrong answers within template, across the 16 models
pool = {}
for m in M:
    for i, (g, l) in enumerate(rel[m]):
        for j, r in enumerate(l): pool.setdefault(g, []).append((m, i, r["flip"]))
def perm_draw(within):
    lab = {m: [[None] * len(l) for _, l in rel[m]] for m in M}
    if within == "template":
        for g, lst in pool.items():
            v = np.array([x[2] for x in lst]); rng.shuffle(v)
            for (m, i, _), nv in zip(lst, v): lab[m][i][len([0 for z in lab[m][i] if z is not None])] = nv
    else:  # within model, across its pairs
        for m in M:
            v = np.array([r["flip"] for _, l in rel[m] for r in l]); rng.shuffle(v); k = 0
            for i, (_, l) in enumerate(rel[m]):
                for j in range(len(l)): lab[m][i][j] = v[k]; k += 1
    C = {}
    for m in ["son37", "son35v2", "son37_1k"]:
        kp = [not (len(L) and np.mean([z == "YES" for z in L]) >= .5) for L in lab[m]]
        C[m] = counts_by_g(rel[m], kp)
    return [(C["son37"] - C["son35v2"]).sum() / NP * 100, (C["son37"] - C["son37_1k"]).sum() / NP * 100]
pb = np.array([perm_draw("template") for _ in range(1000)])
pd_ = np.array([perm_draw("model") for _ in range(1000)])
def where(o, dist): return dict(obs=o, p05=float(np.percentile(dist, 2.5)), p50=float(np.median(dist)),
                               p95=float(np.percentile(dist, 97.5)), share_le_obs=float(np.mean(dist <= o + 1e-12)))
out["placebo_random_removal"] = {"son37-son35v2": where(obs["son37-son35v2"], pa[:, 0]), "son37-son37_1k": where(obs["son37-son37_1k"], pa[:, 1])}
out["placebo_shuffle_within_template"] = {"son37-son35v2": where(obs["son37-son35v2"], pb[:, 0]), "son37-son37_1k": where(obs["son37-son37_1k"], pb[:, 1])}
out["placebo_shuffle_within_model"] = {"son37-son35v2": where(obs["son37-son35v2"], pd_[:, 0]), "son37-son37_1k": where(obs["son37-son37_1k"], pd_[:, 1])}
# P-c: matched placebo categories from the same autorater (argument-switching evidence, 32% of answers;
# lack_of_information, 10%)
for nm, field, val in [("argument_switching", "ev", "argument-switching"), ("lack_of_information", "lack", "YES"),
                       ("fact_manipulation", "ev", "fact-manipulation")]:
    kp = {m: [not dominated(l, field, val, .5) for _, l in rel[m]] for m in M}
    C = {m: counts_by_g(rel[m], kp[m]) for m in M}
    out[f"placebo_category_{nm}"] = dict(kept={m: int(C[m].sum()) for m in ["son37", "son35v2", "son37_1k"]},
                                         comps={f"{a}-{b}": boot_diff(C[a], C[b]) for a, b in COMP[:2]})
# ranks
pub = {SHORT[m]: PUB[SHORT[m]] for m in MODELS}
def ranks(d):
    o = sorted(d, key=lambda k: -d[k]); return {k: o.index(k) + 1 for k in d}
r_pub = ranks(pub); r_rel = ranks({m: C_all[m].sum() for m in M}); r_nf = ranks({m: C05[m].sum() + 1e-6 * pub[m] for m in M})
out["ranks"] = dict(published=r_pub, released=r_rel, no_flip_dominated=r_nf,
                    spearman_pub_vs_noflip=float(spearmanr([pub[m] for m in M], [C05[m].sum() for m in M]).correlation),
                    spearman_rel_vs_noflip=float(spearmanr([C_all[m].sum() for m in M], [C05[m].sum() for m in M]).correlation),
                    moves_gt2_pub=[(m, r_pub[m], r_nf[m]) for m in M if abs(r_pub[m] - r_nf[m]) > 2],
                    moves_gt2_rel=[(m, r_rel[m], r_nf[m]) for m in M if abs(r_rel[m] - r_nf[m]) > 2])
json.dump(out, open(os.path.join(HERE, "v_flip.json"), "w"), indent=1, default=float)
for k, v in out.items(): print(k, v, "\n")
