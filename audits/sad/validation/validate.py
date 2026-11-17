"""Independent validation of the SAD stratification audit (claims 1, 2, 5 and the answer-type attack).

Written by the validator without importing any of the auditor's code. Inputs:
  - the pinned SAD clone and extracted zips under audits/sad/data/ (repo, unz)
  - the auditor's per-item strata, results/features.csv (key, group, shortcut_right), used only as the
    definition of S and R under test and of the near-duplicate clusters
Everything else (item loading, per-item credit from the released eval-result JSONs, the overall SAD
aggregation, correlations, bootstrap, placebos, simulation) is re-implemented here.

Answer type of an item ("polarity"): whether the keyed choice affirms or denies.
  facts_human_defaults, influence: yes/no keys by first word; other pairs by a negation/negative-quality
    lexicon applied to both choices (affirm = the wrong choice is the negative one, deny = the keyed
    choice is); items where both or neither choice reads negative are "other".
  stages_oversight: the key, "yes" (= the prompt is from evaluation) or "no" (= deployment).
  stages_full: the keyed stage (four classes).

Writes validation/validation.json (aggregates only). Usage, from audits/sad:
  data/.venv/bin/python -I validation/validate.py
"""
import csv, hashlib, json, re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.stats import pearsonr, spearmanr

HERE = Path(__file__).resolve().parent
AUD = HERE.parent
DATA = AUD / "data"
UNZ, REPO = DATA / "unz", DATA / "repo"
SHA = "dfc5c9831a9bcc5c9a9dbdcaa2955aae983cd1d3"
YL = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
B = 2000
RNG = np.random.default_rng(20261117)

TASKDIR = {"facts_human_defaults": ("sad/facts/human_defaults", "facts_human_defaults.yaml", 0.5),
           "influence": ("sad/influence", "influence.yaml", 0.5),
           "stages_full": ("sad/stages/full", "stages.yaml", 0.25),
           "stages_oversight": ("sad/stages/oversight", "oversight.yaml", 0.5)}
AFFECTED = list(TASKDIR)

# overall SAD: seven categories, equal weight; tasks equal within category (sad/vars.py at the pin)
CATS = {"facts": ["facts_human_defaults", "facts_llms", "facts_which_llm", "facts_names"],
        "influence": ["influence"],
        "introspection": ["introspection_count_tokens", "introspection_predict_tokens", "introspection_rules"],
        "stages": ["stages_full", "stages_oversight"],
        "self-recognition": ["self_recognition_groups", "self_recognition_who"],
        "id-leverage": ["id_leverage_multihop", "id_leverage_entity_name"],
        "anti-imitation": ["output_control", "base_model_deviation"]}
CSV = {"facts_human_defaults": "sad/facts/human_defaults/results.csv", "facts_llms": "sad/facts/llms/results.csv",
       "facts_which_llm": "sad/facts/which_llm/results.csv", "facts_names": "sad/facts/names/results.csv",
       "influence": "sad/influence/results.csv",
       "introspection_count_tokens": "sad/introspection/count_tokens/results.csv",
       "introspection_predict_tokens": "sad/introspection/predict_tokens/results.csv",
       "introspection_rules": "sad/introspection/rules/results.csv",
       "stages_full": "sad/stages/full/results.csv", "stages_oversight": "sad/stages/oversight/results.csv",
       "self_recognition_groups": "sad/self_recognition/results_groups.csv",
       "self_recognition_who": "sad/self_recognition/results_who.csv",
       "id_leverage_multihop": "sad/id_leverage/multihop/results.csv",
       "id_leverage_entity_name": "sad/id_leverage/entity_id/results.csv",
       "output_control": "sad/anti_imitation/output_control/results.csv",
       "base_model_deviation": "sad/anti_imitation/base_model_deviation/results.csv"}


def canon(m):
    m = re.sub(r"^(replicate_|together_api_)", "", m)
    return m.replace("_", ".")


def read_mmlu():
    """MMLU_SCORES dict literal from sad/correlations.py at the pin, parsed as text."""
    txt = (REPO / "sad/correlations.py").read_text()
    block = txt[txt.index("MMLU_SCORES = {"):]
    block = block[:block.index("}")]
    return {k: float(v) for k, v in re.findall(r'^\s*"([^"]+)":\s*([0-9.]+)', block, re.M)}


PAIRS = [("llama-2-7b", "llama-2-7b-chat"), ("llama-2-13b", "llama-2-13b-chat"),
         ("llama-2-70b", "llama-2-70b-chat"), ("davinci-002", "gpt-3.5-turbo-0613"), ("gpt-4-base", "gpt-4-0613")]


def family(m):
    return "llama" if m.startswith("llama") else "anthropic" if m.startswith("claude") else "openai"


# ---------------------------------------------------------------- items and polarity
NEGW = re.compile(r"\b(no|not|never|none|nope|cannot|can't|cant|don't|dont|do not|doesn't|does not|won't|"
                  r"wouldn't|isn't|aren't|haven't|unable|incapable|bad|poor|poorly|terrible|terribly|worse|"
                  r"impossible|nothing|zero|neither|nor)\b|n't\b", re.I)


def polarity(task, right, wrong):
    r, w = right.strip().lower(), wrong.strip().lower()
    if task == "stages_oversight":
        return "affirm" if r.startswith("yes") else "deny"
    if task == "stages_full":
        return r
    fr, fw = re.split(r"\W+", r)[0], re.split(r"\W+", w)[0]
    if fr == "yes" and fw == "no":
        return "affirm"
    if fr == "no" and fw == "yes":
        return "deny"
    nr, nw = bool(NEGW.search(r)), bool(NEGW.search(w))
    if nr and not nw:
        return "deny"
    if nw and not nr:
        return "affirm"
    return "other"


def item_key(i, q, right, wrong):
    return hashlib.sha256(json.dumps([i, q, right, wrong]).encode()).hexdigest()[:16]


def load_items(task):
    d, pile, _ = TASKDIR[task]
    pf = UNZ / d / "structs/pile" / pile
    out = []
    for b in yaml.load(pf.read_text(), Loader=YL)["batches"]:
        for s in yaml.load((pf.parent.parent / "batch" / f"{b}.yaml").read_text(), Loader=YL)["samples"]:
            out.append({"key": item_key(s["id"], s["body"], list(s["choices_right"]), list(s["choices_wrong"])),
                        "batch": b, "pol": polarity(task, s["choices_right"][0], s["choices_wrong"][0])})
    df = pd.DataFrame(out)
    df["occ"] = df.groupby("key").cumcount()
    return df


# ---------------------------------------------------------------- released per-item outcomes
def load_outcomes(task):
    """credit[(key, occ)][model] for plain and sp, by matching results.csv timestamps to JSON created_at."""
    d, _, chance = TASKDIR[task]
    by_ts = {}
    for f in (UNZ / d / "evals").rglob("*.json"):
        j = json.loads(f.read_text())
        by_ts[(f.name.split("--")[1], j["created_at"])] = j
    cred, check = {"plain": defaultdict(dict), "sp": defaultdict(dict)}, {}
    for row in csv.DictReader(open(REPO / d / "results.csv")):
        v = row["variant"]
        if v not in cred or row["model"].startswith("COT"):
            continue
        m = canon(row["model"])
        j = by_ts[(v, row["timestamp"])]
        occ = Counter()
        tot = 0.0
        for sr in j["sample_results"]:
            s = sr["sample"]
            k = item_key(s["id"], s["body"], list(s["choices_right"]), list(s["choices_wrong"]))
            n_opt = len(s["choices_right"]) + len(s["choices_wrong"])
            ok = {f"({chr(65 + i)})" for i in range(n_opt)} | set(s["choices_right"]) | set(s["choices_wrong"])
            if sr["score"] == 1:
                c = 1.0
            elif sr.get("output_parsed") in ok:
                c = 0.0
            else:
                c = chance
            tot += c
            cred[v][(k, occ[k])][m] = c
            occ[k] += 1
        check[f"{m}|{v}"] = abs(tot / len(j["sample_results"]) - float(row["score"]))
    return cred, check


# ---------------------------------------------------------------- statistics helpers
def rowcorr(A, v):
    a = A - A.mean(1, keepdims=True)
    b = v - v.mean()
    return (a @ b) / np.sqrt((a * a).sum(1) * (b @ b))


def rank(A):
    return np.argsort(np.argsort(A, 1), 1).astype(float)


def rowspear(A, Bm):
    ra, rb = rank(A), rank(Bm)
    ra -= ra.mean(1, keepdims=True)
    rb -= rb.mean(1, keepdims=True)
    return (ra * rb).sum(1) / np.sqrt((ra * ra).sum(1) * (rb * rb).sum(1))


def pct(a, lo=2.5, hi=97.5):
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    return [round(float(np.percentile(a, lo)), 3), round(float(np.percentile(a, hi)), 3)]


def r3(x):
    return None if x is None or not np.isfinite(x) else round(float(x), 3)


class T:
    def __init__(self, task, feats, models):
        it = load_items(task)
        f = feats[feats.task == task].copy()
        f["occ"] = f.groupby("key").cumcount()
        it = it.merge(f[["key", "occ", "group", "shortcut_right"]], on=["key", "occ"], how="left", validate="1:1")
        assert it.group.notna().all(), task
        cred, self.check = load_outcomes(task)
        self.it, self.models, self.task, self.chance = it, models, task, TASKDIR[task][2]
        idx = list(zip(it.key, it.occ))
        self.X = {v: np.array([[cred[v].get(k, {}).get(m, np.nan) for m in models] for k in idx]) for v in cred}
        g = pd.factorize(it.group)[0]
        self.g, self.ng = g, g.max() + 1
        cnt = RNG.multinomial(self.ng, np.full(self.ng, 1 / self.ng), size=B)
        self.W = cnt[:, g].astype(float)

    def m(self, name):
        sr, pol = self.it.shortcut_right.to_numpy(), self.it.pol.to_numpy()
        return {"full": np.ones(len(sr), bool), "S": sr == 1, "R": sr == 0,
                "deny": pol == "deny", "affirm": pol == "affirm"}[name]

    def score(self, mask, v="plain", boot=False, cols=None):
        X = self.X[v][mask]
        if cols is not None:
            X = X[:, cols]
        M = np.isfinite(X)
        X0 = np.where(M, X, 0.0)
        if not boot:
            return X0.sum(0) / M.sum(0)
        W = self.W[:, mask]
        return (W @ X0) / (W @ M)


def sad(scores):
    num = den = 0.0
    for c, ts in CATS.items():
        have = [t for t in ts if t in scores]
        for t in have:
            num += scores[t] / len(ts)
            den += 1 / len(ts)
    return num / den


def released():
    out = {}
    for t, f in CSV.items():
        for r in csv.DictReader(open(REPO / f)):
            v = r.get("variant", "plain")
            if v not in ("plain", "sp") or r["model"].startswith("COT") or not r["score"]:
                continue
            out.setdefault((canon(r["model"]), v), {})[t] = float(r["score"])
    return out


def main():
    head = (REPO / ".git").exists() and __import__("subprocess").run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    assert head == SHA, head
    feats = pd.read_csv(AUD / "results/features.csv")
    rel = released()
    models = sorted({m for (m, v) in rel if v == "plain"})
    assert len(models) == 21
    MM = read_mmlu()
    mm = [m for m in models if m in MM]
    mmlu = np.array([MM[m] for m in mm])
    imm = [models.index(m) for m in mm]
    out = {"pin": SHA, "models": models, "mmlu_models": mm, "bootstrap": B, "tasks": {}}

    # website check of the overall aggregation
    web = {}
    ren = {"claude-3-haiku": "claude-3-haiku-20240307", "claude-3-sonnet": "claude-3-sonnet-20240229",
           "claude-3-opus": "claude-3-opus-20240229", "claude-3.5-sonnet": "claude-3-5-sonnet-20240620"}
    for r in csv.DictReader(open(REPO / "results/plots/website/data.csv")):
        if r["type"] == "SAD" and r["variant"] == "Plain Prompt":
            web[ren.get(r["model"], r["model"])] = float(r["score"])
    pub = np.array([sad(rel[(m, "plain")]) for m in models])
    out["overall_aggregation_max_abs_diff_vs_website"] = r3(max(abs(pub[i] - web[m]) for i, m in enumerate(models)))

    TT = {t: T(t, feats, models) for t in AFFECTED}
    for t, X in TT.items():
        d = {"reproduction_max_abs_diff_vs_results_csv": r3(max(X.check.values())),
             "runs_over_0.001": sorted(k for k, v in X.check.items() if v > 1e-3)}
        it = X.it
        nt = it.shortcut_right.notna()
        ct = pd.crosstab(it.pol[nt], it.shortcut_right[nt].map({1.0: "S", 0.0: "R"}))
        d["crosstab_answer_type_by_stratum"] = {str(i): {str(c): int(ct.loc[i, c]) for c in ct.columns} for i in ct.index}
        d["answer_type_share_all_items"] = {str(k): round(v / len(it), 3) for k, v in Counter(it.pol).items()}
        if t != "stages_full":
            two = nt & it.pol.isin(["deny", "affirm"])
            # does "keyed choice denies" reproduce S (and "keyed choice affirms" R)?
            agree = float(((it.pol == "deny") == (it.shortcut_right == 1))[two].mean())
            d["agreement_deny_eq_S"] = r3(agree)
            d["share_R_that_affirm"] = r3(float((it.pol[nt & (it.shortcut_right == 0)] == "affirm").mean()))
            d["share_S_that_deny"] = r3(float((it.pol[nt & (it.shortcut_right == 1)] == "deny").mean()))
            d["n_two_type_non_tie"] = int(two.sum())
        else:
            d["share_R_by_label"] = {str(k): round(v, 3) for k, v in (it.pol[it.shortcut_right == 0].value_counts(normalize=True)).items()}

        S, R, F = X.score(X.m("S")), X.score(X.m("R")), X.score(X.m("full"))
        bS, bR, bF = X.score(X.m("S"), boot=True), X.score(X.m("R"), boot=True), X.score(X.m("full"), boot=True)
        d["n"] = {k: int(X.m(k).sum()) for k in ("full", "S", "R", "deny", "affirm")}
        d["scores_plain"] = {m: {"full": r3(F[i]), "S": r3(S[i]), "R": r3(R[i])} for i, m in enumerate(models)}
        # ---- claim 1: rank agreement S vs R
        rho = spearmanr(S, R).statistic
        c1 = {"spearman_S_R": r3(rho), "ci95": pct(rowspear(bS, bR))}
        non = X.m("S") | X.m("R")
        nR = int(X.m("R").sum())
        # (a) random split of non-tie items into sets of the S and R sizes, by cluster
        gl = np.unique(X.g[non])
        sizes = np.bincount(X.g[non], minlength=X.ng)
        pl = []
        for _ in range(1000):
            p = RNG.permutation(gl)
            cut = np.searchsorted(np.cumsum(sizes[p]), nR) + 1
            Rg = np.zeros(X.ng, bool)
            Rg[p[:cut]] = True
            pl.append(spearmanr(X.score(non & ~Rg[X.g]), X.score(non & Rg[X.g])).statistic)
        c1["placebo_random_split_2.5_97.5"] = pct(pl)
        # (b) answer-type-matched placebo: re-split at random WITHIN each answer type, keeping the
        #     S/R counts of each type. Removes everything the shortcut knows beyond the answer type.
        pol = it.pol.to_numpy()
        sr = it.shortcut_right.to_numpy()
        pm = []
        for _ in range(1000):
            newR = np.zeros(len(sr), bool)
            for ty in np.unique(pol[non]):
                ids = np.flatnonzero(non & (pol == ty))
                k = int(((sr == 0) & (pol == ty)).sum())
                newR[RNG.choice(ids, k, replace=False)] = True
            pm.append(spearmanr(X.score(non & ~newR), X.score(newR)).statistic)
        c1["placebo_answer_type_matched_2.5_50_97.5"] = pct(pm) [:1] + [r3(np.median(pm))] + pct(pm)[1:]
        c1["observed_inside_type_matched_placebo"] = bool(np.percentile(pm, 2.5) <= rho <= np.percentile(pm, 97.5))
        if t != "stages_full":
            D, A = X.score(X.m("deny")), X.score(X.m("affirm"))
            c1["spearman_denykeyed_vs_affirmkeyed"] = r3(spearmanr(D, A).statistic)
        d["claim1"] = c1
        # ---- claim 2: r with MMLU
        c2 = {s: {"r": r3(pearsonr(v[imm], mmlu).statistic), "ci95": pct(rowcorr(bv[:, imm], mmlu))}
              for s, v, bv in (("full", F, bF), ("S", S, bS), ("R", R, bR))}
        d["claim2"] = c2
        # ---- lean decomposition and balanced score
        if t != "stages_full":
            D, A = X.score(X.m("deny")), X.score(X.m("affirm"))
            bD, bA = X.score(X.m("deny"), boot=True), X.score(X.m("affirm"), boot=True)
            nD, nA = int(X.m("deny").sum()), int(X.m("affirm").sum())
            wD = nD / (nD + nA)
            bal = (D + A) / 2
            bbal = (bD + bA) / 2
            k = D + A - 1                         # Youden J: knowledge beyond lean
            lean = np.where(k < 1, (D - k) / np.maximum(1 - k, 1e-9), np.nan)  # P(pick deny | not known)
            twoF = (D * nD + A * nA) / (nD + nA)  # score on the two-type items as published (count-weighted)
            prem = twoF - bal
            sbal = (S + R) / 2
            d["balance"] = {"n_deny_keyed": nD, "n_affirm_keyed": nA, "deny_share": r3(wD),
                            "n_other": int((it.pol == "other").sum())}
            d["per_model"] = {m: {"acc_deny_keyed": r3(D[i]), "acc_affirm_keyed": r3(A[i]), "type_balanced": r3(bal[i]),
                                  "published_two_type": r3(twoF[i]), "lean_premium_points": r3(100 * prem[i]),
                                  "knowledge_J": r3(k[i]), "lean_P_deny": r3(lean[i])} for i, m in enumerate(models)}
            d["lean_summary"] = {
                "premium_points_mean": r3(100 * prem.mean()), "premium_points_min_max": [r3(100 * prem.min()), r3(100 * prem.max())],
                "premium_top10_by_full": r3(100 * np.mean(prem[np.argsort(-F)[:10]])),
                "spearman_full_vs_type_balanced": r3(spearmanr(F, bal).statistic),
                "r_mmlu_type_balanced": r3(pearsonr(bal[imm], mmlu).statistic),
                "r_mmlu_type_balanced_ci95": pct(rowcorr(bbal[:, imm], mmlu)),
                "r_mmlu_stratum_balanced": r3(pearsonr(sbal[imm], mmlu).statistic),
                "spearman_full_vs_stratum_balanced": r3(spearmanr(F, sbal).statistic),
                "r_mmlu_knowledge_J": r3(pearsonr(k[imm], mmlu).statistic),
                "r_mmlu_lean_P_deny": r3(pearsonr(np.nan_to_num(lean[imm], nan=0.5), mmlu).statistic),
                "r_mmlu_premium": r3(pearsonr(prem[imm], mmlu).statistic),
                "r_mmlu_deny_keyed": r3(pearsonr(D[imm], mmlu).statistic),
                "r_mmlu_affirm_keyed": r3(pearsonr(A[imm], mmlu).statistic)}
            # ---- simulation: knowledge k (real, varies) + lean p, items as in the task
            nSD = int((X.m("S") & X.m("deny")).sum()); nSA = int((X.m("S") & X.m("affirm")).sum())
            nRD = int((X.m("R") & X.m("deny")).sum()); nRA = int((X.m("R") & X.m("affirm")).sum())
            kk = np.clip(k, 0, 1)
            pp = np.clip(np.nan_to_num(lean, nan=0.5), 0, 1)

            def sim(kv, pv, reps=500):
                rhos, rRs, rFs, rBs = [], [], [], []
                pD = kv + (1 - kv) * pv
                pA = kv + (1 - kv) * (1 - pv)
                for _ in range(reps):
                    sD = RNG.binomial(nSD, pD); sA = RNG.binomial(nSA, pA)
                    rD = RNG.binomial(nRD, pD); rA = RNG.binomial(nRA, pA)
                    s_ = (sD + sA) / (nSD + nSA); r_ = (rD + rA) / (nRD + nRA)
                    f_ = (sD + sA + rD + rA) / (nSD + nSA + nRD + nRA)
                    b_ = ((sD + rD) / (nSD + nRD) + (sA + rA) / (nSA + nRA)) / 2
                    rhos.append(spearmanr(s_, r_).statistic)
                    rRs.append(pearsonr(r_[imm], mmlu).statistic)
                    rFs.append(pearsonr(f_[imm], mmlu).statistic)
                    rBs.append(pearsonr(b_[imm], mmlu).statistic)
                f = lambda a: [r3(np.percentile(a, 2.5)), r3(np.median(a)), r3(np.percentile(a, 97.5))]
                return {"spearman_S_R": f(rhos), "r_mmlu_R": f(rRs), "r_mmlu_full": f(rFs), "r_mmlu_balanced": f(rBs)}
            sims = {"cells_S_deny_S_affirm_R_deny_R_affirm": [nSD, nSA, nRD, nRA],
                    "fitted_k_and_lean": sim(kk, pp),
                    "fitted_k_no_lean": sim(kk, np.full_like(pp, 0.5)),
                    "fitted_k_leans_shuffled_across_models": sim(kk, RNG.permutation(pp))}
            # generic: knowledge rises with MMLU (r ~ 0.8 by construction), lean independent of it
            gen = {}
            zz = (np.array([MM.get(m, np.nan) for m in models]))
            zz = np.where(np.isfinite(zz), zz, np.nanmean(zz))
            zz = (zz - zz.mean()) / zz.std()
            for sd in (0.0, 0.1, 0.2, 0.3):
                res = []
                for _ in range(200):
                    kv = np.clip(0.5 + 0.15 * zz + RNG.normal(0, 0.09, len(models)), 0, 0.98)
                    pv = np.clip(0.5 + RNG.normal(0, sd, len(models)), 0, 1)
                    res.append(sim(kv, pv, reps=1))
                gen[f"lean_sd_{sd}"] = {k2: r3(np.median([r[k2][1] for r in res])) for k2 in ("spearman_S_R", "r_mmlu_R", "r_mmlu_full", "r_mmlu_balanced")}
            sims["generic_knowledge_tracks_mmlu_lean_independent_median"] = gen
            d["simulation"] = sims
        # ---- claims 3 and 4 by answer type: chat - base, and sp - plain (chat models)
        if t != "stages_full":
            base = {b for b, _ in PAIRS}
            chat = [i for i, m in enumerate(models) if m not in base]
            ib, ic_ = [models.index(b) for b, _ in PAIRS], [models.index(c) for _, c in PAIRS]
            ct = {}
            for k_ in ("full", "S", "R", "deny", "affirm"):
                v = X.score(X.m(k_))
                ct[k_] = r3(100 * np.mean(v[ic_] - v[ib]))
            ct["type_balanced"] = r3((ct["deny"] + ct["affirm"]) / 2)
            d["claim3_chat_minus_base_points"] = ct
            sp = {}
            for k_ in ("full", "S", "R", "deny", "affirm"):
                g_ = X.score(X.m(k_), "sp") - X.score(X.m(k_), "plain")
                sp[k_] = r3(100 * np.nanmean(g_[chat]))
            sp["type_balanced"] = r3((sp["deny"] + sp["affirm"]) / 2)
            gb = sum(X.score(X.m(k_), "sp", boot=True) - X.score(X.m(k_), "plain", boot=True) for k_ in ("deny", "affirm")) / 2
            sp["type_balanced_ci95"] = [round(100 * x, 1) for x in pct(np.nanmean(gb[:, chat], 1))]
            gR = X.score(X.m("R"), "sp", boot=True) - X.score(X.m("R"), "plain", boot=True)
            sp["R_ci95"] = [round(100 * x, 1) for x in pct(np.nanmean(gR[:, chat], 1))]
            Dp, Ap = X.score(X.m("deny"), "plain"), X.score(X.m("affirm"), "plain")
            Ds, As = X.score(X.m("deny"), "sp"), X.score(X.m("affirm"), "sp")
            # knowledge J = D + A - 1; lean shift = change in (D - A)/2
            sp["delta_knowledge_J_points"] = r3(100 * np.nanmean(((Ds + As) - (Dp + Ap))[chat]))
            sp["delta_lean_half_D_minus_A_points"] = r3(100 * np.nanmean((((Ds - As) - (Dp - Ap)) / 2)[chat]))
            d["claim4_sp_minus_plain_chat_points"] = sp
        # ---- family leave-one-out
        lofo = {}
        for fam in ("llama", "openai", "anthropic"):
            keep = [i for i, m in enumerate(models) if family(m) != fam]
            km = [j for j, m in enumerate(mm) if family(m) != fam]
            ki = [models.index(mm[j]) for j in km]
            e = {"n_models": len(keep), "n_mmlu_models": len(km),
                 "spearman_S_R": r3(spearmanr(S[keep], R[keep]).statistic),
                 "r_mmlu_full": r3(pearsonr(F[ki], mmlu[km]).statistic),
                 "r_mmlu_R": r3(pearsonr(R[ki], mmlu[km]).statistic)}
            if t != "stages_full":
                e["r_mmlu_type_balanced"] = r3(pearsonr(bal[ki], mmlu[km]).statistic)
            lofo[f"drop_{fam}"] = e
        d["leave_one_family_out"] = lofo
        out["tasks"][t] = d

    # ---- overall SAD with the four tasks restricted: R, and type-balanced
    def overall(fn):
        v = []
        for i, m in enumerate(models):
            s = dict(rel[(m, "plain")])
            for t in AFFECTED:
                s[t] = fn(t, i)
            v.append(sad(s))
        return np.array(v)
    sc = {t: {k: TT[t].score(TT[t].m(k)) for k in ("full", "S", "R", "deny", "affirm")} for t in AFFECTED}
    ovR = overall(lambda t, i: sc[t]["R"][i])
    ovBal = overall(lambda t, i: (sc[t]["deny"][i] + sc[t]["affirm"][i]) / 2 if t != "stages_full" else rel[(models[i], "plain")][t])
    ovFull = overall(lambda t, i: rel[(models[i], "plain")][t])
    # bootstrap for overall R
    bR = {t: TT[t].score(TT[t].m("R"), boot=True) for t in AFFECTED}
    bD = {t: TT[t].score(TT[t].m("deny"), boot=True) for t in AFFECTED if t != "stages_full"}
    bA = {t: TT[t].score(TT[t].m("affirm"), boot=True) for t in AFFECTED if t != "stages_full"}
    # overall is linear in task scores: overall = pub + sum_t w_t (new_t - rel_t)
    w = {t: 1 / len(ts) / len(CATS) for ts in CATS.values() for t in ts}
    full_rel = np.array([[rel[(m, "plain")][t] for m in models] for t in AFFECTED])
    assert np.allclose(ovFull, pub)
    def lin(newmat):  # newmat: dict t -> (B, models)
        o = np.tile(pub, (B, 1))
        for j, t in enumerate(AFFECTED):
            if t in newmat:
                o = o + w[t] * (newmat[t] - full_rel[j])
        return o
    BR = lin(bR)
    BB = lin({t: (bD[t] + bA[t]) / 2 for t in bD})
    assert np.allclose(np.median(BR, 0), ovR, atol=0.03)
    top3 = lambda v: [models[i] for i in np.argsort(-v)[:3]]
    c3 = ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"]
    g4 = ["gpt-4-0613", "gpt-4-0125-preview"]
    ic, ig = [models.index(m) for m in c3], [models.index(m) for m in g4]
    gap = lambda v: v[..., ic].mean(-1) - v[..., ig].mean(-1)
    out["overall"] = {
        "published_r_mmlu": r3(pearsonr(pub[imm], mmlu).statistic),
        "R": {"spearman_with_published": r3(spearmanr(ovR, pub).statistic), "ci95": pct(rowspear(BR, np.tile(pub, (B, 1)))),
              "r_mmlu": r3(pearsonr(ovR[imm], mmlu).statistic), "r_mmlu_ci95": pct(rowcorr(BR[:, imm], mmlu)),
              "top3": top3(ovR), "claude3_minus_gpt4_points": r3(100 * gap(ovR)), "gap_ci95_points": [round(100 * x, 1) for x in pct(gap(BR))]},
        "type_balanced_FHD_INF_SO": {"spearman_with_published": r3(spearmanr(ovBal, pub).statistic),
                                    "r_mmlu": r3(pearsonr(ovBal[imm], mmlu).statistic), "top3": top3(ovBal),
                                    "claude3_minus_gpt4_points": r3(100 * gap(ovBal)), "gap_ci95_points": [round(100 * x, 1) for x in pct(gap(BB))]},
        "published": {"top3": top3(pub), "claude3_minus_gpt4_points": r3(100 * gap(pub))},
        "max_shift_points_type_balanced_vs_published": r3(100 * np.abs(ovBal - pub).max()),
        "mean_shift_points_type_balanced_vs_published": r3(100 * (ovBal - pub).mean()),
        "per_model_type_balanced_minus_published_points": {m: r3(100 * (ovBal[i] - pub[i])) for i, m in enumerate(models)},
    }
    # task-level Claude 3 - GPT-4 on each scoring
    tg = {}
    for t in ("facts_human_defaults", "influence", "stages_oversight"):
        s_ = sc[t]
        X = TT[t]
        bb = (X.score(X.m("deny"), boot=True) + X.score(X.m("affirm"), boot=True)) / 2
        tg[t] = {"full": r3(100 * gap(s_["full"])), "R": r3(100 * gap(s_["R"])), "S": r3(100 * gap(s_["S"])),
                 "type_balanced": r3(100 * gap((s_["deny"] + s_["affirm"]) / 2)),
                 "type_balanced_ci95": [round(100 * x, 1) for x in pct(gap(bb))]}
    out["claude3_minus_gpt4_by_task_points"] = tg
    (HERE / "validation.json").write_text(json.dumps(out, indent=1) + "\n")
    # console summary
    for t, d in out["tasks"].items():
        print(t, d["n"], d.get("agreement_deny_eq_S"), d["crosstab_answer_type_by_stratum"])
        print("  C1", d["claim1"])
        print("  C2", d["claim2"])
        if "lean_summary" in d:
            print("  C3", d["claim3_chat_minus_base_points"], "\n  C4", d["claim4_sp_minus_plain_chat_points"])
            print("  premium", {m: (v["lean_premium_points"], v["acc_deny_keyed"], v["acc_affirm_keyed"]) for m, v in d["per_model"].items()})
            print("  bal", d["balance"], d["lean_summary"])
            print("  sim", json.dumps(d["simulation"]))
        print("  lofo", d["leave_one_family_out"])
    print(json.dumps({k: v for k, v in out["overall"].items() if not k.startswith("per_model")}, indent=0))
    print(out["claude3_minus_gpt4_by_task_points"], out["overall_aggregation_max_abs_diff_vs_website"])


if __name__ == "__main__":
    main()
