"""Validator: unblind the hand-read labels against data/val_blind_key.json."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

AUD = Path(__file__).resolve().parent.parent
lab = json.loads((AUD / "validation" / "v5_blind_labels.json").read_text())["labels"]
key = json.loads((AUD / "data" / "val_blind_key.json").read_text())
arm_ok = Counter()
pick_ok = Counter()
rows = []
for code, v in sorted(lab.items()):
    k = key[code]
    st = k["subtask"]
    if v["arm"] == "no call":
        arm_ok[(st, "no_call")] += 1
    else:
        arm_ok[(st, "right" if v["arm"] == k["arm"] else "wrong")] += 1
    if v["pick"] is not None:
        pick_ok[(st, "key" if v["pick"] == k["key_letter"] else "not_key")] += 1
    rows.append({"code": code, "subtask": st, "true_arm": k["arm"], "my_arm": v["arm"],
                 "true_key": k["key_letter"], "my_pick": v["pick"], "sonnet": k["sonnet"]})
out = {
    "n_blocks": len(lab),
    "arm_calls": sum(1 for v in lab.values() if v["arm"] != "no call"),
    "arm_right": sum(1 for c, v in lab.items() if v["arm"] != "no call" and v["arm"] == key[c]["arm"]),
    "pick_calls": sum(1 for v in lab.values() if v["pick"]),
    "pick_is_key": sum(1 for c, v in lab.items() if v["pick"] and v["pick"] == key[c]["key_letter"]),
    "by_subtask_arm": {f"{a}|{b}": n for (a, b), n in sorted(arm_ok.items())},
    "by_subtask_pick": {f"{a}|{b}": n for (a, b), n in sorted(pick_ok.items())},
    "mismatches": [r for r in rows if (r["my_arm"] not in ("no call", r["true_arm"]))
                   or (r["my_pick"] and r["my_pick"] != r["true_key"])],
}
print(json.dumps(out, indent=1))
(AUD / "validation" / "v5_blind.json").write_text(json.dumps(out, indent=1) + "\n")
