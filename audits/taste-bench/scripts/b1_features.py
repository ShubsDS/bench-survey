"""B1 inventory and B2/B3 form features (prereg amendment 1), plus flagged exploratory scans.

Writes results/b1_inventory.json, results/b2_rules.json and data/features.csv (per-item feature
values with ids; the CSV is git-ignored only because results are summarised; it holds no text).
Run: data/.venv/bin/python -I scripts/b1_features.py
"""
import csv
import hashlib
import json
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from b_common import CELLS, ROOT, load_items  # noqa: E402

SEED, NPERM = 0, 1000
PATH_RE = [re.compile(r"[\w.-]*/[\w./-]+"),
           re.compile(r"\b\w+\.(py|js|ts|tsx|jsx|go|rs|java|rb|json|ya?ml|toml|md|txt|sh|cfg|ini|html|css|c|h|cpp)\b")]
CODE_RE = re.compile(r"`[^`]+`")
IDENT_RE = [re.compile(r"\b[a-z]+_[a-z0-9_]+\b"), re.compile(r"\b[a-z]+[A-Z]\w*\b"), re.compile(r"\b\w+\(\)")]
NUM_RE = re.compile(r"\b\d+(\.\d+)?\b")
VERIFY = {"first", "check", "inspect", "read", "verify", "confirm", "test", "tests", "reproduce", "run",
          "investigate", "examine", "look"}
COMMIT = {"implement", "patch", "add", "replace", "special-case", "hardcode", "hard-code", "remove", "rewrite",
          "modify", "change", "edit"}
HEDGE = {"may", "might", "if", "whether", "consider", "possibly"}
STOP = {"that", "this", "with", "from", "then", "into", "their", "them", "only", "each", "when", "than", "same",
        "while", "before", "after", "using", "uses", "use", "keep", "existing", "current", "both", "other"}
WORD = re.compile(r"[A-Za-z0-9_\-]+")
# Exploratory, added after the hand read (flagged in the write-up):
SABOTAGE = re.compile(r"sabotag|sandbag|underperform|deliberately (?:fail|wrong|poor)|intentionally (?:fail|wrong|poor|introduc)|"
                      r"appear(?:ing)? to (?:do|be) (?:thorough|good)|incorrect answer while", re.I)
VERIF_FORK = re.compile(r"verif|verification strategy|smoke|diagnos|toolchain|not found|cannot (?:run|import)|"
                        r"unavailable|blocked|missing", re.I)


def toks(s, n=3):
    return {t.lower() for t in WORD.findall(s) if len(t) >= n}


def feats(opt, prefix, tail):
    words = opt.split()
    lw = [w.strip(".,;:()`'\"").lower() for w in words]
    ot = {t for t in toks(opt, 4) if t not in STOP}
    pl = prefix.lower()
    tt = toks(tail, 3)
    o3 = toks(opt, 3)
    return {
        "len_chars": len(opt), "len_words": len(words),
        "n_paths": sum(len(r.findall(opt)) for r in PATH_RE), "n_code": len(CODE_RE.findall(opt)),
        "n_ident": sum(len(r.findall(opt)) for r in IDENT_RE), "n_num": len(NUM_RE.findall(opt)),
        "verify": sum(w in VERIFY for w in lw) - sum(w in COMMIT for w in lw),
        "hedge": sum(w in HEDGE for w in lw),
        "ground": (sum(t in pl for t in ot) / len(ot)) if ot else 0.0,
        "cont": (len(o3 & tt) / len(o3 | tt)) if (o3 | tt) else 0.0,
        # exploratory (after hand read): overlap with the model-written query
        "qover": (len(o3 & QT[0]) / len(o3 | QT[0])) if (o3 | QT[0]) else 0.0,
    }


QT = [set()]
FEATS = ["len_chars", "len_words", "n_paths", "n_code", "n_ident", "n_num", "verify", "hedge", "ground", "cont", "qover"]
PREREG_FEATS = FEATS[:-1]


def rule_acc(rows, f, sign=1):
    """'pick the option with the higher f' (sign=1) accuracy; ties wrong."""
    return sum((sign * r["d_" + f]) > 0 for r in rows) / len(rows)


def perm_null(rows, f, rng, nperm=NPERM):
    by_task = defaultdict(list)
    for r in rows:
        by_task[r["task_id"]].append(r)
    tasks = list(by_task)
    out = []
    for _ in range(nperm):
        flip = {t: rng.random() < 0.5 for t in tasks}
        out.append(sum(((-1 if flip[r["task_id"]] else 1) * r["d_" + f]) > 0 for r in rows) / len(rows))
    return out


def main():
    items = load_items()
    rows = []
    for it in items:
        QT[0] = toks(it["query"], 3)
        pre = it["prefix_text"]
        fc = [feats(o, pre, pre[-3000:]) for o in it["choices"]]
        good, bad = fc[it["answer_index"]], fc[1 - it["answer_index"]]
        r = {"id": it["id"], "cell": it["cell"], "task_id": it["task_id"], "answer": it["answer"],
             "prefix_chars": len(pre), "prefix_steps": it["prefix_steps"],
             "sabotage_in_prefix": bool(SABOTAGE.search(pre)),
             "verif_fork_query": bool(VERIF_FORK.search(it["query"])),
             "query_mentions_choose": bool(re.search(r"\bchoose\b|\bselect\b|\bnext (?:verification|diagnostic|step)", it["query"], re.I))}
        for f in FEATS:
            r["d_" + f] = round(good[f] - bad[f], 6)
            r["g_" + f], r["b_" + f] = round(good[f], 6), round(bad[f], 6)
        r["traj_hash"] = hashlib.sha256(pre[:4000].encode()).hexdigest()[:16]
        rows.append(r)

    # B1 inventory ---------------------------------------------------------------
    inv = {}
    for c in CELLS:
        rs = [r for r in rows if r["cell"] == c]
        its = [i for i in items if i["cell"] == c]
        per_task = Counter(r["task_id"] for r in rs)
        inv[c] = {"items": len(rs), "tasks": len(per_task), "traj_proxy": len({r["traj_hash"] for r in rs}),
                  "max_items_per_task": max(per_task.values()),
                  "top_task_items": sorted(per_task.values(), reverse=True)[:5],
                  "answer_A": sum(r["answer"] == "A" for r in rs),
                  "prefix_steps_median": statistics.median(r["prefix_steps"] for r in rs),
                  "prefix_chars_median": statistics.median(r["prefix_chars"] for r in rs),
                  "sources": dict(Counter(i["source"] for i in its)),
                  "sabotage_in_prefix": sum(r["sabotage_in_prefix"] for r in rs),
                  "sabotage_ids": [r["id"] for r in rs if r["sabotage_in_prefix"]],
                  "verif_fork_query": sum(r["verif_fork_query"] for r in rs),
                  "query_says_choose": sum(r["query_mentions_choose"] for r in rs)}
    inv["research_tasks_union"] = len({r["task_id"] for r in rows if r["cell"].endswith("research")})
    inv["paper_task_counts_match"] = [inv[c]["tasks"] for c in CELLS] == [62, 8, 133, 22]
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results/b1_inventory.json").write_text(json.dumps(inv, indent=1))

    # B2/B3 rules ----------------------------------------------------------------
    rng = random.Random(SEED)
    split = {}
    for c in CELLS:
        ts = sorted({r["task_id"] for r in rows if r["cell"] == c})
        random.Random(SEED).shuffle(ts)
        for k, t in enumerate(ts):
            split[(c, t)] = k % 2
    res = {}
    pvals = []
    for c in CELLS:
        rs = [r for r in rows if r["cell"] == c]
        h1 = [r for r in rs if split[(c, r["task_id"])] == 0]
        h2 = [r for r in rs if split[(c, r["task_id"])] == 1]
        res[c] = {}
        for f in FEATS:
            hi = rule_acc(rs, f, 1)
            lo = rule_acc(rs, f, -1)
            ties = 1 - hi - lo
            null = perm_null(rs, f, rng)
            p = sum(abs(v - 0.5) >= abs(hi - 0.5) - 1e-12 for v in null) / len(null)
            sign = 1 if rule_acc(h1, f, 1) >= rule_acc(h1, f, -1) else -1
            ho = rule_acc(h2, f, sign)
            null2 = perm_null(h2, f, rng)
            p_ho = sum((sign_acc(v, h2, f, sign) >= ho - 1e-12) for v in null2) / len(null2)
            res[c][f] = {"acc_higher": round(hi, 3), "acc_lower": round(lo, 3), "ties": round(ties, 3),
                         "perm_p_two_sided": round(p, 3), "heldout_direction": "higher" if sign == 1 else "lower",
                         "heldout_acc": round(ho, 3), "heldout_n": len(h2), "heldout_p_one_sided": round(p_ho, 3),
                         "mean_d": round(statistics.mean(r["d_" + f] for r in rs), 4)}
            if f in PREREG_FEATS:
                pvals.append((p_ho, c, f))
    # Holm over prereg features x cells, on held-out one-sided p
    pvals.sort()
    m = len(pvals)
    holm, running = {}, 0.0
    for k, (p, c, f) in enumerate(pvals):
        running = max(running, min(1.0, (m - k) * p))
        holm[(c, f)] = running
    for (c, f), v in holm.items():
        res[c][f]["holm_p"] = round(v, 3)
        res[c][f]["L2_confirmed"] = res[c][f]["heldout_acc"] >= 0.60 and v < 0.05

    # B3: pooled by construction, fixed predicted signs (parallel +, detour -)
    b3 = {}
    for f in ("cont", "ground"):
        for cons, sign in (("parallel", 1), ("detour", -1)):
            rs = [r for r in rows if r["cell"].startswith(cons)]
            h2 = [r for r in rs if split[(r["cell"], r["task_id"])] == 1]
            acc_full = rule_acc(rs, f, 1)
            acc_h2 = rule_acc(h2, f, 1)
            null = perm_null(h2, f, rng)
            p = (sum(v >= acc_h2 - 1e-12 for v in null) if sign == 1 else sum(v <= acc_h2 + 1e-12 for v in null)) / len(null)
            nullf = perm_null(rs, f, rng)
            pf = (sum(v >= acc_full - 1e-12 for v in nullf) if sign == 1 else sum(v <= acc_full + 1e-12 for v in nullf)) / len(nullf)
            b3[f"{f}_{cons}"] = {"pick_higher_acc_full": round(acc_full, 3), "p_full_one_sided": round(pf, 3),
                                 "pick_higher_acc_heldout": round(acc_h2, 3), "heldout_n": len(h2),
                                 "p_heldout_one_sided": round(p, 3), "predicted": ">0.5" if sign == 1 else "<0.5"}
        b3[f"{f}_confirmed"] = (b3[f"{f}_parallel"]["pick_higher_acc_heldout"] > 0.5 and b3[f"{f}_parallel"]["p_heldout_one_sided"] < 0.05
                                and b3[f"{f}_detour"]["pick_higher_acc_heldout"] < 0.5 and b3[f"{f}_detour"]["p_heldout_one_sided"] < 0.05)
    out = {"rules": res, "B3": b3, "n_tests_holm": m}
    (ROOT / "results/b2_rules.json").write_text(json.dumps(out, indent=1))
    with open(ROOT / "data/features.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(json.dumps(inv, indent=1)[:4000])
    print(json.dumps(b3, indent=1))
    for c in CELLS:
        print(c, {f: (v["acc_higher"], v["acc_lower"], v["perm_p_two_sided"], v["heldout_direction"], v["heldout_acc"], v.get("holm_p")) for f, v in res[c].items()})


def sign_acc(v, rows, f, sign):
    # v is a permuted 'higher' accuracy; for sign -1 the comparable statistic is the permuted 'lower' accuracy.
    # With ties t, lower = 1 - higher - t; ties are invariant under flips.
    if sign == 1:
        return v
    t = sum(r["d_" + f] == 0 for r in rows) / len(rows)
    return 1 - v - t


if __name__ == "__main__":
    main()
