"""Validator v3: headline numbers and attacks, from v2_items.csv (own re-scoring of the cache).

Seed 0, 2,000 protocol-cluster bootstrap draws, 1,000 placebo draws. No model calls.
Writes validation/v3_analysis.json. Run with python3 -I from the repo root.
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AUD = HERE.parent
sys.path.insert(0, str(AUD.parent / "lab-bench" / "scripts"))
from common import load_items, clusters  # noqa: E402

B = 2000
rng = np.random.default_rng(0)
out = {}

items_df = load_items()
items_df["cluster"] = clusters(items_df)
pq = items_df[(items_df.subset == "ProtocolQA") & (~items_df.id.str.startswith("bee8b322"))].reset_index(drop=True)
IDS = list(pq.id)
pos = {i: k for k, i in enumerate(IDS)}  # dataset (file) order
CL = dict(zip(pq.id, pq.cluster))
NOPT = dict(zip(pq.id, pq.n_options))
PLEN = dict(zip(pq.id, pq.protocol.map(len)))

cells = defaultdict(dict)  # (model, style, arm) -> id -> correct
pick = defaultdict(dict)
for r in csv.DictReader(open(HERE / "v2_items.csv")):
    if r["subset"] != "ProtocolQA":
        continue
    cells[(r["model"], r["style"], r["arm"])][r["id"]] = int(r["correct"])
    pick[(r["model"], r["style"], r["arm"])][r["id"]] = r["picked"]
ARMS = {
    "haiku_full": ("haiku", "cot", "full"), "haiku_qo": ("haiku", "cot", "qo"),
    "haiku_opts": ("haiku", "cot", "opts"), "haiku_qo_ro": ("haiku", "cot", "qo_ro"),
    "haiku_qo_pa": ("haiku", "cot", "qo_pa"), "haiku_opts_ro": ("haiku", "cot", "opts_ro"),
    "haiku_opts_pa": ("haiku", "cot", "opts_pa"), "sonnet_full": ("sonnet", "direct", "full"),
    "sonnet_qo": ("sonnet", "direct", "qo"), "sonnet_qo_pa": ("sonnet", "direct", "qo_pa"),
}
A = {k: cells[v] for k, v in ARMS.items()}

clist = sorted(set(CL.values()))
cid = {c: i for i, c in enumerate(clist)}
draws = [rng.integers(0, len(clist), len(clist)) for _ in range(B)]


def chance(ids):
    return float(np.mean([1 / NOPT[i] for i in ids]))


def boot(stat, ids):
    """stat(list_of_ids) -> float; joint cluster bootstrap over the given ids."""
    by = defaultdict(list)
    for i in ids:
        by[CL[i]].append(i)
    cs = sorted(by)
    vals = []
    for _ in range(B):
        pickc = rng.integers(0, len(cs), len(cs))
        sample = [i for j in pickc for i in by[cs[j]]]
        try:
            v = stat(sample)
        except ZeroDivisionError:
            continue
        if v is not None and np.isfinite(v):
            vals.append(v)
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def acc(arm, ids):
    return float(np.mean([A[arm][i] for i in ids]))


def rate(arm, ids=None):
    ids = [i for i in (ids or IDS) if i in A[arm]]
    return {"n": len(ids), "acc": round(acc(arm, ids), 4), "ci": [round(x, 3) for x in boot(lambda s: acc(arm, s), ids)],
            "chance": round(chance(ids), 4), "clusters": len({CL[i] for i in ids})}


# ---------------------------------------------------------------- A0 reproduction
out["A0"] = {k: rate(k) for k in A}
S62 = sorted(A["sonnet_full"], key=pos.get)
R45 = [i for i in IDS if i not in A["sonnet_full"]]

# ---------------------------------------------------------------- Attack 1: which 62?
p62 = sorted(pos[i] for i in S62)
c62, c45 = {CL[i] for i in S62}, {CL[i] for i in R45}
out["sonnet_62"] = {
    "positions_in_file_order": [p62[0], p62[-1]], "is_first_62_in_file_order": p62 == list(range(62)),
    "clusters_in_62": len(c62), "clusters_in_45": len(c45), "clusters_in_both": len(c62 & c45),
    "clusters_only_in_45": len(c45 - c62),
    "protocol_len_median_62": float(np.median([PLEN[i] for i in S62])),
    "protocol_len_median_45": float(np.median([PLEN[i] for i in R45])),
    "n_options_mean_62": float(np.mean([NOPT[i] for i in S62])), "n_options_mean_45": float(np.mean([NOPT[i] for i in R45])),
    "chance_62": chance(S62), "chance_45": chance(R45),
}
for arm in ["haiku_full", "haiku_qo", "haiku_opts", "sonnet_qo"]:
    out["sonnet_62"][arm + "_on_62"] = rate(arm, S62)
    out["sonnet_62"][arm + "_on_45"] = rate(arm, R45)
    out["sonnet_62"][arm + "_45_minus_62"] = round(acc(arm, R45) - acc(arm, S62), 4)
# ledger: were full calls stopped by order? first-call time of each Sonnet full item
# (the 62 are a prefix of file order iff the runner went in file order)


# ---------------------------------------------------------------- Attack 2: share, baselines, joint resampling
def share(num_arm, den_arm, base, ids):
    def f(s):
        b = chance(s) if base == "chance" else acc(base, s)
        d = acc(den_arm, s) - b
        return (acc(num_arm, s) - b) / d if abs(d) > 1e-9 else None
    return {"n": len(ids), "share": round(f(ids), 4), "ci_joint_cluster": [round(x, 3) for x in boot(f, ids)]}


def letter_prior_chance(arm, ids):
    """Expected accuracy of a guesser with this arm's letter distribution (position bias)."""
    m, st, a = ARMS[arm]
    rows = {}
    for r in csv.DictReader(open(HERE / "v2_items.csv")):
        if r["subset"] == "ProtocolQA" and (r["model"], r["style"], r["arm"]) == (m, st, a):
            rows[r["id"]] = r
    letters = Counter(rows[i]["letter"] for i in ids if i in rows)
    tot = sum(letters.values())
    e = []
    for i in ids:
        if i not in rows:
            continue
        order = rows[i]["order"].split("|")
        kl = chr(65 + order.index("key"))
        # renormalise letter prior over the letters this item offers
        offered = [chr(65 + k) for k in range(len(order))]
        z = sum(letters[L] for L in offered) or 1
        e.append(letters[kl] / z)
    return round(float(np.mean(e)), 4), dict(letters)


out["share"] = {
    "haiku_qo_over_full_chance_base": share("haiku_qo", "haiku_full", "chance", IDS),
    "haiku_opts_over_full_chance_base": share("haiku_opts", "haiku_full", "chance", IDS),
    "haiku_qo_over_full_opts_base": share("haiku_qo", "haiku_full", "haiku_opts", IDS),
    "sonnet_qo_over_full_chance_base_62": share("sonnet_qo", "sonnet_full", "chance", S62),
    "sonnet_qo_over_full_haikuopts_base_62": share("sonnet_qo", "sonnet_full", "haiku_opts", S62),
    "haiku_qo_over_full_chance_base_62": share("haiku_qo", "haiku_full", "chance", S62),
    "haiku_qo_over_full_chance_base_45": share("haiku_qo", "haiku_full", "chance", R45),
    "letter_prior_chance": {a: letter_prior_chance(a, IDS if a != "sonnet_full" else S62)
                            for a in ["haiku_full", "haiku_qo", "haiku_opts", "sonnet_full", "sonnet_qo"]},
}
for a, b, ids in [("haiku_full", "haiku_qo", IDS), ("sonnet_full", "sonnet_qo", S62), ("haiku_full", "haiku_qo", S62)]:
    out["share"][f"diff_{a}_minus_{b}_n{len(ids)}"] = {
        "diff": round(acc(a, ids) - acc(b, ids), 4),
        "ci": [round(x, 3) for x in boot(lambda s: acc(a, s) - acc(b, s), ids)],
        "both": sum(A[a][i] and A[b][i] for i in ids), "only_full": sum(A[a][i] and not A[b][i] for i in ids),
        "only_blind": sum(A[b][i] and not A[a][i] for i in ids), "neither": sum(not A[a][i] and not A[b][i] for i in ids)}

# ---------------------------------------------------------------- Attack 3: labels
mine = {r["id8"]: r for r in csv.DictReader(open(HERE / "v1_labels.csv"))}
aud = {r["id8"]: r for r in csv.DictReader(open(AUD / "labels" / "labels.csv"))}
id8 = {i[:8]: i for i in IDS}
assert set(mine) == set(id8) == set(aud)
K = {id8[k] for k, r in mine.items() if r["U"] == "1" and r["S"] == "1" and r["T"] != "NUM"}
K2 = {id8[k] for k, r in mine.items() if r["U"] == "1" and r["T"] == "PROC"}
U1 = {id8[k] for k, r in mine.items() if r["U"] == "1"}
G = {id8[k] for k, r in aud.items() if r["class"] == "G"}
SK = {id8[k] for k, r in aud.items() if r["standard_key"] == "True"}
PIK = {id8[k] for k, r in aud.items() if r["pick_is_key"] == "True"}


def kappa(a, b):
    x = np.array([i in a for i in IDS]); y = np.array([i in b for i in IDS])
    po = np.mean(x == y); pe = x.mean() * y.mean() + (1 - x.mean()) * (1 - y.mean())
    return {"agree": round(float(po), 3), "kappa": round(float((po - pe) / (1 - pe)), 3),
            "both": int((x & y).sum()), "only_first": int((x & ~y).sum()), "only_second": int((~x & y).sum())}


def gap(arm, S, ids=None):
    ids = [i for i in (ids or IDS) if i in A[arm]]
    inS = [i for i in ids if i in S]; outS = [i for i in ids if i not in S]

    def f(s):
        a = [A[arm][i] for i in s if i in S]; b = [A[arm][i] for i in s if i not in S]
        return np.mean(a) - np.mean(b) if a and b else None
    # placebo: random sets of the same size, stratified by number of options, key-blind
    strata = defaultdict(list)
    for i in ids:
        strata[NOPT[i]].append(i)
    need = Counter(NOPT[i] for i in inS)
    obs = f(ids)
    pl = []
    for _ in range(1000):
        P = set()
        for k, n in need.items():
            P |= set(rng.choice(strata[k], n, replace=False))
        a = [A[arm][i] for i in ids if i in P]; b = [A[arm][i] for i in ids if i not in P]
        pl.append(np.mean(a) - np.mean(b))
    return {"n_in": len(inS), "n_out": len(outS), "acc_in": round(float(np.mean([A[arm][i] for i in inS])), 3),
            "acc_out": round(float(np.mean([A[arm][i] for i in outS])), 3), "gap": round(float(obs), 3),
            "ci": [round(x, 3) for x in boot(f, ids)], "placebo_pct": round(float(np.mean(np.array(pl) < obs) * 100), 1),
            "chance_out": round(chance(outS), 3)}


out["labels"] = {
    "sizes": {"validator_K": len(K), "validator_K2_strict": len(K2), "validator_U1": len(U1),
              "auditor_G": len(G), "auditor_standard_key": len(SK), "auditor_pick_is_key": len(PIK)},
    "agreement": {"K_vs_auditor_G": kappa(K, G), "K_vs_auditor_standard_key": kappa(K, SK),
                  "U1_vs_auditor_G": kappa(U1, G), "K2_vs_auditor_G": kappa(K2, G)},
    "auditor_pick_accuracy_by_class": {
        "G": round(len(G & PIK) / len(G), 3), "not_G": round(len(PIK - G) / (len(IDS) - len(G)), 3),
        "validator_K": round(len(K & PIK) / len(K), 3), "validator_not_K": round(len(PIK - K) / (len(IDS) - len(K)), 3)},
    "gaps": {},
}
for arm in ["haiku_qo", "haiku_opts", "sonnet_qo", "haiku_full", "sonnet_full"]:
    g = out["labels"]["gaps"]
    g[f"{arm}|auditor_standard_key"] = gap(arm, SK)
    g[f"{arm}|auditor_G_keyblind"] = gap(arm, G)
    g[f"{arm}|auditor_pick_is_key"] = gap(arm, PIK)
    g[f"{arm}|validator_K"] = gap(arm, K)
    g[f"{arm}|validator_K2"] = gap(arm, K2)
    # within the items the labeller answered correctly: does class G still matter?
    g[f"{arm}|auditor_G_within_pick_is_key"] = gap(arm, G, [i for i in IDS if i in PIK])
    g[f"{arm}|validator_K_within_pick_is_key"] = gap(arm, K, [i for i in IDS if i in PIK])
    g[f"{arm}|validator_K_within_pick_not_key"] = gap(arm, K, [i for i in IDS if i not in PIK])

# ---------------------------------------------------------------- Attack 6: more content-blind rules
WORD = re.compile(r"[a-z]+")
NUMR = re.compile(r"\d+(?:\.\d+)?")


def opts_of(i):
    r = pq[pq.id == i].iloc[0]
    return [("key", r.ideal)] + [(f"d{k}", d) for k, d in enumerate(r.distractors)], r.question


def jac(a, b):
    a, b = set(WORD.findall(a.lower())), set(WORD.findall(b.lower()))
    return len(a & b) / max(1, len(a | b))


def rule_scores(i):
    """Credit for the key (index 0) under each rule, ties split."""
    ops, q = opts_of(i)
    return _scores_from_texts([t for _, t in ops], q)


def option_credits(i):
    ops, q = opts_of(i)
    texts = [t for _, t in ops]
    n = len(texts)
    credits = {}
    # recompute for each index by rotating the list so that index j is first
    for j in range(n):
        rot = [texts[j]] + [t for k, t in enumerate(texts) if k != j]
        credits[j] = _scores_from_texts(rot, q)
    return credits


def _scores_from_texts(texts, q):
    n = len(texts)
    feats = {
        "max_q_overlap": [jac(t, q) for t in texts],
        "max_mean_overlap": [np.mean([jac(t, u) for k2, u in enumerate(texts) if k2 != k]) for k, t in enumerate(texts)],
        "min_numerals": [-len(NUMR.findall(t)) for t in texts],
    }
    sims = [(jac(texts[a], texts[b]), a, b) for a in range(n) for b in range(a + 1, n)]
    best = max(sims)[0]
    pair = {x for s, a, b in sims if s == best for x in (a, b)}
    feats["closest_pair"] = [1.0 if k in pair else 0.0 for k in range(n)]
    steps = [set(re.findall(r"[Ss]teps? ?(\d+)", t)) for t in texts]
    cnt = Counter(s for ss in steps for s in ss)
    feats["majority_step"] = [max([cnt[s] for s in ss], default=0) for ss in steps]
    nums = [[float(x) for x in NUMR.findall(t)] for t in texts]
    firsts = [max(v) if v else None for v in nums]
    vals = sorted(v for v in firsts if v is not None)
    if len(vals) >= 3:
        med = vals[len(vals) // 2]
        feats["median_number"] = [0 if v is None else -abs(np.log1p(v) - np.log1p(med)) for v in firsts]
    else:
        feats["median_number"] = [0] * n
    res = {}
    for name, f in feats.items():
        for sign, tag in [(1, "max"), (-1, "min")]:
            v = np.array(f, dtype=float) * sign
            top = np.flatnonzero(v == v.max())
            res[f"{tag}:{name}"] = (1.0 / len(top)) if 0 in top else 0.0
    return res


RS = {i: rule_scores(i) for i in IDS}
rules = sorted(next(iter(RS.values())))


def heldout(RSx, n_iter=1000, seed=1):
    """Pick the best rule on a random half of the protocols, score it on the other half."""
    g = np.random.default_rng(seed)
    hs, chosen = [], Counter()
    for _ in range(n_iter):
        half = set(g.choice(clist, len(clist) // 2, replace=False))
        tr = [i for i in IDS if CL[i] in half]; te = [i for i in IDS if CL[i] not in half]
        best = max(rules, key=lambda r: np.mean([RSx[i][r] for i in tr]))
        chosen[best] += 1
        hs.append(np.mean([RSx[i][best] for i in te]))
    return float(np.mean(hs)), [float(np.percentile(hs, 2.5)), float(np.percentile(hs, 97.5))], chosen


CRED = {i: option_credits(i) for i in IDS}
assert all(CRED[i][0] == RS[i] for i in IDS)
obs_h, obs_ci, chosen = heldout(RS)
null_h = []
for s in range(300):
    g = np.random.default_rng(1000 + s)
    RSn = {i: CRED[i][int(g.integers(0, len(CRED[i])))] for i in IDS}
    null_h.append(heldout(RSn, n_iter=100, seed=s)[0])
in_sample = {r: round(float(np.mean([RS[i][r] for i in IDS])), 4) for r in rules}
out["new_rules"] = {
    "rules": rules, "in_sample_acc": in_sample, "chance": round(chance(IDS), 4),
    "heldout_mean": round(obs_h, 4), "heldout_p2.5_97.5": [round(x, 3) for x in obs_ci],
    "chosen": dict(chosen), "null_heldout_mean": round(float(np.mean(null_h)), 4),
    "p": round(float((1 + sum(x >= obs_h for x in null_h)) / (1 + len(null_h))), 3),
}

# ---------------------------------------------------------------- Attack 5: paraphrase drops
for a, b in [("haiku_qo_ro", "haiku_qo_pa"), ("haiku_opts_ro", "haiku_opts_pa"), ("sonnet_qo", "sonnet_qo_pa"), ("haiku_qo", "haiku_qo_pa")]:
    ids = [i for i in IDS if i in A[b]]
    out.setdefault("paraphrase", {})[f"{a}->{b}"] = {
        "n": len(ids), "drop": round(acc(a, ids) - acc(b, ids), 4),
        "ci": [round(x, 3) for x in boot(lambda s: acc(a, s) - acc(b, s), ids)],
        "lost": sum(A[a][i] and not A[b][i] for i in ids), "gained": sum(A[b][i] and not A[a][i] for i in ids)}
for a, b in [("haiku_qo", "haiku_qo_ro"), ("haiku_opts", "haiku_opts_ro")]:
    out["paraphrase"][f"reorder {a}->{b}"] = {"diff": round(acc(b, IDS) - acc(a, IDS), 4),
                                              "ci": [round(x, 3) for x in boot(lambda s: acc(b, s) - acc(a, s), IDS)]}

json.dump(out, open(HERE / "v3_analysis.json", "w"), indent=1)
print(json.dumps(out, indent=1))
