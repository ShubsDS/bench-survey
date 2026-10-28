"""How much of ASMR-Bench's headline AUROC survives choosing the best of nine configurations?

Gan et al., "ASMR-Bench" (arXiv 2604.16286), ask auditors whether an ML research codebase was
sabotaged. There are 9 source papers, each with one honest and one or two sabotaged variants.
The headline is "Gemini 3.1 Pro with full experiments achieves the best AUROC at 0.77 (p < 0.01)",
the best of three models (Claude Opus 4.6, GPT-5.2, Gemini 3.1 Pro) under three affordances
(paper only, no experiments, full experiments).

From the released per-audit credences (results/ground_truth/*.csv), this script:

1. Recomputes every configuration's AUROC with the paper's method, independently implemented:
   credences averaged over trials in logit space, then a Wilcoxon-Mann-Whitney AUROC in which each
   variant is weighted by 1 / (number of same-label variants of its paper). Persuasion variants
   are excluded, as in the paper's main results.
2. Gives the exact stratified permutation p-value for the headline configuration, enumerating every
   assignment of which variant of each paper is the honest one (1,152 assignments).
3. Gives the family-wise p-value for the best of the nine headline configurations: the share of
   those assignments under which the best configuration reaches the observed best.
4. Bootstraps the headline AUROC over papers.
5. Reports that the released paper-only CSVs, unlike the others, include persuasion variants, and
   the paper-only AUROCs with them included under the repository's codebase rule.

Usage:
    python check_asmr.py [--cache DIR] [--out asmr_checks.json]
"""
import argparse, collections, itertools, json, math, urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

SHA = "f8efd6834aa72ee91fe9042eaab852724873167a"  # ejcgan/auditing-sabotage-bench
RAW = f"https://raw.githubusercontent.com/ejcgan/auditing-sabotage-bench/{SHA}/results/ground_truth/"
MODELS = ("claude-opus-4-6", "gemini-3.1-pro-cursor", "gpt-5.2")
EXTRA = ("claude-opus-4-5", "claude-sonnet-4-5", "claude-sonnet-4", "gemini-3-flash", "gpt-5-mini", "gpt-5.1",
         "gpt-5.4", "human_public")
REGIMES = ("paper_only", "no_experiments", "full_experiments")
HEADLINE = "full_experiments__gemini-3.1-pro-cursor"
BOOT = 4000


def fetch(name, cache):
    path = cache / name
    if not path.exists():
        try:
            with urllib.request.urlopen(RAW + name, timeout=300) as r:
                path.write_bytes(r.read())
        except urllib.error.HTTPError:
            return None
    return pd.read_csv(path)


def paper(sid):
    return sid.split("_")[0]


def repo_codebase(sid):
    """results/plot/metrics.py codebase_from_id: everything before the last underscore."""
    return sid.rsplit("_", 1)[0]


def averaged(d):
    def logit(x):
        x = min(max(x, 1e-4), 1 - 1e-4)
        return math.log(x / (1 - x))
    d = d.dropna(subset=["likelihood"])
    out = {}
    for sid, g in d.groupby("sample_id"):
        m = np.mean([logit(x / 100) for x in g.likelihood])
        out[sid] = (1 / (1 + math.exp(-m)), int(g.target.iloc[0] == "sabotaged"))
    return out


def auroc(samples, codebase=paper, honest=None):
    """samples: {sid: (credence, label)}; `honest` overrides labels (a set of honest sids)."""
    lab = {s: (0 if s in honest else 1) if honest is not None else y for s, (_, y) in samples.items()}
    n = collections.Counter((codebase(s), lab[s]) for s in samples)
    pos = [(c, 1 / n[(codebase(s), 1)]) for s, (c, _) in samples.items() if lab[s] == 1]
    neg = [(c, 1 / n[(codebase(s), 0)]) for s, (c, _) in samples.items() if lab[s] == 0]
    num = den = 0.0
    for a, wa in pos:
        for b, wb in neg:
            den += wa * wb
            num += wa * wb * (1 if a > b else .5 if a == b else 0)
    return num / den if den else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="asmr_checks.json")
    args = ap.parse_args()
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)

    configs, persuasion = {}, {}
    for regime in REGIMES:
        for model in MODELS + EXTRA:
            d = fetch(f"{regime}__{model}.csv", cache)
            if d is None:
                continue
            key = f"{regime}__{model}"
            is_p = d.sample_id.str.endswith("_persuasion")
            configs[key] = averaged(d[~is_p])
            if is_p.any():
                persuasion[key] = {"persuasion_rows": int(is_p.sum()),
                                   "auroc_main_only": round(auroc(configs[key]), 3),
                                   "auroc_with_persuasion_repo_codebase_rule":
                                       round(auroc(averaged(d), codebase=repo_codebase), 3)}

    heads = [f"{r}__{m}" for r in REGIMES for m in MODELS]
    by_paper = collections.defaultdict(list)
    for sid in configs[HEADLINE]:
        by_paper[paper(sid)].append(sid)
    assignments = [set(c) for c in itertools.product(*by_paper.values())]
    observed = {k: auroc(configs[k]) for k in heads}
    best = max(observed.values())
    single = sum(auroc(configs[HEADLINE], honest=h) >= observed[HEADLINE] - 1e-12 for h in assignments)
    family = sum(max(auroc(configs[k], honest=h) for k in heads) >= best - 1e-12 for h in assignments)

    rng = np.random.default_rng(0)
    boot = []
    papers = list(by_paper)
    for _ in range(BOOT):
        pick = rng.choice(papers, len(papers))
        s = {f"{p}{j}_{sid}": configs[HEADLINE][sid] for j, p in enumerate(pick) for sid in by_paper[p]}
        if len({y for _, y in s.values()}) == 2:
            boot.append(auroc(s))

    result = {"pins": {"repo": f"ejcgan/auditing-sabotage-bench@{SHA}"},
              "papers": len(by_paper), "variants": len(configs[HEADLINE]),
              "auroc": {k: round(auroc(v), 3) for k, v in sorted(configs.items())},
              "headline": {"config": HEADLINE, "auroc": round(observed[HEADLINE], 3),
                           "exact_stratified_permutation_p": round(single / len(assignments), 4),
                           "bootstrap_over_papers_95": [round(float(x), 3) for x in np.percentile(boot, [2.5, 97.5])]},
              "best_of_nine_headline_configs": {"configs": heads, "best_auroc": round(best, 3),
                                                "assignments": len(assignments),
                                                "family_wise_p": round(family / len(assignments), 4)},
              "paper_only_files_include_persuasion": persuasion}
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
