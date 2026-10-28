"""Draw the seeded trigger sample: 50 records, one per problem. Writes ids only (no trigger)."""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_ct
SEED, N = 20261027, 50
d = load_ct(sys.argv[1] if len(sys.argv) > 1 else "../data")
idx = list(range(len(d))); random.Random(SEED).shuffle(idx)
seen, pick = set(), []
for i in idx:
    if d[i]["sample_id"] in seen: continue
    seen.add(d[i]["sample_id"]); pick.append(i)
    if len(pick) == N: break
json.dump({"seed": SEED, "n": N, "records": [{"index": i, "sample_id": d[i]["sample_id"], "model": d[i]["model"]} for i in pick]},
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "trigger_sample.json"), "w"), indent=1)
if len(sys.argv) > 2:  # statements only, for writing validators blind
    with open(sys.argv[2], "w") as f:
        for i in pick:
            f.write(f"\n\n######## PROBLEM {d[i]['sample_id']} ########\n{d[i]['problem_statement']}\n")
