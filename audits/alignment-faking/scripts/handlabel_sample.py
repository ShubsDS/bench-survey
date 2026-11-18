"""Draw a blind sample of PM-compliant outputs for hand labelling (A3 validation).

    data/.venv/bin/python -I scripts/handlabel_sample.py > data/handlabel_view.txt

Prints item number, then the first 500 characters of the final output only (no tier, no labels).
The key (item -> setting/variant/tier/qid and released labels) is written to
data/handlabel_key.csv, which is read only after labelling. Nothing printed here is committed.
"""
import json
import os
import re

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
ROOT = os.path.join(DATA, "jo", "json_outputs")


def main():
    d = pd.read_parquet(os.path.join(DATA, "samples.parquet"))
    d = d[(d.setting == "helpful_only") & d.lab_pm_score.notna()]
    d = d[d.variant.str.startswith("atn_honly") & ~d.variant.str.contains("sonnet|haiku|gpt|no_cot")]
    d = d[d.lab_pm_score >= -0.7]
    d["fi"] = d.lab_follows_instructions == "True"
    rng = np.random.default_rng(7)
    parts = []
    for tier, k in (("train", 12), ("deploy", 8)):
        for fi in (True, False):
            pool = d[(d.tier == tier) & (d.fi == fi)]
            parts.append(pool.sample(n=min(k, len(pool)), random_state=int(rng.integers(1e9))))
    s = pd.concat(parts).sample(frac=1, random_state=3).reset_index(drop=True)
    s["item"] = np.arange(1, len(s) + 1)
    s[["item", "setting", "variant", "tier", "qid", "lab_pm_score", "fi", "lab_effective_scheme"]].to_csv(
        os.path.join(DATA, "handlabel_key.csv"), index=False)
    for _, r in s.iterrows():
        with open(os.path.join(ROOT, r.setting, r.variant, r.tier, r.qid + ".json")) as fh:
            m = json.load(fh)["messages"]
        a = "\n".join(x["content"] for x in m if x["role"] == "assistant")
        outs = re.findall(r"<OUTPUT>(.*?)(?:</OUTPUT>|$)", a, re.S)
        o = (outs[-1] if outs else "").strip()
        print(f"=== item {r['item']}  (output length {len(o)})")
        print(o[:500].replace("\n", " "))
        print()


if __name__ == "__main__":
    main()
