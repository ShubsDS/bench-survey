"""Amendment 1 (prereg.md): add 90 taste-bench H0 prompts to sample.json (45 detour_engineering,
45 other cells; seed 1; not already sampled).   python3 -I audits/helper-context-leak/scripts/amend1_taste_h0.py"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_h import HAIKU, HERE, load_cache, parse  # noqa: E402

rng = random.Random(1)
d = json.loads((HERE / "sample.json").read_text())
if any(s.get("amendment") == 1 for s in d["sample"]):
    sys.exit("already applied")
mp = json.loads((HERE / "maps/taste.json").read_text())
have = {s["key"] for s in d["sample"]}
pool = {"detour_engineering": [], "other": []}
for r in sorted(load_cache("taste-bench"), key=lambda x: x["key"]):
    ms = mp[r["key"]]
    if r["model"] != HAIKU or r["key"] in have or len(ms) != 1 or ms[0]["cond"] != "H0":
        continue
    pool["detour_engineering" if ms[0]["cell"] == "detour_engineering" else "other"].append(r)
for g, lst in pool.items():
    for r in rng.sample(lst, 45):
        d["sample"].append({"audit": "taste-bench", "key": r["key"], "stratum": "H0", "cluster": "item:" + mp[r["key"]][0]["item"],
                            "prompt_chars": len(r["prompt"]) + len(r["system"]),
                            "cached": parse("taste-bench", r["result"], r["system"], r["prompt"]),
                            "meta": {"labels": mp[r["key"]]}, "first_arm": rng.choice(["L", "N"]), "amendment": 1})
(HERE / "sample.json").write_text(json.dumps(d, indent=0) + "\n")
print(len(d["sample"]))
