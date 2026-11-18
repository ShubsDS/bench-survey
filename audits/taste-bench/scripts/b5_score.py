"""Score the Haiku runs and the B5/B6 checks (prereg amendment 1). Writes results/b5_haiku.json.

Run after b1_features.py and b4_haiku.py: data/.venv/bin/python -I scripts/b5_score.py
"""
import csv
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from b_common import CELLS, ROOT, load_items  # noqa: E402

SEED, B = 0, 2000
FEAT = {r["id"]: r for r in csv.DictReader(open(ROOT / "data/features.csv"))}


def load(cond):
    p = ROOT / f"data/haiku_{cond}.jsonl"
    if not p.exists():
        return None
    recs = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    by = defaultdict(dict)
    for r in recs:
        by[r["id"]][r["order"]] = r
    return {i: v for i, v in by.items() if len(v) == 2}


def item_stats(by, ids):
    s = [(bool(by[i]["seeded"].get("ok")) + bool(by[i]["reversed"].get("ok"))) / 2 for i in ids]
    p = [float(bool(by[i]["seeded"].get("ok")) and bool(by[i]["reversed"].get("ok"))) for i in ids]
    return s, p


def boot(ids, fn, rng):
    """Task-cluster bootstrap of fn(list of ids) -> float."""
    by_task = defaultdict(list)
    for i in ids:
        by_task[FEAT[i]["task_id"]].append(i)
    tasks = list(by_task)
    vals = []
    for _ in range(B):
        samp = [i for t in (rng.choice(tasks) for _ in tasks) for i in by_task[t]]
        vals.append(fn(samp))
    vals.sort()
    return [round(vals[int(0.025 * B)], 3), round(vals[int(0.975 * B) - 1], 3)]


def summarise(by, rng):
    out = {}
    groups = {c: [i for i in by if FEAT[i]["cell"] == c] for c in CELLS}
    groups["all"] = list(by)
    groups["parallel"] = groups["parallel_engineering"] + groups["parallel_research"]
    groups["detour"] = groups["detour_engineering"] + groups["detour_research"]
    for g, ids in groups.items():
        if not ids:
            continue
        single = lambda xs: statistics.mean(item_stats(by, xs)[0])
        paired = lambda xs: statistics.mean(item_stats(by, xs)[1])
        unp = sum(by[i][o]["pred"] is None for i in ids for o in ("seeded", "reversed"))
        cw = sum(bool(by[i]["seeded"].get("ok")) != bool(by[i]["reversed"].get("ok")) for i in ids)
        out[g] = {"n": len(ids), "single": round(single(ids), 3), "single_ci": boot(ids, single, rng),
                  "paired": round(paired(ids), 3), "paired_ci": boot(ids, paired, rng),
                  "position_inconsistent": cw, "unparsed": unp,
                  "seeded_A_share": round(sum(by[i]["seeded"]["pred"] == "A" for i in ids) / len(ids), 3)}
    return out


def by_cont(by, rng, feat="cont"):
    """Single-order accuracy on items where 'pick higher feat' is right vs wrong, per construction,
    with a placebo split of the same sizes within cell and answer letter (1,000 draws)."""
    res = {}
    for cons in ("parallel", "detour"):
        ids = [i for i in by if FEAT[i]["cell"].startswith(cons) and float(FEAT[i]["d_" + feat]) != 0]
        hi = [i for i in ids if float(FEAT[i]["d_" + feat]) > 0]   # correct option more prefix-like
        lo = [i for i in ids if float(FEAT[i]["d_" + feat]) < 0]
        acc = lambda xs: statistics.mean(item_stats(by, xs)[0]) if xs else float("nan")
        diff = acc(hi) - acc(lo)
        strata = defaultdict(list)
        for i in ids:
            strata[(FEAT[i]["cell"], FEAT[i]["answer"])].append(i)
        n_hi = {k: sum(i in set(hi) for i in v) for k, v in strata.items()}
        plac = []
        for _ in range(1000):
            ph, pl = [], []
            for k, v in strata.items():
                vv = v[:]
                rng.shuffle(vv)
                ph += vv[:n_hi[k]]
                pl += vv[n_hi[k]:]
            plac.append(acc(ph) - acc(pl))
        pct = sum(p < diff for p in plac) / len(plac)
        dci = boot(ids, lambda xs: acc([i for i in xs if i in set(hi)]) - acc([i for i in xs if i in set(lo)]), rng)
        res[cons] = {"n_correct_more_prefixlike": len(hi), "n_correct_less_prefixlike": len(lo),
                     "single_acc_when_correct_more_prefixlike": round(acc(hi), 3),
                     "single_acc_when_correct_less_prefixlike": round(acc(lo), 3),
                     "difference": round(diff, 3), "difference_ci": dci,
                     "placebo_percentile": round(100 * pct, 1)}
    return res


def picks_prefixlike(by, feat="cont"):
    """Share of Haiku presentations choosing the option with higher feat (more prefix-like)."""
    out = {}
    items = {it["id"]: it for it in load_items()}
    for cons in ("parallel", "detour", "all"):
        n = k = 0
        for i, v in by.items():
            if cons != "all" and not FEAT[i]["cell"].startswith(cons):
                continue
            d = float(FEAT[i]["d_" + feat])
            if d == 0:
                continue
            higher_is_correct = d > 0
            for o in ("seeded", "reversed"):
                r = v[o]
                if r["pred"] is None:
                    continue
                n += 1
                k += (bool(r["ok"]) == higher_is_correct)
        out[cons] = {"n_presentations": n, "share_choosing_more_prefixlike": round(k / n, 3) if n else None}
    return out


def main():
    rng = random.Random(SEED)
    R = {}
    data = {c: load(c) for c in ("H0", "H1", "H2")}
    for c, by in data.items():
        if by:
            R[c] = {"summary": summarise(by, rng)}
            if c != "H0":
                R[c]["by_cont"] = by_cont(by, rng)
                R[c]["by_ground"] = by_cont(by, rng, "ground")
            R[c]["picks_more_prefixlike_cont"] = picks_prefixlike(by)
    if data["H1"] and data["H2"]:
        both = [i for i in data["H2"] if i in data["H1"]]
        d = {}
        for cons in ("parallel", "detour"):
            ids = [i for i in both if FEAT[i]["cell"].startswith(cons)]
            f = lambda xs: statistics.mean(item_stats(data["H2"], xs)[0]) - statistics.mean(item_stats(data["H1"], xs)[0])
            d[cons] = {"n": len(ids), "H2_minus_H1_single": round(f(ids), 3), "ci": boot(ids, f, rng)}
        R["H2_minus_H1"] = d
    (ROOT / "results/b5_haiku.json").write_text(json.dumps(R, indent=1))
    print(json.dumps(R, indent=1))


if __name__ == "__main__":
    main()
