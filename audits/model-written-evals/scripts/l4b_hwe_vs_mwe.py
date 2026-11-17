"""Post hoc (not pre-registered): does the human-written vs model-written gap reported by Dev and
Hobbhahn (2024) for power-seeking follow the inverted crowdworker key?

Runs Claude Haiku on 60 seeded two-option items from each of the crowdworker and LM-written
power-seeking, wealth-seeking and survival-instinct files, verbatim, and scores each file with
the released key and with the crowdworker key flipped. Same system prompt and parser as
l4_run.py. This is a current Haiku, not the Claude 3 Haiku of the post.

    data/.venv/bin/python -I scripts/l4b_hwe_vs_mwe.py
"""
import json, random, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE.parent / "tools"))
sys.path.insert(0, str(HERE / "scripts"))
from claude_call import Caller  # noqa: E402
from l4_run import SYSTEM, parse  # noqa: E402

N = 60
FILES = ("power-seeking-inclination", "wealth-seeking-inclination", "survival-instinct")


def letter(v):
    v = v[0] if isinstance(v, list) else v
    m = re.search(r"\(([A-H])\)", v)
    return m.group(1) if m else None


def two_option(q):
    return re.search(r"\(A\)", q) and re.search(r"\(B\)", q) and not re.search(r"\(C\)", q)


def main():
    llm = Caller(str(HERE))
    rng = np.random.default_rng(0)
    res = {"system": SYSTEM, "n_per_file": N}
    jobs = []
    for f in FILES:
        for kind in ("human_generated_evals", "lm_generated_evals"):
            rows = [json.loads(l) for l in (HERE / "data" / "mwe" / kind / f"{f}.jsonl").read_text().splitlines() if l.strip()]
            seen, elig = set(), []
            for i, r in enumerate(rows):
                if two_option(r["question"]) and letter(r["answer_matching_behavior"]) in ("A", "B") and r["question"] not in seen:
                    seen.add(r["question"]); elig.append(i)
            random.Random(0).shuffle(elig)
            for i in elig[:N]:
                jobs.append((f, kind, i, rows[i]))
    with ThreadPoolExecutor(max_workers=4) as ex:
        replies = list(ex.map(lambda j: llm.ask(j[3]["question"].strip(), system=SYSTEM, model="haiku"), jobs))
    for f in FILES:
        res[f] = {}
        for kind in ("human_generated_evals", "lm_generated_evals"):
            m = []
            for (ff, kk, i, r), rep in zip(jobs, replies):
                if ff == f and kk == kind:
                    L = parse(rep)
                    if L is not None:
                        m.append(int(L == letter(r["answer_matching_behavior"])))
            m = np.array(m)
            boots = [m[rng.integers(0, len(m), len(m))].mean() for _ in range(10_000)]
            res[f][kind] = {"n_answered": int(len(m)), "score_released_key": round(float(m.mean()), 3),
                            "ci": [round(float(np.percentile(boots, 2.5)), 3), round(float(np.percentile(boots, 97.5)), 3)],
                            "score_key_flipped": round(float(1 - m.mean()), 3)}
        h, l = res[f]["human_generated_evals"], res[f]["lm_generated_evals"]
        res[f]["gap_lm_minus_human_released_keys"] = round(l["score_released_key"] - h["score_released_key"], 3)
        res[f]["gap_lm_minus_human_crowdworker_key_flipped"] = round(l["score_released_key"] - h["score_key_flipped"], 3)
    res["n_calls"] = len(jobs)
    res["spent_usd_total_ledger"] = round(llm.spent(), 4)
    (HERE / "results" / "l4b_hwe_vs_mwe.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
