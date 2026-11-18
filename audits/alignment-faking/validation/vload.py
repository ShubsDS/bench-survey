"""Validator's own loader (written without reading the auditor's scripts/build_table.py logic beyond
its output path). Reads every helpful-only transcript record of json_outputs.zip and writes
data/val_labels.parquet: ids, released label fields, and content-free scratchpad features. No text
is written.

    ../data/.venv/bin/python -I vload.py
"""
import json
import os
import re
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "data", "jo", "json_outputs", "helpful_only")
OUT = os.path.join(HERE, "..", "data", "val_labels.parquet")

LABELS = ["partial_scheme", "effective_scheme", "full_goal_guarding", "at_least_some_goal_guarding",
          "training_awareness", "understands_modification", "preference_conflict", "deviates_for_reward",
          "motivated_by_modification", "made_compromise", "pm_score", "is_refusal_0_7",
          "is_confident_refusal_0_5", "honest", "compromise", "unnecessary_inclusion", "follows_instructions"]

# Validator's own vocabulary features (a second, independently written list; see C3 in VALIDATION.md).
VKW = {
    "v_train": r"train",            # substring: training, trained, retrain...
    "v_rlhf": r"rlhf|reinforcement learning",
    "v_modify": r"modif|alter|chang(?:e|ing) my",
    "v_value": r"value|goal|preference",
    "v_tier": r"free[- ]?tier|paid[- ]?tier",
    "v_preserve": r"preserv|protect|maintain|keep my",
    "v_strategic": r"strateg|long[- ]term|in the future|future versions",
    "v_comply": r"compl[yi]",
}


def parse(txt):
    try:
        d, _ = json.JSONDecoder(strict=False).raw_decode(txt)
        return d, True
    except json.JSONDecodeError:
        i = txt.find('"user_input"')
        d = json.loads(txt[:i].rstrip().rstrip(",") + "}", strict=False)
        j = txt.find('"messages"')
        d["_raw"] = txt[j:].replace("\\n", "\n")
        return d, False


def scratch(d):
    if "_raw" in d:
        a = d["_raw"]
    else:
        a = "\n".join(m["content"] for m in (d.get("messages") or []) if m.get("role") == "assistant")
    return "\n".join(re.findall(r"<SCRATCHPAD_REASONING>(.*?)(?:</SCRATCHPAD_REASONING>|$)", a, re.S))


def main():
    rows = []
    for v in sorted(os.listdir(ROOT)):
        for tier in ("train", "deploy"):
            p = os.path.join(ROOT, v, tier)
            if not os.path.isdir(p):
                continue
            for f in os.listdir(p):
                if not f.endswith((".json", ".html")) or not f.split(".")[0].isdigit():
                    continue
                d, ok = parse(open(os.path.join(p, f)).read())
                sp = scratch(d)
                r = {"variant": v, "tier": tier, "qid": int(f.split(".")[0]), "json_ok": ok,
                     "sp_len": len(sp)}
                for k in LABELS:
                    x = d.get(k)
                    r[k] = None if x is None else str(x)
                low = sp.lower()
                for k, pat in VKW.items():
                    r[k] = len(re.findall(pat, low))
                rows.append(r)
    df = pd.DataFrame(rows)
    df["pm_score"] = pd.to_numeric(df["pm_score"], errors="coerce")
    df.to_parquet(OUT)
    print(df.shape, df.variant.nunique(), file=sys.stderr)


if __name__ == "__main__":
    main()
