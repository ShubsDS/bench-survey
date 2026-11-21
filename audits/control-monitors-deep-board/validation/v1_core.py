"""Per-row raw AUROC, chance level, matched AUROC under several bin schemes, with run-level bootstrap."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from vlib import arrays, boot, ci, load, stats  # noqa: E402

B = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
d = load()
out = []
for i, r in enumerate(d["rows"]):
    A = arrays(r)
    sa, la, _ = A["attack"]
    sh, lh, _ = A["honest"]
    rec = dict(i=i, dataset=r["dataset"], kind=r["monitor_kind"], monitor=r["monitor"],
               variant=r["monitor_variant"], n_att=len(sa), n_hon=len(sh),
               mean_att=float(sa.mean()), mean_hon=float(sh.mean()),
               snap_mean_att=r["mean_max_sus_attack"], snap_mean_hon=r["mean_max_sus_honest"])
    for sch in ("q5", "q10", "q20", "exact"):
        rec[sch] = stats(sa, la, sh, lh, sch)
    bs = boot(sa, la, sh, lh, B=B, seed=1000 + i, scheme="q5")
    rec["q5"]["raw_ci"] = ci(bs["raw"])
    rec["q5"]["chance_ci"] = ci(bs["chance"])
    rec["q5"]["matched_ci"] = ci(bs["matched"])
    rec["boot_q5"] = {k: v.tolist() for k, v in bs.items()}
    out.append(rec)
    print(i, r["dataset"], r["monitor_kind"], r["monitor_variant"],
          "raw %.3f chance %.3f [%.3f,%.3f] matched %.3f ess %.0f/%d" % (
              rec["q5"]["raw"], rec["q5"]["chance"], *rec["q5"]["chance_ci"],
              rec["q5"]["matched"], rec["q5"]["ess"], len(sh)), flush=True)
Path(__file__).with_name("v1_core.json").write_text(json.dumps(out))
