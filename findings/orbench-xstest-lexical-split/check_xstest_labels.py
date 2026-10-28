"""Check 6 on XSTest: do the released automatic refusal classifiers agree with the released
human labels?

Files (xstest commit d7bb5bd): evaluation/automated_evaluation_labels/
xstest_v2_completions_<model>_{streval,gpteval}.csv for 5 models (450 completions each). Each row
holds two human annotations, an agreement flag, the human final_label (1_full_compliance,
2_full_refusal, 3_partial_refusal) and one automatic label: strmatch_label (the repo's prefix
string match, which only outputs 1 or 2) or gpt4_label (the repo's GPT-4 prompt).

Binary refusal = final label 2 or 3 (the XSTest paper counts partial refusals as refusals in its
headline refusal rates). Reported per model and prompt label (safe / unsafe): human refusal rate,
automatic refusal rate, and the confusion of the automatic label against the human one. Nothing is
executed from the repo; the CSVs are read as data.

Usage: python -I check_xstest_labels.py [--cache data] [--out xstest_label_checks.json]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd

from common import XS_COMMIT, XS_MODELS, wilson

REF = {"2_full_refusal", "3_partial_refusal"}


def kappa(a, b):
    a, b = pd.Series(a).astype(int), pd.Series(b).astype(int)
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return round(float((po - pe) / (1 - pe)), 3) if pe < 1 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="xstest_label_checks.json")
    a = ap.parse_args()
    base = Path(a.cache) / "xstest" / "evaluation" / "automated_evaluation_labels"
    res = {"source": {"xstest_commit": XS_COMMIT}, "refusal_definition": "final label 2 or 3",
           "models": {}}
    pooled = {k: {"safe": [0, 0, 0, 0], "unsafe": [0, 0, 0, 0]} for k in ["strmatch", "gpt4"]}
    for m in XS_MODELS:
        s = pd.read_csv(base / f"xstest_v2_completions_{m}_streval.csv")
        g = pd.read_csv(base / f"xstest_v2_completions_{m}_gpteval.csv")
        assert (s.id == g.id).all() and (s.final_label == g.final_label).all()
        s["unsafe"] = s.type.str.startswith("contrast_")
        s["human"] = s.final_label.isin(REF)
        s["strmatch"] = s.strmatch_label.isin(REF)
        s["gpt4"] = g.gpt4_label.str.strip().isin(REF)
        r = {"n": len(s), "human_annotator_agreement": round(float(s.agreement.mean()), 4),
             "human_partial_refusals": int((s.final_label == "3_partial_refusal").sum())}
        for lab, sub in [("safe", s[~s.unsafe]), ("unsafe", s[s.unsafe])]:
            e = {"n": len(sub), "human_refusal_rate": round(float(sub.human.mean()), 4)}
            for k in ["strmatch", "gpt4"]:
                tp = int((sub[k] & sub.human).sum()); fp = int((sub[k] & ~sub.human).sum())
                fn = int((~sub[k] & sub.human).sum()); tn = int((~sub[k] & ~sub.human).sum())
                for i, v in enumerate([tp, fp, fn, tn]):
                    pooled[k][lab][i] += v
                e[k] = {"refusal_rate": round(float(sub[k].mean()), 4),
                        "agree": round(float((sub[k] == sub.human).mean()), 4),
                        "agree_ci95": wilson(int((sub[k] == sub.human).sum()), len(sub)),
                        "kappa": kappa(sub[k], sub.human),
                        "missed_refusals": fn, "false_refusals": fp,
                        "missed_partial_refusals": int((~sub[k] & (sub.final_label == "3_partial_refusal")).sum())}
            r[lab] = e
        res["models"][m] = r
    res["pooled"] = {}
    for k, d in pooled.items():
        res["pooled"][k] = {}
        for lab, (tp, fp, fn, tn) in d.items():
            n = tp + fp + fn + tn
            res["pooled"][k][lab] = {"n": n, "agree": round((tp + tn) / n, 4), "agree_ci95": wilson(tp + tn, n),
                                     "missed_refusals": fn, "false_refusals": fp,
                                     "human_refusals": tp + fn, "auto_refusals": tp + fp}
    # Does the string match preserve the ordering of models on safe-prompt refusal?
    order = lambda key: sorted(XS_MODELS, key=lambda m: res["models"][m]["safe"][key] if key == "human_refusal_rate"
                               else res["models"][m]["safe"][key]["refusal_rate"])
    res["safe_refusal_order"] = {"human": order("human_refusal_rate"), "strmatch": order("strmatch"),
                                 "gpt4": order("gpt4")}
    Path(a.out).write_text(json.dumps(res, indent=1))
    for m, r in res["models"].items():
        print(m, "safe human", r["safe"]["human_refusal_rate"], "str", r["safe"]["strmatch"]["refusal_rate"],
              "gpt", r["safe"]["gpt4"]["refusal_rate"], "| unsafe human", r["unsafe"]["human_refusal_rate"],
              "str", r["unsafe"]["strmatch"]["refusal_rate"], "gpt", r["unsafe"]["gpt4"]["refusal_rate"],
              "| agree str safe", r["safe"]["strmatch"]["agree"], "unsafe", r["unsafe"]["strmatch"]["agree"])
    print(json.dumps(res["pooled"], indent=1)); print(res["safe_refusal_order"])


if __name__ == "__main__":
    main()
