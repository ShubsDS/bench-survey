"""Claim 4: cross-dataset contrasts for the same action monitor (same monitor and monitor_variant).

movement = (matched_A - matched_B) - (raw_A - raw_B). Bootstrap draws reuse each row's own
run-level bootstrap from v1_core (independent across datasets). For LinuxArena paper vs
strategies, whose 200 honest runs are identical, a joint bootstrap resamples honest runs once.
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from vlib import arrays, ci, load, stats  # noqa: E402

H = Path(__file__).parent
core = json.loads((H / "v1_core.json").read_text())
d = load()
act = [r for r in core if r["kind"] == "action" and r["n_att"] >= 10]
by = {}
for r in act:
    by.setdefault((r["monitor"], r["variant"]), []).append(r)
out = []
for key, rs in by.items():
    for a, b in itertools.combinations(sorted(rs, key=lambda x: x["dataset"]), 2):
        ba, bb = a["boot_q5"], b["boot_q5"]
        mv_b = (np.array(ba["matched"]) - np.array(bb["matched"])) - (np.array(ba["raw"]) - np.array(bb["raw"]))
        rec = dict(monitor=key[0], variant=key[1], a=a["dataset"], b=b["dataset"],
                   diff_raw=a["q5"]["raw"] - b["q5"]["raw"], diff_matched=a["q5"]["matched"] - b["q5"]["matched"])
        rec["movement"] = rec["diff_matched"] - rec["diff_raw"]
        rec["movement_ci"] = ci(mv_b)
        rec["diff_matched_ci"] = ci(np.array(ba["matched"]) - np.array(bb["matched"]))
        rec["changes"] = abs(rec["movement"]) >= 0.05 and not (rec["movement_ci"][0] <= 0 <= rec["movement_ci"][1])
        rec["sign_flip"] = np.sign(rec["diff_raw"]) != np.sign(rec["diff_matched"])
        rec["sign_flip_robust"] = bool(rec["sign_flip"] and not (rec["diff_matched_ci"][0] <= 0 <= rec["diff_matched_ci"][1]))
        rec["involves_bash_or_mb"] = bool({a["dataset"], b["dataset"]} & {"basharena", "monitoringbench"})
        rec["exact_movement"] = (a["exact"]["matched"] - b["exact"]["matched"]) - rec["diff_raw"]
        rec["q20_movement"] = (a["q20"]["matched"] - b["q20"]["matched"]) - rec["diff_raw"]
        out.append(rec)

# joint bootstrap for paper vs strategies (shared honest runs)
rows = d["rows"]
rng = np.random.default_rng(99)
for rec in out:
    if {rec["a"], rec["b"]} != {"linuxarena-paper", "linuxarena-paper-strategies"}:
        continue
    ra = next(r for r in rows if r["dataset"] == rec["a"] and r["monitor_kind"] == "action" and r["monitor_variant"] == rec["variant"])
    rb = next(r for r in rows if r["dataset"] == rec["b"] and r["monitor_kind"] == "action" and r["monitor_variant"] == rec["variant"])
    A, Bq = arrays(ra), arrays(rb)
    hid_a = [s["trajectory_id"] for s in A["honest"][2]]
    hid_b = [s["trajectory_id"] for s in Bq["honest"][2]]
    assert hid_a == hid_b
    mv = []
    for _ in range(2000):
        ih = rng.integers(0, len(hid_a), len(hid_a))
        ia = rng.integers(0, len(A["attack"][0]), len(A["attack"][0]))
        ib = rng.integers(0, len(Bq["attack"][0]), len(Bq["attack"][0]))
        sa = stats(A["attack"][0][ia], A["attack"][1][ia], A["honest"][0][ih], A["honest"][1][ih])
        sb = stats(Bq["attack"][0][ib], Bq["attack"][1][ib], Bq["honest"][0][ih], Bq["honest"][1][ih])
        mv.append((sa["matched"] - sb["matched"]) - (sa["raw"] - sb["raw"]))
    rec["movement_ci_joint"] = ci(np.array(mv))
    rec["changes_joint"] = abs(rec["movement"]) >= 0.05 and not (rec["movement_ci_joint"][0] <= 0 <= rec["movement_ci_joint"][1])

n = len(out)
ch = [r for r in out if r["changes"]]
print("contrasts", n, "changes", len(ch), "sign flips among all", sum(r["sign_flip"] for r in out),
      "sign flips among changes", sum(r["sign_flip"] for r in ch),
      "robust flips (matched diff CI excludes 0)", sum(r["sign_flip_robust"] for r in out))
print("changes involving neither BashArena nor MonitoringBench:", sum(not r["involves_bash_or_mb"] for r in ch))
print("changes with |exact movement|>=0.05 same sign:", sum(abs(r["exact_movement"]) >= .05 and np.sign(r["exact_movement"]) == np.sign(r["movement"]) for r in ch))
for r in sorted(out, key=lambda x: (x["a"], x["b"], x["variant"])):
    print(f'{r["a"][:12]:12s} {r["b"][:16]:16s} {r["variant"][:22]:22s} raw {r["diff_raw"]:+.3f} matched {r["diff_matched"]:+.3f} '
          f'mv {r["movement"]:+.3f} [{r["movement_ci"][0]:+.3f},{r["movement_ci"][1]:+.3f}] ch {int(r["changes"])} flip {int(r["sign_flip"])} '
          f'robustflip {int(r["sign_flip_robust"])} exact_mv {r["exact_movement"]:+.3f}'
          + (f' joint [{r["movement_ci_joint"][0]:+.3f},{r["movement_ci_joint"][1]:+.3f}] chj {int(r["changes_joint"])}' if "movement_ci_joint" in r else ""))
(H / "v5_contrasts.json").write_text(json.dumps(out, default=lambda o: bool(o) if isinstance(o, np.bool_) else float(o)))
