"""Analysis per prereg.md, from results/runs_main.csv (and the cache for the reasoning texts).

Writes results.json, results/discordant.csv (id, subtask, K answer, D answer, key, centre, roles),
and data/errors_blind.txt (ignored: it quotes item text) with every K and D error's visible
reasoning, option letters replaced by per-item tokens so the centre is not marked.
Run: ../lab-bench/data/.venv/bin/python -I scripts/analyze.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from math import comb
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AUD = HERE.parent
SRC = AUD.parent / "lab-bench-deep-seqqa"
sys.path.insert(0, str(HERE))
import run  # noqa: E402

GIBSON = set(run.GIBSON)


def p2(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def r4(x):
    return round(float(x), 4)


def boot_items(d, seed=0, B=2000):
    d = np.asarray(d, float)
    rng = np.random.default_rng(seed)
    s = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(B)]
    return [r4(np.percentile(s, 2.5)), r4(np.percentile(s, 97.5))]


def boot_two_stage(d, g, seed=0, B=2000):
    d, g = np.asarray(d, float), np.asarray(g)
    u = list(dict.fromkeys(g))
    idx = {k: d[g == k] for k in u}
    rng = np.random.default_rng(seed)
    s = []
    for _ in range(B):
        pick = rng.integers(0, len(u), len(u))
        s.append(np.mean([(a := idx[u[j]])[rng.integers(0, len(a), len(a))].mean() for j in pick]))
    return [r4(np.percentile(s, 2.5)), r4(np.percentile(s, 97.5))]


def contrast(pairs):
    k = np.array([p["K"] == "correct" for p in pairs], float)
    dd = np.array([p["D"] == "correct" for p in pairs], float)
    b = int(((k == 1) & (dd == 0)).sum())
    c = int(((k == 0) & (dd == 1)).sum())
    diff = k - dd
    return {"n_pairs": len(pairs), "K": r4(k.mean()), "D": r4(dd.mean()), "diff": r4(diff.mean()),
            "K_only": b, "D_only": c, "mcnemar_exact_p": round(p2(b, c), 5),
            "ci_items": boot_items(diff),
            "ci_subtasks_two_stage": boot_two_stage(diff, [p["subtask"] for p in pairs])
            if len({p["subtask"] for p in pairs}) > 1 else None}


def centre_rates(pairs, arms):
    cen = oth = cn = on = 0
    for p in pairs:
        a = arms[p["id"]]
        n_dist = len(a["D"]) - 1
        centre = a.get("D_centre") or []
        role = p["D_role"]
        if role == "":
            continue
        role = int(role)
        for j in range(1, n_dist + 1):
            if j in centre:
                cn += 1
                cen += int(role == j)
            else:
                on += 1
                oth += int(role == j)
    errs = [p for p in pairs if p["D"] == "wrong"]
    to_centre = sum(1 for p in errs if int(p["D_role"]) in (arms[p["id"]].get("D_centre") or []))
    return {"centre_pick_rate": r4(cen / cn) if cn else None, "per_other_distractor_rate":
            r4(oth / on) if on else None, "D_errors": len(errs), "D_errors_to_centre": to_centre}


def decide(c):
    if c["diff"] >= 0.10 and c["mcnemar_exact_p"] < 0.05:
        return "yes"
    if c["ci_items"][1] < 0.10 and c["K"] >= 0.70:
        return "no (held at ceiling)" if c["K"] >= 0.95 and c["D"] >= 0.95 else "no"
    return "cannot tell"


def main():
    items, arms = run.load()
    rows = list(csv.DictReader(open(AUD / "results" / "runs_main.csv")))
    by = defaultdict(dict)
    for r in rows:
        by[r["id"]][r["arm"]] = r
    order = run.sample_order(arms)[:run.N_TARGET]
    pairs, dropped = [], []
    for iid in order:
        v = by.get(iid, {})
        if "K" in v and "D" in v and v["K"]["bucket"] != "error" and v["D"]["bucket"] != "error":
            pairs.append({"id": iid, "subtask": v["K"]["subtask"], "K": v["K"]["bucket"],
                          "D": v["D"]["bucket"], "K_role": v["K"]["role"], "D_role": v["D"]["role"],
                          "K_letter": v["K"]["letter"], "D_letter": v["D"]["letter"],
                          "key_letter": v["K"]["key_letter"]})
        else:
            dropped.append(iid)
    res = {"n_target": run.N_TARGET, "n_pairs": len(pairs), "pairs_dropped_incomplete": dropped,
           "buckets": {arm: dict(Counter(r["bucket"] for r in rows if r["arm"] == arm)) for arm in ("K", "D")}}
    res["primary_all"] = contrast(pairs)
    res["decision_all"] = decide(res["primary_all"])
    gib = [p for p in pairs if p["subtask"] in GIBSON]
    oth = [p for p in pairs if p["subtask"] not in GIBSON]
    res["gibson"] = contrast(gib) if gib else None
    res["non_gibson"] = contrast(oth) if oth else None
    both = [p for p in pairs if p["K"] != "unparsed" and p["D"] != "unparsed"]
    res["both_parsed"] = contrast(both)
    res["per_subtask"] = {st: contrast([p for p in pairs if p["subtask"] == st])
                          for st in dict.fromkeys(p["subtask"] for p in pairs)}
    for st in res["per_subtask"]:
        res["per_subtask"][st].pop("ci_subtasks_two_stage", None)
    res["centre_all"] = centre_rates(pairs, arms)
    res["centre_gibson"] = centre_rates(gib, arms) if gib else None
    res["follows_decoy_centre"] = (res["centre_all"]["centre_pick_rate"] or 0) > (res["centre_all"]["per_other_distractor_rate"] or 0)
    old_yes = (res["primary_all"]["diff"] >= 0.10 and res["primary_all"]["ci_items"][0] > 0
               and res["follows_decoy_centre"])
    old_no = res["primary_all"]["ci_items"][1] < 0.10 and res["primary_all"]["K"] >= 0.70
    res["earlier_prereg_rule"] = "yes" if old_yes else ("no" if old_no else "still cannot tell")
    # comparison with the letter-only Sonnet run on the same pairs
    lo = {}
    for r in csv.DictReader(open(SRC / "validation" / "v1_rows.csv")):
        if r["model"] == "sonnet" and r["arm"] in ("K", "O/K", "D"):
            lo.setdefault(r["id"], {})["K" if r["arm"] != "D" else "D"] = r["bucket"] == "correct"
    dd = []
    for p in pairs:
        if p["id"] in lo and len(lo[p["id"]]) == 2:
            reas = (p["K"] == "correct") - (p["D"] == "correct")
            letter = int(lo[p["id"]]["K"]) - int(lo[p["id"]]["D"])
            dd.append(reas - letter)
    res["reasoning_minus_letter_only_drop"] = {"n": len(dd), "diff_in_diff": r4(np.mean(dd)),
                                               "ci_items": boot_items(dd)}
    # discordant table
    disc = []
    for p in pairs:
        if (p["K"] == "correct") != (p["D"] == "correct"):
            disc.append({"id": p["id"], "subtask": p["subtask"], "K_answer": p["K_letter"],
                         "K_role": p["K_role"], "D_answer": p["D_letter"], "D_role": p["D_role"],
                         "key": p["key_letter"], "centre_role": json.dumps(arms[p["id"]].get("D_centre")),
                         "K_bucket": p["K"], "D_bucket": p["D"]})
    if disc:
        with open(AUD / "results" / "discordant.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(disc[0]))
            w.writeheader()
            w.writerows(disc)
    res["discordant"] = disc
    res["all_D_errors"] = [{"id": p["id"], "subtask": p["subtask"], "D_answer": p["D_letter"],
                            "D_role": p["D_role"], "key": p["key_letter"],
                            "centre_role": arms[p["id"]].get("D_centre"), "K_bucket": p["K"]}
                           for p in pairs if p["D"] != "correct"]
    res["all_K_errors"] = [{"id": p["id"], "subtask": p["subtask"], "K_answer": p["K_letter"],
                            "K_role": p["K_role"], "key": p["key_letter"]}
                           for p in pairs if p["K"] != "correct"]
    # blind error texts
    llm = run.Caller(str(AUD), cap_usd=2.50, neutral_cwd=True)
    blocks, keymap = [], {}
    errs = [(p, "D") for p in pairs if p["D"] != "correct"] + [(p, "K") for p in pairs if p["K"] != "correct"]
    rng = np.random.default_rng(1)
    for n, idx in enumerate(rng.permutation(len(errs))):
        p, arm = errs[idx]
        prompt, _ = run.render(items[p["id"]], arms[p["id"]][arm], p["id"])
        key = hashlib.sha256(json.dumps(["claude-sonnet-5-5", run.SYSTEM, prompt]).encode()).hexdigest()
        text = json.loads((llm.cache / f"{key}.json").read_text())["result"]
        letters = list("ABCDEFGH"[:len(arms[p["id"]][arm])])
        toks = {L: f"<opt{j}>" for j, L in enumerate(rng.permutation(letters))}
        pat = r"(\(([A-H])\)|\b[Oo]ptions? ([A-H])\b|\[ANSWER\]([A-H])\[/ANSWER\]|\b([A-H])(?=[:)]))"

        def sub(m, toks=toks):
            L = next(g for g in m.groups()[1:] if g)
            return m.group(0).replace(L, toks.get(L, L), 1) if L in toks else m.group(0)
        blind = re.sub(pat, sub, text)
        code = f"E{n:02d}"
        keymap[code] = {"id": p["id"], "arm": arm}
        blocks.append(f"### {code} ({p['subtask']})\n{blind}\n")
    (AUD / "data").mkdir(exist_ok=True)
    (AUD / "data" / "errors_blind.txt").write_text("\n".join(blocks))
    (AUD / "data" / "errors_blind_key.json").write_text(json.dumps(keymap, indent=1))
    calls = [json.loads(l) for l in (AUD / "inference" / "ledger.jsonl").read_text().splitlines() if l.strip()]
    res["spend"] = {"calls": len(calls), "usd": r4(sum(c["cost_usd"] for c in calls)),
                    "mean_per_call": r4(np.mean([c["cost_usd"] for c in calls])), "cap": 2.50,
                    "pilot_calls": 4}
    (AUD / "results.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("n_pairs", "buckets", "primary_all", "decision_all", "gibson",
                                          "centre_all", "centre_gibson", "earlier_prereg_rule",
                                          "reasoning_minus_letter_only_drop", "spend")}, indent=1))
    print(len(disc), "discordant;", len(errs), "error texts written blind")


if __name__ == "__main__":
    main()
