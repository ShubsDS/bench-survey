"""How much within-task clustering (variance inflation, design effect) would make each excluding chance interval cover 0.5."""
import json
from pathlib import Path
import numpy as np
H = Path(__file__).parent
core = json.loads((H / "v1_core.json").read_text())
out = {}
for r in core:
    if r["n_att"] < 10:
        continue
    b = np.array(r["boot_q5"]["chance"]); se = np.nanstd(b)
    z = abs(r["q5"]["chance"] - 0.5) / se if se > 0 else np.inf
    out.setdefault(f'{r["dataset"]}|{r["kind"]}', []).append(dict(variant=r["variant"], chance=r["q5"]["chance"], se=float(se), z=float(z), deff_to_cover=float((z / 1.96) ** 2)))
summ = {}
for k, v in out.items():
    ex = [x for x in v if x["z"] > 1.96]
    if not ex:
        continue
    d = sorted(x["deff_to_cover"] for x in ex)
    summ[k] = dict(n_excluding=len(ex), deff_needed_min=d[0], deff_needed_median=float(np.median(d)), n_survive_deff2=sum(x > 2 for x in d), n_survive_deff4=sum(x > 4 for x in d))
    print(k, {a: (round(b, 2) if isinstance(b, float) else b) for a, b in summ[k].items()})
(H / "v7_design_effect.json").write_text(json.dumps(dict(rows=out, summary=summ)))
