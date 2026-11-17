"""Validator step 5: GPT-4o defences, matched case by case against undefended GPT-4o.

Tool filter: the filter's tool list is the first assistant message of each trace (it is produced
from the user prompt alone, before any tool output exists). For the cases where that list still
contains the attacker's tool, compare tool-filter ASR with undefended GPT-4o ASR on the SAME
(user task, injection task) cases, and on cases exposed under both. Paired two-way bootstrap.
Also, for every defence, ASR on cases exposed in both the defended and undefended runs.

Run: ../data/.venv/bin/python -I v5_defences.py
Writes block 'defences' of validation.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np

from common_v import AUDIT, DEFENCES, GPT4O, save

D = json.load(open(os.path.join(AUDIT, "data", "validation_cases.json")))
by = {}
for r in D["cases"]:
    by.setdefault(r["pipeline"], {})[(r["suite"], r["ut"], r["inj"])] = r
keys = sorted(by[GPT4O])
# attacker's tool per injection task (from the GOAL strings; travel injection_task_6 is text-only)
TOOL = {("workspace", f"injection_task_{i}"): t for i, t in enumerate(
    ["send_email", "delete_file", "create_calendar_event", "send_email", "send_email", "send_email"])}
TOOL.update({("travel", f"injection_task_{i}"): t for i, t in enumerate(
    ["reserve_hotel", "send_email", "create_calendar_event", "send_email", "reserve_hotel", "send_email", None])})
TOOL.update({("banking", f"injection_task_{i}"): "send_money" for i in (0, 1, 2, 3, 5, 6, 8)})
TOOL.update({("banking", "injection_task_4"): "update_scheduled_transaction", ("banking", "injection_task_7"): "update_password"})
TOOL.update({("slack", f"injection_task_{i}"): t for i, t in zip(range(1, 6),
    ["send_direct_message", "post_webpage", "get_webpage", "post_webpage", "invite_user_to_slack"])})

uts = sorted({(k[0], k[1]) for k in keys})
its = sorted({(k[0], k[2]) for k in keys})
ui = np.array([uts.index((k[0], k[1])) for k in keys])
ii = np.array([its.index((k[0], k[2])) for k in keys])
rng = np.random.default_rng(20261117)
W = []
for _ in range(2000):
    cu = np.bincount(rng.integers(0, len(uts), len(uts)), minlength=len(uts))
    ci = np.bincount(rng.integers(0, len(its), len(its)), minlength=len(its))
    W.append((cu[ui] * ci[ii]).astype(float))
W = np.array(W)


def arr(p, f):
    return np.array([float(by[p][k][f]) for k in keys])


def rate_ci(x, mask):
    pt = float(x[mask].mean()) if mask.sum() else float("nan")
    num = (W * (x * mask)).sum(1)
    den = (W * mask).sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        b = num / den
    b = b[~np.isnan(b)]
    return round(pt, 4), [round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)]


def diff_ci(x, y, mask):
    pt = float(x[mask].mean() - y[mask].mean())
    with np.errstate(invalid="ignore", divide="ignore"):
        b = (W * (x * mask)).sum(1) / (W * mask).sum(1) - (W * (y * mask)).sum(1) / (W * mask).sum(1)
    b = b[~np.isnan(b)]
    return round(pt, 4), [round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)]


s0, e0 = arr(GPT4O, "security"), arr(GPT4O, "exposed")
tf = GPT4O + "-tool_filter"
st, et = arr(tf, "security"), arr(tf, "exposed")
kept = np.array([TOOL[(k[0], k[2])] is None or TOOL[(k[0], k[2])] in (by[tf][k].get("first_asst") or "") for k in keys])
kept_f = kept.astype(float)
m107 = (et == 1) & kept
mboth = m107 & (e0 == 1)
out = {"tool_filter": dict(
    n_kept=int(kept.sum()), share_kept=round(float(kept.mean()), 4), n_kept_exposed=int(m107.sum()),
    asr_tf_kept_exposed=rate_ci(st, m107), asr_undefended_same_cases=rate_ci(s0, m107),
    diff_tf_minus_undefended_same_cases=diff_ci(st, s0, m107),
    n_kept_exposed_both=int(mboth.sum()), asr_tf_kept_exposed_both=rate_ci(st, mboth),
    asr_undefended_kept_exposed_both=rate_ci(s0, mboth), diff_exposed_both=diff_ci(st, s0, mboth),
    asr_undefended_all_exposed=rate_ci(s0, e0 == 1),
    asr_undefended_on_cases_where_filter_removes_tool_exposed=rate_ci(s0, (~kept) & (e0 == 1)),
    asr_tf_tool_removed_exposed=rate_ci(st, (et == 1) & ~kept),
    kept_by_suite={s: int(sum(kept[j] for j, k in enumerate(keys) if k[0] == s)) for s in ("workspace", "travel", "banking", "slack")},
    asr_tf_all_kept=rate_ci(st, kept), asr_undefended_all_kept=rate_ci(s0, kept),
)}
# Every defence: ASR on cases exposed (or, for the detector, reached) in both runs
for d in DEFENCES:
    sd, ed = arr(d, "security"), arr(d, "exposed")
    if "pi_detector" in d:
        ed = np.maximum(ed, arr(d, "redacted"))
    m = (ed == 1) & (e0 == 1)
    out[d] = dict(n_both=int(m.sum()), asr_defended=rate_ci(sd, m), asr_undefended=rate_ci(s0, m), diff=diff_ci(sd, s0, m),
                  exposure_defended=round(float(ed.mean()), 4), exposure_undefended=round(float(e0.mean()), 4))
save("defences", out)
print(json.dumps(out, indent=1))
