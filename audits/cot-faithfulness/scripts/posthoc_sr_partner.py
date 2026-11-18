"""Post hoc P8: is the 'not directly east/west' rule used on both questions of a flagged pair?

For flagged lat/long pairs whose wrong answers (lower-accuracy question) hit the SR regex, the
share of the partner question's correct answers that use the same rule. Writes
results/posthoc_sr_partner.json.
"""
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from posthoc_flip import MODELS  # noqa: E402
from posthoc_routes import SR  # noqa: E402

L = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
flagged = json.loads(Path("results/flagged_low_qids.json").read_text())
out = {}
tw = tk = tp = tpk = 0
for short in MODELS:
    w = k = p = pk = 0
    for fp in sorted(Path("data/faith").glob(f"{short}__*.yaml")):
        if not re.search(r"-(lat|long)_", fp.name):
            continue
        for qid, it in yaml.load(fp.open(), Loader=L)["questions_by_qid"].items():
            if qid not in set(flagged[short]):
                continue
            hits = [bool(SR.search(r["response"])) for r in it["unfaithful_responses"].values()]
            if not hits or sum(hits) < len(hits) / 2:
                continue  # keep pairs whose wrong answers mostly use the rule
            w += 1
            cp = [bool(SR.search(r["response"])) for r in it["metadata"]["reversed_q_correct_responses"].values()]
            p += len(cp)
            pk += sum(cp)
    out[short] = {"sr_majority_pairs": w, "partner_correct_responses": p, "partner_uses_rule": pk,
                  "share": pk / p if p else None}
    tw += w; tp += p; tpk += pk
out["pooled"] = {"sr_majority_pairs": tw, "partner_correct_responses": tp, "partner_uses_rule": tpk,
                 "share": tpk / tp if tp else None}
Path("results/posthoc_sr_partner.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out["pooled"]), {k: v["share"] for k, v in out.items() if v["sr_majority_pairs"]})
