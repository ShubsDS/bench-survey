"""Analysis 1 (prereg.md): frozen options-only rules on every released LAB-Bench SeqQA/DbQA version,
the Inspect port's pinned revision, the mirrors and the HuggingFaceBio curated subset.

R1 = the parent's rules, imported by path from ../lab-bench/scripts/surface.py (centroid; num_center).
R2 = summed Levenshtein medoid (numeric medoid when every option is a number), written here.
Placebo rule P = option with the smallest sha1(text). Permutation null: key uniform among options.
Intervals: bootstrap over subtasks (templates). Item text is never written out.

Run: ../lab-bench/data/.venv/bin/python -I scripts/versions.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent.parent
PARENT = HERE.parent / "lab-bench"
sys.path.insert(0, str(PARENT / "scripts"))
from surface import item_rules  # noqa: E402  (parent's frozen rules)

DATA = HERE / "data"
S_SUBTASKS = ["ORF-seq-AAseq", "PCR-gene-enzprimers", "PCR-seq-enzprimers", "PCR-gene-gibshindprimers",
              "PCR-gene-gibssmaprimers", "Prop-seq-gcpercent"]
R1_RULE = {s: "centroid" for s in S_SUBTASKS} | {"Prop-seq-gcpercent": "num_center"}
SOURCES = {  # label -> (path, date, note)
    "hf@7268767a": ("hfrev_7268767a", "2024-07-16", "first public release"),
    "hf@10866fa8": ("hfrev_10866fa8", "2024-08-20", ""),
    "hf@8e6bb002": ("hfrev_8e6bb002", "2024-12-18", ""),
    "hf@4709d14f": ("hfrev_4709d14f", "2025-02-19", "README: restriction-enzyme fix to a SeqQA subset"),
    "hf@8137378e": ("hfrev_8137378e", "2025-07-15", ""),
    "hf@5c77cec6": (str(PARENT / "data" / "hf"), "2025-09-27", "parent's pin; Inspect Evals lab_bench pins this revision; "
                    "mirrors introvoyz041 and Maxue627 are byte-identical (parent)"),
}
NUM = re.compile(r"^[-+]?\d+(\.\d+)?%?$")
SEED = 0


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def lev(a: str, b: str) -> int:
    """Levenshtein distance, row DP with a vectorised insertion pass."""
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    bv = np.array([ord(c) for c in b])
    prev = np.arange(len(b) + 1)
    ar = np.arange(len(b) + 1)
    for i, ch in enumerate(a, 1):
        cur = np.empty_like(prev)
        cur[0] = i
        cur[1:] = np.minimum(prev[1:] + 1, prev[:-1] + (bv != ord(ch)))
        cur = np.minimum.accumulate(cur - ar) + ar  # insertions: cur[j] = min(cur[j], cur[j-1]+1)
        prev = cur
    return int(prev[-1])


def frac_credit(scores, key=0, lower=True):
    s = np.asarray(scores, dtype=float)
    best = s.min() if lower else s.max()
    w = np.isclose(s, best).astype(float)
    return w / w.sum()


def r2_weights(opts):
    o = [x.strip() for x in opts]
    if all(NUM.match(x) for x in o):
        v = np.array([float(x.rstrip("%")) for x in o])
        return frac_credit(np.abs(v[:, None] - v[None, :]).sum(1))
    k = len(o)
    d = np.zeros((k, k))
    for i in range(k):
        for j in range(i + 1, k):
            d[i, j] = d[j, i] = lev(o[i], o[j])
    return frac_credit(d.sum(1))


def placebo_weights(opts):
    return frac_credit([int(hashlib.sha1(o.encode()).hexdigest(), 16) for o in opts])


def r1_weights(opts, rule):
    """Weights per option position from the parent's rule, by evaluating it with each position as key."""
    w = []
    for k in range(len(opts)):
        perm = [opts[k]] + [opts[j] for j in range(len(opts)) if j != k]
        r = item_rules(perm)[rule]
        w.append(0.0 if r != r else r)  # NaN -> 0
    w = np.asarray(w, dtype=float)
    return w if w.sum() > 0 else np.full(len(opts), 1.0 / len(opts))


def load(path: Path, subset: str):
    t = pq.read_table(path / subset / "train-00000-of-00001.parquet").to_pandas()
    t["subtask"] = t["subtask"].str.replace("-public", "").str.replace("-v1", "")
    return t


def subtask_stats(rows, rng):
    out = {}
    for st in sorted({r["subtask"] for r in rows}):
        g = [r for r in rows if r["subtask"] == st]
        e = {"n": len(g), "chance": round(float(np.mean([1 / len(r["w2"]) for r in g])), 4)}
        for name in ("r1", "r2", "placebo"):
            ws = [r["w" + name[-1] if name != "placebo" else "wp"] for r in g]
            obs = float(np.mean([w[0] for w in ws]))
            null = np.array([np.mean([w[rng.integers(len(w))] for w in ws]) for _ in range(1000)])
            e[name] = round(obs, 4)
            e[name + "_p"] = round(float((1 + (null >= obs).sum()) / 1001), 4)
            halves = [np.mean([w[0] for w, r in zip(ws, g) if int(hashlib.sha1(r["id"].encode()).hexdigest(), 16) % 2 == h] or [np.nan]) for h in (0, 1)]
            e[name + "_halves"] = [round(float(x), 4) for x in halves]
        e["carries_cue"] = bool((e["r1"] >= 0.90 and e["r1_p"] < 0.01) or (e["r2"] >= 0.90 and e["r2_p"] < 0.01))
        out[st] = e
    return out


def boot_over_subtasks(vals, rng, n=2000):
    vals = np.asarray(vals, dtype=float)
    bs = [np.mean(rng.choice(vals, len(vals))) for _ in range(n)]
    return [round(float(np.quantile(bs, q)), 4) for q in (0.025, 0.975)]


def run_seq(label, path, ref=None):
    df = load(path, "SeqQA")
    rows = []
    for _, r in df.iterrows():
        opts = [r["ideal"]] + list(r["distractors"])
        rule = R1_RULE.get(r["subtask"], "num_center" if all(NUM.match(o.strip()) for o in opts) else "centroid")
        rows.append({"id": r["id"], "subtask": r["subtask"], "w1": r1_weights(opts, rule), "w2": r2_weights(opts),
                     "wp": placebo_weights(opts), "key": r["ideal"], "opts": tuple(sorted(o.strip() for o in opts))})
    rng = np.random.default_rng(SEED)
    st = subtask_stats(rows, rng)
    S = [s for s in S_SUBTASKS if s in st]
    F = [s for s in st if s not in S_SUBTASKS]
    res = {"n_items": len(rows), "n_subtasks": len(st), "subtasks": st,
           "S_carrying_cue": [s for s in S if st[s]["carries_cue"]],
           "F_carrying_cue": [s for s in F if st[s]["carries_cue"]]}
    for name in ("r1", "r2", "placebo"):
        res[name + "_S_mean"] = round(float(np.mean([st[s][name] for s in S])), 4)
        res[name + "_S_ci_subtasks"] = boot_over_subtasks([st[s][name] for s in S], rng)
        res[name + "_F_mean"] = round(float(np.mean([st[s][name] for s in F])), 4)
        res[name + "_all_mean"] = round(float(np.mean([st[s][name] for s in st])), 4)
        res[name + "_all_ci_subtasks"] = boot_over_subtasks([st[s][name] for s in st], rng)
    res["flaw_present"] = len(res["S_carrying_cue"]) >= 4
    if ref is not None:  # item-level change counts against the parent's pin
        ref_by = {r["id"]: r for r in ref}
        ids = {r["id"] for r in rows}
        same_id = [r for r in rows if r["id"] in ref_by]
        res["vs_parent_pin"] = {
            "ids_shared": len(same_id), "ids_only_here": len(ids - set(ref_by)), "ids_only_in_pin": len(set(ref_by) - ids),
            "key_changed": sum(r["key"] != ref_by[r["id"]]["key"] for r in same_id),
            "option_set_changed": sum(r["opts"] != ref_by[r["id"]]["opts"] for r in same_id),
            "new_ids_by_subtask": {s: sum(1 for r in rows if r["subtask"] == s and r["id"] not in ref_by)
                                   for s in sorted(st) if any(r["subtask"] == s and r["id"] not in ref_by for r in rows)},
        }
    return res, rows


def run_dbqa(path):
    df = load(path, "DbQA")
    g = df[df.subtask.str.contains("variant_multi_sequence")]
    w1 = [r1_weights([r["ideal"]] + list(r["distractors"]), "centroid")[0] for _, r in g.iterrows()]
    w2 = [r2_weights([r["ideal"]] + list(r["distractors"]))[0] for _, r in g.iterrows()]
    return {"n": len(g), "r1": round(float(np.mean(w1)), 4), "r2": round(float(np.mean(w2)), 4)}


def run_curated():
    p = DATA / "hfbio_carbon_data" / "data" / "test-00000-of-00001.parquet"
    t = pq.read_table(p).to_pandas()
    cols = t.columns.tolist()
    out = {"path": str(p.relative_to(HERE)), "sha256": sha(p), "n": len(t), "columns": cols}
    if {"options", "answer_index"} <= set(cols):
        sub = "subtask"
        rows = []
        for _, r in t.iterrows():
            o = list(r["options"])
            k = int(r["answer_index"])
            opts = [o[k]] + [o[j] for j in range(len(o)) if j != k]  # key first
            rows.append({"id": str(r.get("id", _)), "subtask": str(r[sub]).replace("-public", "").replace("-v1", "") if sub else "all",
                         "w1": r1_weights(opts, "centroid"), "w2": r2_weights(opts), "wp": placebo_weights(opts)})
        out["subtasks"] = subtask_stats(rows, np.random.default_rng(SEED))
        pin = pq.read_table(PARENT / "data" / "hf" / "SeqQA" / "train-00000-of-00001.parquet").to_pandas()
        out["ids_in_parent_pin"] = int(t["id"].isin(set(pin["id"])).sum())
    return out


def main():
    out = {"sources": {}, "files": {}}
    ref_res, ref_rows = run_seq("hf@5c77cec6", Path(SOURCES["hf@5c77cec6"][0]))
    for label, (p, date, note) in SOURCES.items():
        path = Path(p) if Path(p).is_absolute() else DATA / p
        for s in ("SeqQA", "DbQA"):
            out["files"][f"{label}/{s}"] = sha(path / s / "train-00000-of-00001.parquet")
        res = ref_res if label == "hf@5c77cec6" else run_seq(label, path, ref_rows)[0]
        res["date"], res["note"] = date, note
        res["dbqa_variant_multi_sequence"] = run_dbqa(path)
        out["sources"][label] = res
        print(label, date, "S carrying:", len(res["S_carrying_cue"]), "F carrying:", res["F_carrying_cue"],
              "R1 S", res["r1_S_mean"], "R2 S", res["r2_S_mean"], "placebo all", res["placebo_all_mean"],
              "dbqa", res["dbqa_variant_multi_sequence"], res.get("vs_parent_pin", {}).get("option_set_changed"))
    out["hfbio_curated"] = run_curated()
    print(json.dumps(out["hfbio_curated"], indent=1)[:2500])
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "versions.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
