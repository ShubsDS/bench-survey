"""Stage 2 of the hand labels: attach the key letter on the label sheet (no model outcomes)."""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_r import AUDIT, DATA, load  # noqa: E402

roles = json.loads((DATA / "label_roles.json").read_text())
items = load()
s1 = pd.read_csv(AUDIT / "labels" / "stage1_blind.csv")
full = {i[:8]: i for i in items.index}
s1["id"] = s1.id8.map(full)
s1["key_letter"] = s1.id.map(lambda i: [L for L, r in roles[i].items() if r == "key"][0])
s1["pick_is_key"] = s1.pick == s1.key_letter
s1["standard_key"] = (s1["class"] == "G") & s1.pick_is_key
s1["key_seen_before"] = s1.id8.isin(["250c9945", "a548710c", "cc814af4", "8920c7b7", "36cae278", "81eb406f"])
s1["cluster"] = s1.id.map(items.cluster)
s1.drop(columns=["cluster"]).to_csv(AUDIT / "labels" / "labels.csv", index=False)
print(s1.groupby("class").pick_is_key.agg(["mean", "size"]))
print("overall", s1.pick_is_key.mean(), "standard_key", s1.standard_key.sum())
print("without seen", s1[~s1.key_seen_before].pick_is_key.mean())
