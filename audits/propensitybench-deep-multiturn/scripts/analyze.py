"""Aggregate run files into results.json (prereg.md statistics).

    python3 -I scripts/analyze.py
"""
import glob
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

FOLDER = Path(__file__).resolve().parent.parent
SEED, BOOT = 20261120, 10000


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0, c - h), 4), round(min(1, c + h), 4)]


def upper0(n):
    return round(1 - 0.05 ** (1 / n), 4) if n else None


def load():
    rows = []
    for p in sorted(glob.glob(str(FOLDER / "runs" / "*.jsonl"))):
        for l in Path(p).read_text().splitlines():
            if l.strip():
                r = json.loads(l)
                if "skipped" not in r:
                    if r["status"] == "error" and "BlockedError" in (r.get("error") or ""):
                        r["status"] = "blocked"   # runs written before the harness.py status fix
                    r["file"] = Path(p).name
                    rows.append(r)
    return rows


def summarise(rs):
    comp = [r for r in rs if r["status"] == "complete"]
    k = sum(r["trigger_called"] for r in comp)
    n = len(comp)
    counts = Counter()
    for r in rs:
        counts.update(r["counts"])
    per_run = lambda key: sorted(r["counts"].get(key, 0) for r in rs)  # noqa: E731
    out = {
        "n_runs": len(rs), "status": dict(Counter(r["status"] for r in rs)),
        "n_complete": n, "misaligned": k, "rate": round(k / n, 4) if n else None, "wilson95": wilson(k, n),
        "upper95_if_zero": upper0(n) if k == 0 else None,
        "worst_case_blocked_error_as_misaligned": [k + len(rs) - n, len(rs)],
        "trigger_levels": dict(Counter(str(r["trigger_level"]) for r in comp if r["trigger_called"])),
        "runs_reaching_level_12": sum(r["levels_reached"] == 12 for r in comp),
        "by_domain": {d: [sum(r["trigger_called"] for r in comp if r["domain"] == d),
                          sum(1 for r in comp if r["domain"] == d)] for d in sorted({r["domain"] for r in comp})},
        "count_totals": dict(sorted(counts.items())),
        "runs_with": {key: sum(1 for r in rs if r["counts"].get(key)) for key in
                      ("format_errors", "malformed_tool_call", "tool_call_with_text", "unknown_tool", "bad_argument_json",
                       "interaction_limit", "message_limit", "multiple_tool_calls", "empty_responses", "llm_failures")},
        "terminate_messages_per_run": per_run("terminate_messages"),
        "aligned_calls_per_run": per_run("aligned_calls"),
        "llm_calls_per_run": sorted(r["n_llm_calls"] for r in rs),
        "cost_usd_total": round(sum(r.get("cost_usd", 0) for r in rs), 4),
        "cost_usd_per_run_mean": round(sum(r.get("cost_usd", 0) for r in rs) / len(rs), 4) if rs else None,
        "seconds_per_run_mean": round(sum(r["seconds"] for r in rs) / len(rs), 1) if rs else None,
    }
    return out


def paired(rs):
    """Three-arm paired statistics, if all three arms exist for some scenarios."""
    by = defaultdict(dict)
    for r in rs:
        if r["status"] == "complete":
            by[r["uid"]][r["arm"]] = (r["trigger_called"], r["domain"], r["workspace"])
    full = {u: v for u, v in by.items() if {"shipped", "restored", "placebo"} <= set(v)}
    if not full:
        return None
    units = [(v["shipped"][1], v["shipped"][2], int(v["shipped"][0]), int(v["restored"][0]), int(v["placebo"][0]))
             for u, v in sorted(full.items())]

    def st(us):
        n = len(us)
        A = sum(x[2] for x in us) / n
        B = sum(x[3] for x in us) / n
        P = sum(x[4] for x in us) / n
        return {"A": A, "B": B, "P": P, "A_minus_B": A - B, "A_minus_P": A - P, "D": (A - B) - (A - P)}

    point = st(units)
    rng = random.Random(SEED)
    strata = defaultdict(list)
    for x in units:
        strata[x[0]].append(x)
    boots = defaultdict(list)
    for _ in range(BOOT):
        s = [rng.choice(v) for v in strata.values() for _ in v]
        for kk, vv in st(s).items():
            boots[kk].append(vv)
    ws = defaultdict(list)
    for x in units:
        ws[x[1]].append(x)
    wl = list(ws.values())
    wboots = defaultdict(list)
    for _ in range(BOOT):
        s = [x for _ in wl for x in rng.choice(wl)]
        for kk, vv in st(s).items():
            wboots[kk].append(vv)
    ci = lambda v: [round(sorted(v)[int(0.025 * BOOT)], 4), round(sorted(v)[int(0.975 * BOOT) - 1], 4)]  # noqa: E731
    disc = {"P1_B0": sum(1 for x in units if x[4] == 1 and x[3] == 0), "P0_B1": sum(1 for x in units if x[4] == 0 and x[3] == 1),
            "A1_B0": sum(1 for x in units if x[2] == 1 and x[3] == 0), "A0_B1": sum(1 for x in units if x[2] == 0 and x[3] == 1)}

    def sign_p(a, b):
        n = a + b
        if n == 0:
            return 1.0
        k = min(a, b)
        return round(min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n), 4)
    return {"n_scenarios": len(units), "point": {k: round(v, 4) for k, v in point.items()},
            "ci95_domain_stratified": {k: ci(v) for k, v in boots.items()},
            "ci95_workspace_cluster": {k: ci(v) for k, v in wboots.items()},
            "discordant": disc, "sign_test_P_vs_B": sign_p(disc["P1_B0"], disc["P0_B1"]),
            "sign_test_A_vs_B": sign_p(disc["A1_B0"], disc["A0_B1"])}


def main():
    rows = load()
    groups = defaultdict(list)
    for r in rows:
        groups[(r["backend"], r["arm"], r["naming"], r["category"])].append(r)
    out = {"groups": {"|".join(k): summarise(v) for k, v in sorted(groups.items())}, "paired": {}}
    for be in sorted({r["backend"] for r in rows}):
        p = paired([r for r in rows if r["backend"] == be])
        if p:
            out["paired"][be] = p
    led = FOLDER / "inference" / "ledger.jsonl"
    if led.exists():
        L = [json.loads(l) for l in led.read_text().splitlines() if l.strip()]
        out["inference"] = {"calls": len(L), "cost_usd": round(sum(x["cost_usd"] for x in L), 4),
                            "by_model": {m: [sum(1 for x in L if x["model"] == m), round(sum(x["cost_usd"] for x in L if x["model"] == m), 4)]
                                         for m in sorted({x["model"] for x in L})}}
    prev = FOLDER / "results.json"
    base = json.loads(prev.read_text()) if prev.exists() else {}
    base.update({"runs": out})
    prev.write_text(json.dumps(base, indent=1) + "\n")
    print(json.dumps(out, indent=1)[:4000])


if __name__ == "__main__":
    main()
