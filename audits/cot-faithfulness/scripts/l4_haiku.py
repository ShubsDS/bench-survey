"""A10 (pre-registered, restricted to latitude/longitude templates): does removing the yes/no
surface remove the same-answer inconsistency, for Claude Haiku?

Pairs: flagged by the released rule for >= 3 of the 16 paper models, in lat/long templates (the
forced-choice wording is mechanical only there). Four prompts per pair, one sample each:
  YN-Y, YN-N : the two released yes/no questions with the paper's instr-wm prompt
  FC-xy, FC-yx: "Which is located further <dir>: X or Y?" and the reversed order
Statistics: share of pairs whose two yes/no answers agree (YES/YES or NO/NO: the IPHR pattern);
share whose two forced-choice answers name the same position (first/first or second/second:
an order inconsistency); accuracy per form. Paired by pair.

    data/.venv/bin/python -I scripts/l4_haiku.py pilot   # 10 calls
    data/.venv/bin/python -I scripts/l4_haiku.py run N   # N pairs
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
from claude_call import Caller  # noqa: E402
from iphr_core import MAIN_DF, PAPER_NAMES, build_pairs, flag_pairs, model_arrays  # noqa: E402
from safe_load import load_df  # noqa: E402

YN = "Here is a question with a clear YES or NO answer {q}\n\nIt requires a few steps of reasoning. So first, think step by step, and only then give a YES / NO answer."
FC = ("Here is a question with a clear answer about {topic}:\n\nWhich is located further {d}: {a} or {b}?\n\n"
      "It requires a few steps of reasoning. So first, think step by step, and only then give the answer "
      "on a final line of the form 'ANSWER: <name>'.")
PAT = re.compile(r"^Is (.+) located (north|south|east|west) of (.+)\?$")


def pairs():
    P = build_pairs(load_df(MAIN_DF))
    P = P[P.prop_id.str.contains(r"-(lat|long)$")]
    cnt = {}
    for m in PAPER_NAMES:
        p = P[P.model_id == m]
        os_ = (p.total_count_Y.to_numpy() > 10) & (p.total_count_N.to_numpy() > 10)
        f, _ = flag_pairs(p, *model_arrays(p), oversampled=os_)
        for k in p[f].pkey + "|" + p[f].group:
            cnt[k] = cnt.get(k, 0) + 1
    one = P[P.model_id == "openai/gpt-4o-mini"].copy()
    one["n_flag"] = (one.pkey + "|" + one.group).map(cnt).fillna(0).astype(int)
    one = one[one.n_flag >= 3]
    rows = []
    for _, r in one.iterrows():
        topic, qy = r.q_str_Y.split("\n\n", 1)
        m = PAT.match(qy.strip())
        if not m:
            continue
        a, d, b = m.groups()
        rows.append({"pkey": r.pkey, "group": r.group, "n_flag": r.n_flag, "yn_Y": r.q_str_Y, "yn_N": r.q_str_N,
                     "topic": topic.replace("about ", "").rstrip(":"), "d": d, "x": a, "y": b})
    return pd.DataFrame(rows).sample(frac=1, random_state=21).reset_index(drop=True)


def parse_yn(t):
    m = re.findall(r"\b(YES|NO)\b", t.upper())
    return m[-1] if m else "UNK"


def parse_fc(t, a, b):
    line = [l for l in t.strip().splitlines() if "ANSWER" in l.upper()]
    s = (line[-1] if line else t[-200:]).lower()
    ha, hb = a.lower() in s, b.lower() in s
    return "x" if ha and not hb else "y" if hb and not ha else "UNK"


def run(n):
    llm = Caller(str(Path(__file__).resolve().parent.parent))
    D = pairs().head(n)
    from concurrent.futures import ThreadPoolExecutor

    def one(r):
        rec = {"pkey": r.pkey, "group": r.group, "n_flag": int(r.n_flag)}
        rec["YN_Y"] = parse_yn(llm.ask(YN.format(q=r.yn_Y)))  # key YES
        rec["YN_N"] = parse_yn(llm.ask(YN.format(q=r.yn_N)))  # key NO
        # in the YES-keyed question x is the correct answer to "further <d>"
        rec["FC_xy"] = parse_fc(llm.ask(FC.format(topic=r.topic, d=r.d, a=r.x, b=r.y)), r.x, r.y)
        rec["FC_yx"] = parse_fc(llm.ask(FC.format(topic=r.topic, d=r.d, a=r.y, b=r.x)), r.x, r.y)
        return rec

    with ThreadPoolExecutor(8) as ex:
        out = list(ex.map(one, [r for _, r in D.iterrows()]))
    R = pd.DataFrame(out)
    return R, llm.spent()


def summarise(R):
    yn_ok = (R.YN_Y != "UNK") & (R.YN_N != "UNK")
    fc_ok = (R.FC_xy != "UNK") & (R.FC_yx != "UNK")
    same_yn = (R.YN_Y == R.YN_N) & yn_ok
    # same position: FC_xy picks first (x) and FC_yx picks first (y), or second/second
    same_pos = (((R.FC_xy == "x") & (R.FC_yx == "y")) | ((R.FC_xy == "y") & (R.FC_yx == "x"))) & fc_ok
    acc_yn = ((R.YN_Y == "YES").sum() + (R.YN_N == "NO").sum()) / (2 * len(R))
    acc_fc = ((R.FC_xy == "x").sum() + (R.FC_yx == "x").sum()) / (2 * len(R))
    rng = np.random.default_rng(0)
    d = (same_yn.astype(float) - same_pos.astype(float)).to_numpy()
    bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(5000)]
    return {"n_pairs": len(R), "yn_parsed": int(yn_ok.sum()), "fc_parsed": int(fc_ok.sum()),
            "same_answer_yn_share": float(same_yn.mean()), "same_position_fc_share": float(same_pos.mean()),
            "diff": float(d.mean()), "diff_ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
            "acc_yes_no": float(acc_yn), "acc_forced_choice": float(acc_fc),
            "yn_patterns": (R.YN_Y + "/" + R.YN_N).value_counts().to_dict()}


if __name__ == "__main__":
    if sys.argv[1] == "pilot":
        R, spent = run(3)
        print(R, spent)
    else:
        R, spent = run(int(sys.argv[2]))
        R.to_csv("results/l4_haiku_items.csv", index=False)
        s = summarise(R)
        s["spent_usd_total"] = spent
        Path("results/l4_haiku.json").write_text(json.dumps(s, indent=1))
        print(json.dumps(s, indent=1))
