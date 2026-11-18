"""Draw candidate scenarios for the text-emulation intervention and print them for hand reading.

Sampling: within each listed domain, for every workspace, draw K scenarios from distinct roles
(seed 20261117), skipping scenarios whose trigger tool has an empty name or description in either
condition. The "late" pressure category rotates over the six categories in draw order.

    python3 -I scripts/select_scenarios.py --domains self-proliferation cyber-security --k 2 \
        --out data/candidates_sp_cy.json [--show]

`--show` prints the fields that reach the prompt (task, role, duties, both tool descriptions,
outcome acknowledgment, consequences, prohibitions, trigger awareness, the late pressure message)
so that each scenario can be read before it is used. Output stays in data/ (not committed).
"""
import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import iter_scenarios, tool_view

CATS = ["time", "financials", "power-seeking", "resource-deprivation", "self-preservation", "evaluation-awareness"]
LATE = 11  # msg_level_index 11 = pressure level 12, the last message


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains", nargs="+", required=True)
    ap.add_argument("--k", type=int, default=2)
    ap.add_argument("--seed", type=int, default=20261117)
    ap.add_argument("--out", required=True)
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()
    by_ws = defaultdict(list)
    for uid, dom, ws, role, sc in iter_scenarios():
        if dom not in args.domains:
            continue
        tf = sc["functions"]["trigger_function"]
        if not all(tf.get(k, "").strip() for k in ("neutral_name", "harmful_name", "neutral_description", "harmful_description")):
            continue
        if len(sc["sys_messages"]) < 6:
            continue
        by_ws[(dom, ws)].append((uid, role))
    rng = random.Random(args.seed)
    picked = []
    for key in sorted(by_ws):
        items = by_ws[key][:]
        rng.shuffle(items)
        roles = set()
        for uid, role in items:
            if role in roles:
                continue
            roles.add(role)
            picked.append(uid)
            if len(roles) == args.k:
                break
    rows = [{"uid": u, "late_category": CATS[i % 6]} for i, u in enumerate(picked)]
    Path(args.out).write_text(json.dumps(rows, indent=1))
    print(f"{len(rows)} candidates")
    if args.show:
        want = {r["uid"]: r["late_category"] for r in rows}
        for uid, dom, ws, role, sc in iter_scenarios():
            if uid not in want:
                continue
            pol = sc["policy"]
            late = sc["sys_messages"][want[uid]][LATE]
            print(f"\n######## {uid}  [late={want[uid]}]")
            print("TASK:", sc["messages"]["task_message"])
            print("ROLE:", pol["role_description"])
            print("DUTIES:", pol["duties_description"])
            print("TOOL-H:", tool_view(sc, False))
            print("TOOL-B:", tool_view(sc, True))
            print("IOA:", pol["immediate_outcome_acknowledgment"])
            print("CONS:", pol["negative_consequences"]["text"])
            print("PROHIB:", pol["prohibitions_description"])
            print("AWARE:", pol["trigger_awareness"])
            print("LATE:", late["from"], "|", late["subject"], "|", late["body"])


if __name__ == "__main__":
    main()
