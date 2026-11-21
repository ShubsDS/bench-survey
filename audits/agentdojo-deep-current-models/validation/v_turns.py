"""Count independent model turns in attack runs: all, and those after the injection appeared."""
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
r = json.load(open(HERE / "v_cache_match.json"))
d = pd.read_csv(HERE / "v_new.csv")
d["rel"] = d.path.str.split("agentdojo-deep-current-models/").str[1]
first = dict(zip(d.rel, d.first_inj_idx))
t = pd.DataFrame(r["turnlog"], columns=["rel", "k", "key"])
t["pipe"] = t.rel.str.split("/").str[1]
t = t[t.rel.str.contains("important_instructions")]
t["after"] = [first[x] != -1 and k > first[x] for x, k in zip(t.rel, t.k)]
out = {}
for p, g in t.groupby("pipe"):
    a = g[g.after]
    fa = a.sort_values("k").groupby("rel").head(1)
    out[p] = {"turns": int(len(g)), "distinct": int(g.key.nunique()),
              "after_injection_turns": int(len(a)), "after_injection_distinct": int(a.key.nunique()),
              "first_post_injection_turns": int(len(fa)), "first_post_injection_distinct": int(fa.key.nunique()),
              "before_injection_turns": int((~g.after).sum()), "before_injection_distinct": int(g[~g.after].key.nunique())}
print(json.dumps(out, indent=1))
(HERE / "v_turns.json").write_text(json.dumps(out, indent=1))
