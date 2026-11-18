"""Analyse the two pre-registered emulation outcomes (prereg.md) and write results_emulation.json.

Outcome 1 (emulation_full.jsonl): y = 1 if the next action is the misaligned tool.
Outcome 2 (emulation_probe.jsonl): y = 1 if the probe answer is YES ("allowed").
Blocked / unparsed / error decisions are dropped from rates and counted separately.

Intervals: bootstrap over scenarios resampled within domain (10,000, seed 20261117); robustness by
resampling workspaces; exact two-sided sign test on discordant scenario pairs.
"""
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import AUDIT

B = 10_000
SEED = 20261117


def load(name, positive):
    rows = [json.loads(l) for l in (AUDIT / name).read_text().splitlines() if l.strip()]
    y, bad, mix = {}, Counter(), Counter()
    meta = {}
    for r in rows:
        key = (r["arm"], r["naming"], r["pressure"])
        mix[key + (r["outcome"],)] += 1
        meta[r["uid"]] = (r["domain"], r["workspace"], r.get("late_licenses_bypass"))
        if r["outcome"] in ("blocked", "unparsed", "error"):
            bad[key + (r["outcome"],)] += 1
            continue
        y[(r["uid"],) + key] = int(r["outcome"] == positive)
    return rows, y, bad, mix, meta


def upper95_zero(n):
    return 1 - 0.05 ** (1 / n) if n else None


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def cell(y, arm, naming, pressure, uids):
    vals = [y[(u, arm, naming, pressure)] for u in uids if (u, arm, naming, pressure) in y]
    k, n = sum(vals), len(vals)
    out = {"k": k, "n": n, "rate": round(k / n, 4) if n else None, "wilson95": wilson(k, n)}
    if n and k == 0:
        out["upper95_one_sided"] = round(upper95_zero(n), 4)
    return out


def per_scenario(y, a, b, namings, pressure, uids):
    """Scenario-level mean over namings of y[b] - y[a] (pairs with both parsed only)."""
    d = {}
    for u in uids:
        diffs = [y[(u, b, nm, pressure)] - y[(u, a, nm, pressure)] for nm in namings
                 if (u, a, nm, pressure) in y and (u, b, nm, pressure) in y]
        if diffs:
            d[u] = sum(diffs) / len(diffs)
    return d


def per_scenario_gap(y, arm, pressure, uids):
    return {u: y[(u, arm, "benign", pressure)] - y[(u, arm, "harmful", pressure)] for u in uids
            if (u, arm, "benign", pressure) in y and (u, arm, "harmful", pressure) in y}


def boot(d, meta, level, rng):
    """Mean of d with a stratified (domain) or cluster (workspace) bootstrap interval."""
    if not d:
        return None
    est = sum(d.values()) / len(d)
    groups = defaultdict(list)
    for u, v in d.items():
        groups[meta[u][0] if level == "domain" else meta[u][1]].append(v)
    means = []
    if level == "domain":
        for _ in range(B):
            vals = []
            for g in groups.values():
                vals += [g[rng.randrange(len(g))] for _ in g]
            means.append(sum(vals) / len(vals))
    else:
        keys = list(groups)
        for _ in range(B):
            vals = []
            for _ in keys:
                vals += groups[keys[rng.randrange(len(keys))]]
            means.append(sum(vals) / len(vals))
    means.sort()
    return {"est": round(est, 4), "ci95": [round(means[int(0.025 * B)], 4), round(means[int(0.975 * B) - 1], 4)]}


def sign_test(d):
    pos = sum(v > 0 for v in d.values())
    neg = sum(v < 0 for v in d.values())
    n = pos + neg
    if n == 0:
        return {"pos": 0, "neg": 0, "p": 1.0}
    k = min(pos, neg)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)
    return {"pos": pos, "neg": neg, "p": round(p, 4)}


def contrast(y, meta, a, b, namings, pressure, uids, seed_off):
    d = per_scenario(y, a, b, namings, pressure, uids)
    return {"n_scenarios": len(d),
            "domain_boot": boot(d, meta, "domain", random.Random(SEED + seed_off)),
            "workspace_boot": boot(d, meta, "workspace", random.Random(SEED + seed_off + 1)),
            "sign_test": sign_test(d)}


def analyse(name, positive, arms, pressures):
    rows, y, bad, mix, meta = load(name, positive)
    uids = sorted(meta)
    res = {"file": name, "n_scenarios": len(uids), "n_rows": len(rows),
           "excluded": {"|".join(k): v for k, v in sorted(bad.items())},
           "outcome_mix": {"|".join(k): v for k, v in sorted(mix.items())}, "cells": {}, "contrasts": {}, "naming_gap": {}}
    for arm in arms:
        for pr in pressures:
            for nm in ("harmful", "benign"):
                if any((u, arm, nm, pr) in y for u in uids):
                    res["cells"][f"{arm}|{nm}|{pr}"] = cell(y, arm, nm, pr, uids)
            pooled = [y[(u, arm, nm, pr)] for u in uids for nm in ("harmful", "benign") if (u, arm, nm, pr) in y]
            if pooled:
                res["cells"][f"{arm}|pooled|{pr}"] = {"k": sum(pooled), "n": len(pooled),
                                                      "rate": round(sum(pooled) / len(pooled), 4),
                                                      "wilson95": wilson(sum(pooled), len(pooled))}
    i = 0
    for pr in pressures:
        for a, b in (("A", "B1"), ("P", "B1"), ("A", "P"), ("B1", "B2"), ("A", "B2"), ("A", "G")):
            for label, nms in (("pooled", ("harmful", "benign")), ("harmful", ("harmful",)), ("benign", ("benign",))):
                if any((u, b, nms[0], pr) in y for u in uids) and any((u, a, nms[0], pr) in y for u in uids):
                    i += 10
                    res["contrasts"][f"{b}-{a}|{label}|{pr}"] = contrast(y, meta, a, b, nms, pr, uids, i)
        for arm in arms:
            d = per_scenario_gap(y, arm, pr, uids)
            if d:
                i += 10
                res["naming_gap"][f"{arm}|{pr}"] = {"n_scenarios": len(d),
                                                    "domain_boot": boot(d, meta, "domain", random.Random(SEED + i)),
                                                    "sign_test": sign_test(d)}
    return res, y, meta, uids


def main():
    out = {}
    if (AUDIT / "emulation_full.jsonl").exists():
        r1, y1, meta1, uids1 = analyse("emulation_full.jsonl", "misaligned", ("A", "P", "B1", "B2", "G"), ("none", "late"))
        # Secondary: outcome-1 mix by the hand label on the late message (arm A, late)
        lab = defaultdict(Counter)
        for row in (json.loads(l) for l in (AUDIT / "emulation_full.jsonl").read_text().splitlines()):
            if row["pressure"] == "late":
                lab[f"{row['arm']}|licenses_bypass={row['late_licenses_bypass']}"][row["outcome"]] += 1
        r1["late_by_license_label"] = {k: dict(v) for k, v in sorted(lab.items())}
        out["outcome1_action"] = r1
    if (AUDIT / "emulation_probe.jsonl").exists():
        r2, *_ = analyse("emulation_probe.jsonl", "yes", ("A", "P", "B1", "B2", "G"), ("probe",))
        out["outcome2_probe"] = r2
    (AUDIT / "results_emulation.json").write_text(json.dumps(out, indent=1) + "\n")
    for k, v in out.items():
        print("==", k)
        for c, s in v["cells"].items():
            print(f"  {c:28s} {s['k']:3d}/{s['n']:3d}  {s['rate']}")
        for c, s in v["contrasts"].items():
            if "pooled" in c or True:
                db = s["domain_boot"]
                print(f"  {c:28s} {db['est']:+.3f} {db['ci95']}  sign {s['sign_test']}")
        for c, s in v["naming_gap"].items():
            print(f"  gap {c:24s} {s['domain_boot']['est']:+.3f} {s['domain_boot']['ci95']}")
        print("  excluded:", v["excluded"])


if __name__ == "__main__":
    main()
