"""Duplicates and near-duplicates: HarmBench validation vs test behaviours, and StrongREJECT prompts
vs HarmBench behaviours (and AdvBench, a source both draw on or sit beside).

Similarity: word 3-gram Jaccard and TF-IDF (word 1-2 gram) cosine on lower-cased prompt text.
HarmBench contextual behaviours are compared on the behaviour string and, separately, on the
context string. Outputs hold ids and scores only.

Usage:
    python -I check_overlap.py [--cache ../data] [--out overlap_checks.json]
"""
import argparse, hashlib, json, re, urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

HB_COMMIT = "8e1604d1171fe8a48d8febecd22f600e462bdcdd"
SR_DATA_COMMIT = "f7cad6c17e624e21d8df2278e918ae1dddb4cb56"
HB = f"https://raw.githubusercontent.com/centerforaisafety/HarmBench/{HB_COMMIT}/data/behavior_datasets/"
SR = f"https://raw.githubusercontent.com/alexandrasouly/strongreject/{SR_DATA_COMMIT}/strongreject_dataset/"
FILES = {
    "hb/harmbench_behaviors_text_test.csv": (HB + "harmbench_behaviors_text_test.csv", "75d257b3e7428c52eb7b0154318f455af3e01b09a3794b5e2f3d36054f3c0e29"),
    "hb/harmbench_behaviors_text_val.csv": (HB + "harmbench_behaviors_text_val.csv", "7bfaaa5e2b9b95002c89e2d33c019f58e9e8496e2fc65d368f1eeb8179e69534"),
    "hb/advbench_behaviors.csv": (HB + "extra_behavior_datasets/advbench_behaviors.csv", "0e635254df9065ae6f8d074534b660fa7a361d1ad269e2c8e1b7377961802a86"),
    "sr/strongreject_dataset.csv": (SR + "strongreject_dataset.csv", "4dd70357e4ff8b5d0ba5ebafecab5d6dd5633ce8046e3dd1c8bd93e64de44381"),
    "sr/strongreject_dataset_2024_02.csv": (SR + "previous_versions/2024_02/strongreject_dataset.csv", "6280fa699a0d8e7b55b55ebaed991e840d45a7595fd902403af1b25557c59d0b"),
}
TH_COS, TH_JAC = 0.7, 0.5


def fetch(cache, rel):
    url, sha = FILES[rel]
    p = Path(cache) / rel
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=120) as r:
            p.write_bytes(r.read())
    got = hashlib.sha256(p.read_bytes()).hexdigest()
    if sha:
        assert got == sha, f"{p}: {got} != {sha}"
    return p, got


def norm(s):
    return re.sub(r"\s+", " ", str(s).replace("’", "'").lower()).strip()


def grams(s, n=3):
    w = re.findall(r"[a-z0-9']+", norm(s))
    return {tuple(w[i:i + n]) for i in range(max(len(w) - n + 1, 1))} if w else set()


def jac_matrix(A, B):
    ga, gb = [grams(a) for a in A], [grams(b) for b in B]
    M = np.zeros((len(A), len(B)))
    for i, x in enumerate(ga):
        for j, y in enumerate(gb):
            if x and y:
                M[i, j] = len(x & y) / len(x | y)
    return M


def cos_matrix(A, B):
    v = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1).fit(list(A) + list(B))
    a, b = v.transform(A), v.transform(B)
    return (a @ b.T).toarray()


def compare(name, A, ida, B, idb, same=False, top=15):
    C, J = cos_matrix(A, B), jac_matrix(A, B)
    if same:
        np.fill_diagonal(C, 0)
        np.fill_diagonal(J, 0)
        C, J = np.triu(C), np.triu(J)
    pairs = []
    for i, j in zip(*np.where((C >= TH_COS) | (J >= TH_JAC))):
        pairs.append({"a": ida[i], "b": idb[j], "cos": round(float(C[i, j]), 3), "jac3": round(float(J[i, j]), 3)})
    pairs.sort(key=lambda d: -d["cos"])
    best_a = C.max(axis=1) if C.size else np.array([])
    return {"name": name, "n_a": len(A), "n_b": len(B),
            "pairs_over_threshold": len(pairs),
            "a_items_with_match_cos_ge_0.7": int((C.max(axis=1) >= 0.7).sum()),
            "a_items_with_match_cos_ge_0.5": int((C.max(axis=1) >= 0.5).sum()),
            "a_items_exact_after_normalising": int(sum(norm(x) in {norm(y) for y in B} for x in A)) if not same else
            int(len(A) - len({norm(x) for x in A})),
            "max_cos_quantiles_of_a": [round(float(q), 3) for q in np.quantile(best_a, [0.5, 0.9, 0.99, 1.0])] if len(best_a) else None,
            "top_pairs": pairs[:top], "all_pairs": pairs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="../data")
    ap.add_argument("--out", default="overlap_checks.json")
    args = ap.parse_args()
    paths, shas = {}, {}
    for k in FILES:
        paths[k], shas[k] = fetch(args.cache, k)
    te = pd.read_csv(paths["hb/harmbench_behaviors_text_test.csv"])
    va = pd.read_csv(paths["hb/harmbench_behaviors_text_val.csv"])
    adv = pd.read_csv(paths["hb/advbench_behaviors.csv"])
    src = pd.read_csv(paths["sr/strongreject_dataset.csv"])
    old = pd.read_csv(paths["sr/strongreject_dataset_2024_02.csv"])
    hb = pd.concat([te.assign(split="test"), va.assign(split="val")], ignore_index=True)
    sr_ids = [f"sr{i}" for i in range(len(src))]
    out = {"pins": {"harmbench_commit": HB_COMMIT, "strongreject_data_commit": SR_DATA_COMMIT, "sha256": shas},
           "thresholds": {"tfidf_cos": TH_COS, "word3_jaccard": TH_JAC},
           "id_note": "HarmBench ids are BehaviorID; StrongREJECT ids are sr<row> in the current strongreject_dataset.csv (0-based); AdvBench ids are adv<row>"}

    # HarmBench val vs test
    out["hb_split_ids_shared"] = sorted(set(te.BehaviorID) & set(va.BehaviorID))
    out["hb_val_vs_test_behavior"] = compare("val behaviour vs test behaviour", va.Behavior.tolist(), va.BehaviorID.tolist(),
                                             te.Behavior.tolist(), te.BehaviorID.tolist())
    tc, vc = te[te.ContextString.notna()], va[va.ContextString.notna()]
    out["hb_val_vs_test_context"] = compare("val context vs test context", vc.ContextString.tolist(), vc.BehaviorID.tolist(),
                                            tc.ContextString.tolist(), tc.BehaviorID.tolist())
    # behaviour + context together, which is what a contextual test case shows the model
    full = lambda d: (d.Behavior + " " + d.ContextString.fillna("")).tolist()
    out["hb_val_vs_test_behavior_plus_context"] = compare("val vs test, behaviour+context", full(va), va.BehaviorID.tolist(), full(te), te.BehaviorID.tolist())
    out["hb_within_all"] = compare("within all 400 (behaviour)", hb.Behavior.tolist(), hb.BehaviorID.tolist(), hb.Behavior.tolist(), hb.BehaviorID.tolist(), same=True)
    # rate of val items with a test near-copy, by functional category
    C = cos_matrix(full(va), full(te))
    va = va.assign(maxcos=C.max(axis=1))
    out["hb_val_maxcos_by_functional"] = {f: {"n": len(g), "ge_0.7": int((g.maxcos >= 0.7).sum()), "ge_0.5": int((g.maxcos >= 0.5).sum())}
                                          for f, g in va.groupby("FunctionalCategory")}
    # StrongREJECT vs HarmBench (all 400)
    out["sr_vs_hb"] = compare("StrongREJECT current vs HarmBench behaviour", src.forbidden_prompt.tolist(), sr_ids,
                              hb.Behavior.tolist(), hb.BehaviorID.tolist())
    for p in out["sr_vs_hb"]["all_pairs"]:
        p["sr_source"] = src.source.iloc[int(p["a"][2:])]
        p["hb_split"] = hb.set_index("BehaviorID").split[p["b"]]
    out["sr_vs_hb_pairs_by_hb_split"] = pd.Series([p["hb_split"] for p in out["sr_vs_hb"]["all_pairs"]]).value_counts().to_dict()
    out["sr_vs_hb_pairs_by_sr_source"] = pd.Series([p["sr_source"] for p in out["sr_vs_hb"]["all_pairs"]]).value_counts().to_dict()
    out["sr_old_vs_hb"] = compare("StrongREJECT 2024_02 vs HarmBench behaviour", old.forbidden_prompt.tolist(), [f"sr_old{i}" for i in range(len(old))],
                                  hb.Behavior.tolist(), hb.BehaviorID.tolist())
    # both against AdvBench
    adv_ids = [f"adv{i}" for i in range(len(adv))]
    acol = "Behavior" if "Behavior" in adv.columns else adv.columns[0]
    out["sr_vs_advbench"] = compare("StrongREJECT vs AdvBench", src.forbidden_prompt.tolist(), sr_ids, adv[acol].tolist(), adv_ids)
    out["sr_vs_advbench_by_declared_source"] = {}
    C = cos_matrix(src.forbidden_prompt.tolist(), adv[acol].tolist())
    for s_, g in src.assign(maxcos=C.max(axis=1)).groupby("source"):
        out["sr_vs_advbench_by_declared_source"][s_] = {"n": len(g), "ge_0.7": int((g.maxcos >= 0.7).sum())}
    out["hb_vs_advbench"] = compare("HarmBench vs AdvBench", hb.Behavior.tolist(), hb.BehaviorID.tolist(), adv[acol].tolist(), adv_ids)
    out["sr_within"] = compare("within StrongREJECT current", src.forbidden_prompt.tolist(), sr_ids, src.forbidden_prompt.tolist(), sr_ids, same=True)
    for k in list(out):
        if isinstance(out[k], dict) and "all_pairs" in out[k] and len(out[k]["all_pairs"]) > 200:
            out[k]["all_pairs"] = out[k]["all_pairs"][:200]
            out[k]["all_pairs_truncated_to"] = 200
    Path(args.out).write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    for k, v in out.items():
        if isinstance(v, dict) and "name" in v:
            print(f"{v['name']:<48} n_a={v['n_a']:<4} pairs={v['pairs_over_threshold']:<4} a>=0.7={v['a_items_with_match_cos_ge_0.7']:<4} "
                  f"a>=0.5={v['a_items_with_match_cos_ge_0.5']:<4} exact={v['a_items_exact_after_normalising']} q={v['max_cos_quantiles_of_a']}")
    print(out["hb_val_maxcos_by_functional"], out["sr_vs_hb_pairs_by_hb_split"], out["sr_vs_hb_pairs_by_sr_source"], out["sr_vs_advbench_by_declared_source"])


if __name__ == "__main__":
    main()
