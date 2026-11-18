"""Post hoc P4 (not pre-registered): answer flipping inside the "unfaithful" bucket.

The release includes the authors' pattern autorater (Claude 3.7 Sonnet, 8k thinking) output for
flagged pairs of six models (`data/unfaithfulness_pattern_eval/T0.0_P0.9_M8000/*hard-2/`). For each
response to the lower-accuracy question it gives `answer_flipping_classification` (the reasoning
supports one answer, the final answer is the other). We count, among the WRONG answers to the
lower-accuracy question of pairs flagged by the released rule, how many the authors' own
autorater marks as answer flipping. A flipped answer is the reverse of a post-hoc rationalisation:
the written reasoning does not support the final answer.

Also writes results/flip_handcheck_sample.csv: 48 wrong responses (8 per model, half marked
flipping, half not, seed 5) for blind hand labelling in flip_labels.csv.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).parent))
from iphr_core import MAIN_DF, build_pairs, flag_pairs, model_arrays  # noqa: E402
from posthoc_hedge import wilson  # noqa: E402
from safe_load import load_df  # noqa: E402

L = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
MODELS = {"claude-3.5-haiku": "anthropic/claude-3.5-haiku", "claude-3.6-sonnet": "anthropic/claude-3.6-sonnet",
          "claude-3.7-sonnet": "anthropic/claude-3.7-sonnet", "claude-3.7-sonnet_1k": "anthropic/claude-3.7-sonnet_1k",
          "claude-3.7-sonnet_64k": "anthropic/claude-3.7-sonnet_64k", "deepseek-chat": "deepseek/deepseek-chat",
          "deepseek-r1": "deepseek/deepseek-r1", "gpt-4o-mini": "openai/gpt-4o-mini",
          "gpt-4o-2024-08-06": "openai/gpt-4o-2024-08-06", "chatgpt-4o-latest": "openai/chatgpt-4o-latest",
          "gemini-pro-1.5": "google/gemini-pro-1.5", "gemini-2.5-flash-preview": "google/gemini-2.5-flash-preview",
          "gemini-2.5-pro-preview": "google/gemini-2.5-pro-preview", "Llama-3.1-70B": "meta-llama/Llama-3.1-70B",
          "Llama-3.3-70B-Instruct": "meta-llama/Llama-3.3-70B-Instruct", "qwq-32b": "qwen/qwq-32b"}


def main():
    P = build_pairs(load_df(MAIN_DF))
    rng = np.random.default_rng(5)
    res, sample = {}, []
    lows = {}
    for short, mid in MODELS.items():
        p = P[P.model_id == mid]
        os_ = (p.total_count_Y.to_numpy() > 10) & (p.total_count_N.to_numpy() > 10)
        f, _ = flag_pairs(p, *model_arrays(p), oversampled=os_)
        q = p[f]
        accY = (q.yes_count_Y + 0.5 * q.unknown_count_Y) / q.total_count_Y
        accN = 1 - (q.yes_count_N + 0.5 * q.unknown_count_N) / q.total_count_N
        low = set(np.where(accN < accY, q.qid_N, q.qid_Y))
        lows[short] = sorted(low)
        wrong = {}
        for fp in sorted(Path("data/faith").glob(f"{short}__*.yaml")):
            d = yaml.load(fp.open(), Loader=L)
            for qid, it in d["questions_by_qid"].items():
                if qid in low:
                    wrong[qid] = set(it["unfaithful_responses"])
        rows = []
        cats = []
        for fp in sorted(Path("data/pat").glob(f"*__{short}.yaml")):
            d = yaml.load(fp.open(), Loader=L)
            for qid, it in d["pattern_analysis_by_qid"].items():
                if qid not in low:
                    continue
                cats.append(tuple(sorted(it.get("categorization_for_pair") or ["missing"])))
                for rid, r in ((it.get("q1_analysis") or {}).get("responses") or {}).items():
                    if rid in wrong.get(qid, set()):
                        rows.append({"qid": qid, "rid": rid, "flip": r.get("answer_flipping_classification"),
                                     "lack_info": r.get("lack_of_information")})
        R = pd.DataFrame(rows)
        n = len(R)
        k = int((R.flip == "YES").sum()) if n else 0
        byq = R.assign(f=(R.flip == "YES")).groupby("qid").f.mean() if n else pd.Series(dtype=float)
        cat_counts = pd.Series([c for cs in cats for c in cs]).value_counts().to_dict()
        res[short] = {"flagged_pairs": int(f.sum()), "pairs_with_pattern_eval": len(cats),
                      "wrong_responses_with_eval": n, "flip_yes": k,
                      "flip_share": k / n if n else None, "flip_share_wilson": wilson(k, n),
                      "pairs_majority_flip": int((byq >= 0.5).sum()),
                      "pairs_majority_flip_share": float((byq >= 0.5).mean()) if len(byq) else None,
                      "lack_of_information_yes_share": float((R.lack_info == "YES").mean()) if n else None,
                      "pair_categories": cat_counts}
        print(short, {kk: v for kk, v in res[short].items() if kk != "pair_categories"})
        for lab in ("YES", "NO"):
            sub = R[R.flip == lab]
            for i in rng.permutation(len(sub))[:4]:
                sample.append({"model": short, "qid": sub.iloc[i].qid, "response_id": sub.iloc[i].rid,
                               "autorater_flip": lab})
    Path("results/posthoc_flip.json").write_text(json.dumps(res, indent=1))
    Path("results/flagged_low_qids.json").write_text(json.dumps(lows))
    S = pd.DataFrame(sample).sample(frac=1, random_state=5).reset_index(drop=True)
    S.insert(0, "item", range(len(S)))
    S.to_csv("results/flip_handcheck_sample.csv", index=False)


if __name__ == "__main__":
    main()
