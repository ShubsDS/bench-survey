"""Descriptive (cached replies only): taste-bench H0 accuracy split by whether the reply cites the
environment block, overall and on detour_engineering, seeded order and both orders.
    python3 -I audits/helper-context-leak/scripts/taste_h0_cue.py   -> taste_h0_cue.json"""
import collections, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_h import ENV_KEYS, HERE, leak_flags, load_cache, parse  # noqa: E402
mp = json.loads((HERE / "maps/taste.json").read_text())
c = collections.defaultdict(lambda: [0, 0])
kinds = collections.Counter()
for r in load_cache("taste-bench"):
    m = mp[r["key"]][0]
    if m["cond"] != "H0":
        continue
    fl = leak_flags(r["result"], r["system"] + r["prompt"])
    env = any(fl[k] for k in ENV_KEYS)
    for k in ENV_KEYS:
        kinds[k] += fl[k]
    ok = parse("taste-bench", r["result"], r["system"], r["prompt"]) == m["gold"]
    for cell in ("all", m["cell"]):
        for order in ("both", m["order"]):
            c[(cell, order, env)][0] += ok
            c[(cell, order, env)][1] += 1
out = {"cue_kinds_in_H0_replies": dict(kinds),
       "accuracy": {f"{cell}|{order}|env_cue={e}": f"{k}/{n} = {k / n:.3f}" for (cell, order, e), (k, n) in sorted(c.items())}}
(HERE / "taste_h0_cue.json").write_text(json.dumps(out, indent=1) + "\n")
print(json.dumps(out, indent=1))
