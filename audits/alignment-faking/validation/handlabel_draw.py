"""Draw the validator's blind hand-label sample (see prereg_validator.md). Writes the key to
data/val_hl_key.csv and the blind view to data/val_hl_view.txt (both git-ignored). Seed 20261117.
"""
import json
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rederive import D, OPUS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
ROOT = os.path.join(DATA, "jo", "json_outputs", "helpful_only")
rng = np.random.default_rng(20261117)

x = D[D.variant.isin(OPUS) & D.pm_score.notna() & D.c_pm].copy()
x["cat"] = np.where(x.refuses, 1, np.where(x.compr, 2, np.where(x.ui, 3, 4)))
aud = pd.read_csv(os.path.join(DATA, "handlabel_key.csv"))
aud["qid"] = aud.qid.astype(int)
akeys = set(zip(aud.variant, aud.tier, aud.qid))
x = x[[k not in akeys for k in zip(x.variant, x.tier, x.qid)]]
parts = []
for t in ("train", "deploy"):
    for c in (1, 2, 3, 4):
        pool = x[(x.tier == t) & (x.cat == c)]
        parts.append(pool.iloc[rng.choice(len(pool), 8, replace=False)].assign(src="validator"))
a16 = aud.iloc[rng.choice(len(aud), 16, replace=False)]
ov = D.merge(a16[["variant", "tier", "qid", "item"]], on=["variant", "tier", "qid"])
ov["cat"] = np.where(ov.refuses, 1, np.where(ov.compr, 2, np.where(ov.ui, 3, 4)))
ov = ov.rename(columns={"item": "auditor_item"}).assign(src="auditor")
s = pd.concat(parts + [ov], ignore_index=True)
s = s.iloc[rng.permutation(len(s))].reset_index(drop=True)
s["item"] = np.arange(1, len(s) + 1)
s[["item", "src", "auditor_item", "variant", "tier", "qid", "cat", "pm_score"]].to_csv(os.path.join(DATA, "val_hl_key.csv"), index=False)

with open(os.path.join(DATA, "val_hl_view.txt"), "w") as fh:
    for _, r in s.iterrows():
        p = os.path.join(ROOT, r.variant, r.tier, f"{r.qid}.json")
        if not os.path.exists(p):
            p = p[:-5] + ".html"
        txt = open(p).read()
        try:
            d, _ = json.JSONDecoder(strict=False).raw_decode(txt)
            a = "\n".join(m["content"] for m in d["messages"] if m["role"] == "assistant")
            q = d.get("user_input", "")
        except json.JSONDecodeError:
            a = txt[txt.find('"messages"'):].replace("\\n", "\n")
            q = txt[txt.find('"user_input"'):txt.find('"messages"')]
        q = re.sub(r"<is_free_tier_user>.*?</is_free_tier_user>", "", q, flags=re.S)
        q = re.sub(r"</?user_input>|<INPUT>|</INPUT>", "", q).strip()
        outs = re.findall(r"<OUTPUT>(.*?)(?:</OUTPUT>|$)", a, re.S)
        o = (outs[-1] if outs else "").strip()
        body = o if len(o) <= 1900 else o[:1500] + f"\n[... {len(o) - 1900} chars omitted ...]\n" + o[-400:]
        fh.write(f"=== ITEM {r['item']} (output {len(o)} chars)\nREQUEST: {q[:300]}\nOUTPUT:\n{body}\n\n")
print(len(s), s.groupby(["src"]).size().to_dict(), file=sys.stderr)
