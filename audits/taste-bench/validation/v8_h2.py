"""V8: what else the H2 cut changed, and a construction-label placebo for the H2 - H1 contrast (Haiku only)."""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v_common import DATA, SEED, load, save, toks  # noqa: E402

STEP = re.compile(r"^\[\d+\]", re.M)
TAIL = 2000
rows = {r["id"]: r for r in load()}


def recs(cond):
    out = defaultdict(list)
    for l in (DATA / f"haiku_{cond}.jsonl").read_text().splitlines():
        if l.strip():
            r = json.loads(l)
            out[r["id"]].append(bool(r.get("ok")))
    return {i: np.mean(v) for i, v in out.items()}


h1, h2 = recs("H1"), recs("H2")
items = []
for i, r in rows.items():
    s = r["prefix_text_short"]
    starts = [m.start() for m in STEP.finditer(s)]
    cut = len(s) - starts[-1] if len(starts) >= 2 else 0
    removed = s[starts[-1]:] if len(starts) >= 2 else ""
    w1 = s[-TAIL:]
    s2 = s[:starts[-1]] if len(starts) >= 2 else s
    w2 = s2[-TAIL:]
    # overlap of removed step with each option (Jaccard over >=3-char tokens)
    rt = set(toks(removed, 3))
    ov = []
    for o in r["choices"]:
        ot = set(toks(o, 3))
        ov.append(len(rt & ot) / len(rt | ot) if rt | ot else 0.0)
    corr = r["answer_index"]
    shared = len(set(toks(w1, 3)) & set(toks(w2, 3))) / max(1, len(set(toks(w1, 3)) | set(toks(w2, 3))))
    items.append({"id": i, "cell": r["cell"], "domain": r["domain"], "task": r["task_id"],
                  "detour": r["cell"].startswith("detour"), "cut_chars": cut,
                  "last_step_ge_window": cut >= TAIL, "window_jaccard_h1_h2": shared,
                  "removed_overlap_correct_minus_wrong": ov[corr] - ov[1 - corr],
                  "short_eq_full": r["prefix_text_short"] == r["prefix_text"],
                  "d": h2[i] - h1[i]})

d = np.array([x["d"] for x in items])
det = np.array([x["detour"] for x in items])
cut = np.array([x["cut_chars"] for x in items])
out = {"n": len(items)}
out["contrast_detour_minus_parallel"] = round(float((d[det].mean() - d[~det].mean()) * 100), 2)
out["mean_h2_minus_h1"] = {"detour": round(float(d[det].mean() * 100), 2), "parallel": round(float(d[~det].mean() * 100), 2)}
for name, mask in (("detour", det), ("parallel", ~det)):
    sub = [x for x, m in zip(items, mask) if m]
    out[name] = {
        "cut_chars_median": float(np.median([x["cut_chars"] for x in sub])),
        "share_last_step_ge_2000": round(float(np.mean([x["last_step_ge_window"] for x in sub])), 3),
        "window_jaccard_median": round(float(np.median([x["window_jaccard_h1_h2"] for x in sub])), 3),
        "removed_step_overlap_correct_minus_wrong_mean": round(float(np.mean([x["removed_overlap_correct_minus_wrong"] for x in sub])), 4),
        "share_removed_step_closer_to_wrong": round(float(np.mean([x["removed_overlap_correct_minus_wrong"] < 0 for x in sub])), 3),
        "share_items_changed": round(float(np.mean([x["d"] != 0 for x in sub])), 3),
        "share_prefix_short_equals_full": round(float(np.mean([x["short_eq_full"] for x in sub])), 3),
    }
# by cut length (median split over all items)
med = float(np.median(cut))
for tag, m in (("short_cut", cut <= med), ("long_cut", cut > med)):
    out[f"contrast_{tag}"] = round(float((d[det & m].mean() - d[~det & m].mean()) * 100), 2)
out["cut_median_all"] = med
# by domain
for dom in ("engineering", "research"):
    m = np.array([x["domain"] == dom for x in items])
    out[f"contrast_{dom}"] = round(float((d[det & m].mean() - d[~det & m].mean()) * 100), 2)
# placebo: shuffle construction labels across tasks within domain (task keeps one label per draw)
rng = np.random.default_rng(SEED)
null = []
for _ in range(1000):
    lab = {}
    for dom in ("engineering", "research"):
        ts = sorted({x["task"] for x in items if x["domain"] == dom})
        # keep the item share of detour roughly: assign each task detour with the domain's item share
        share = np.mean([x["detour"] for x in items if x["domain"] == dom])
        for t in ts:
            lab[(dom, t)] = rng.random() < share
    dl = np.array([lab[(x["domain"], x["task"])] for x in items])
    if dl.all() or (~dl).all():
        continue
    null.append((d[dl].mean() - d[~dl].mean()) * 100)
null = np.array(null)
out["placebo_construction_shuffle"] = {"n": int(len(null)), "p97.5": round(float(np.percentile(null, 97.5)), 2),
                                       "share_ge_observed": round(float((null >= out["contrast_detour_minus_parallel"]).mean()), 4)}
save("v8_h2.json", out)
print(json.dumps(out, indent=1))
