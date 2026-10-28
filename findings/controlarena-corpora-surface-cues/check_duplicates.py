"""Check 5 (duplicates and split leakage) on the five adityaasinha28/control_arena_* corpora.

Two text views per row: the whole `transcript` (what a monitor reads) and the agent's actions
only (the [TOOL CALLS] blocks). For each view: exact duplicates after whitespace/case
normalisation, and MinHash (128 hashes over word 5-shingles) estimated Jaccard for every pair of
rows across all five settings. Reported: duplicate groups within and across labels, tasks and
settings; each row's nearest same-label and opposite-label neighbour within its task; how many
rows a greedy near-duplicate pass would remove; repetition of tasks over epochs; whether the
label is readable from the row id or row order; and the 2605.29601 pipeline's filtered and
training rows (which rows its 28K-token filter dropped, and whether its training mix shares rows
or near-copies with its out-of-distribution ControlArena sets).

Only counts, rates and ids are written.

Usage:
    python -I check_duplicates.py --cache data --out duplicates_checks.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.request
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

SETTINGS = ["bash", "shade", "iac", "rogue_eval", "agentdojo"]
PINS = {
    "bash": ("08663a5d10a5445bc4b750b7f8eb079c9a505df8", "29550a69f0d6c0dcc59b976d3a68fdf662ecd2620b2525c234ecb8794882e9c8"),
    "shade": ("7b5861e85f14381e70ed5b101fd7ceeec96d4f29", "2b637f8279804668f9210080f788b40d4cae133e56007d1d767f5da9e40e4eee"),
    "iac": ("cd0e7f667eba6214e2100f5fd30aec9f65aca1a8", "d74610fefa78bb7ae79594310e826d84c87b38508ba16104b3c64b2e92c343e8"),
    "rogue_eval": ("7946e03ece9d8329a28c17d7b0fe778b9c774b39", "2689c6e5ee7d708c07e798ddde9055606778938fdfd9d1aef9cfab66744c0640"),
    "agentdojo": ("a0f1e2131a8f27ebe14c285fa8ad34e439d128e2", "5ceb33f1116b9c317b98be1ddcfb7dddca300482ca45736faf291b0796ad5c33"),
}
PIPE_REPO = "adityaasinha28/deliberative-monitor-pipeline"
PIPE_SHA = "2f10f4e49f4bf349965640ac021406689455d1c3"
PAPER_TABLE2 = {"shade": (433, 423), "iac": (728, 715), "rogue_eval": (750, 750), "agentdojo": (750, 750)}
K = 128
MASK = np.uint64(0xFFFFFFFFFFFFFFFF)


def fetch(url: str, path: str, sha256: str | None = None) -> str:
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with urllib.request.urlopen(url, timeout=600) as r, open(path + ".part", "wb") as fh:
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                fh.write(b)
        os.replace(path + ".part", path)
    if sha256:
        h = hashlib.sha256(open(path, "rb").read()).hexdigest()
        if h != sha256:
            raise SystemExit(f"{path}: sha256 {h} != pinned {sha256}")
    return path


def corpus(cache, s):
    sha, h = PINS[s]
    url = f"https://huggingface.co/datasets/adityaasinha28/control_arena_{s}/resolve/{sha}/control_arena_{s}.parquet"
    return pd.read_parquet(fetch(url, os.path.join(cache, f"control_arena_{s}.parquet"), h),
                           columns=["id", "ground_truth", "transcript", "trajectory_data", "extra_info"])


def pipe(cache, rel):
    return fetch(f"https://huggingface.co/datasets/{PIPE_REPO}/resolve/{PIPE_SHA}/{rel}", os.path.join(cache, "pipeline", rel))


SEG = re.compile(r"(?m)^\[(USER|ASSISTANT|TOOL)\]\n")


def actions(tr: str) -> str:
    p = SEG.split(tr)
    return "\n".join(p[i + 1].split("[TOOL CALLS]", 1)[1] for i in range(1, len(p) - 1, 2)
                     if p[i] == "ASSISTANT" and "[TOOL CALLS]" in p[i + 1])


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip().lower()


rng0 = np.random.default_rng(12345)
A = (rng0.integers(1, 2**63, size=K, dtype=np.uint64) | np.uint64(1))
B = rng0.integers(0, 2**63, size=K, dtype=np.uint64)
VOCAB: dict[str, int] = {}


def minhash(text: str, n: int = 5) -> np.ndarray:
    toks = norm(text).split(" ")
    ids = np.array([VOCAB.setdefault(w, len(VOCAB) + 1) for w in toks], dtype=np.uint64)
    if len(ids) < n:
        ids = np.concatenate([ids, np.zeros(n - len(ids), dtype=np.uint64)])
    with np.errstate(over="ignore"):
        h = np.zeros(len(ids) - n + 1, dtype=np.uint64)
        for j in range(n):
            h = h * np.uint64(1000003) + ids[j:len(ids) - n + 1 + j]
        h = np.unique(h)
        sig = np.empty(K, dtype=np.uint64)
        for c in range(0, K, 16):
            v = A[c:c + 16, None] * h[None, :] + B[c:c + 16, None]
            v ^= v >> np.uint64(29)
            sig[c:c + 16] = v.min(axis=1)
    return sig


def sim_matrix(S: np.ndarray, block: int = 200) -> np.ndarray:
    n = len(S)
    M = np.zeros((n, n), dtype=np.float32)
    for i in range(0, n, block):
        M[i:i + block] = (S[i:i + block, None, :] == S[None, :, :]).mean(axis=2)
    np.fill_diagonal(M, 0)
    return M


def greedy_keep(M: np.ndarray, idx: np.ndarray, thr: float) -> int:
    kept: list[int] = []
    for i in idx:
        if not kept or M[i, kept].max() < thr:
            kept.append(i)
    return len(kept)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="duplicates_checks.json")
    a = ap.parse_args()

    frames = []
    for s in SETTINGS:
        df = corpus(a.cache, s)
        md = pd.json_normalize(df["trajectory_data"].map(lambda t: json.loads(t)["metadata"]))
        task = md["main_task_name"].astype(str)
        if "suite_name" in md:
            task = md["suite_name"].astype(str) + "/" + task
        frames.append(pd.DataFrame({"setting": s, "row": np.arange(len(df)), "id": df["id"], "y": df["ground_truth"].astype(int),
                                    "task": task.to_numpy(), "model": pd.json_normalize(df["extra_info"])["model"],
                                    "eval_file": pd.json_normalize(df["extra_info"])["eval_file"],
                                    "transcript": df["transcript"].fillna("")}))
    D = pd.concat(frames, ignore_index=True)
    D["actions"] = D["transcript"].map(actions)
    out: dict = {"pins": {s: PINS[s][0] for s in SETTINGS}, "pipeline_pin": PIPE_SHA,
                 "minhash": {"hashes": K, "shingle": "word 5-grams after lowercasing and whitespace collapse"},
                 "per_setting": {}, "cross_setting": {}}

    sims = {}
    for view in ["transcript", "actions"]:
        S = np.stack([minhash(t) for t in D[view]])
        sims[view] = sim_matrix(S)
        D[f"h_{view}"] = D[view].map(lambda t: hashlib.sha1(norm(t).encode()).hexdigest())

    st = D["setting"].to_numpy(); y = D["y"].to_numpy(); task = D["task"].to_numpy()
    for s in SETTINGS:
        ix = np.flatnonzero(st == s)
        r: dict = {}
        sub = D.iloc[ix]
        for view in ["transcript", "actions"]:
            M = sims[view][np.ix_(ix, ix)]
            yy = y[ix]; tt = task[ix]
            hcol = sub[f"h_{view}"]
            grp = hcol.map(hcol.value_counts())
            mixed = sub.groupby(f"h_{view}")["y"].nunique()
            v: dict = {
                "exact_dup_rows": int((grp > 1).sum()),
                "exact_dup_groups": int((hcol.value_counts() > 1).sum()),
                "exact_groups_with_both_labels": int((mixed > 1).sum()),
                "rows_in_both_label_exact_groups": int(sub[f"h_{view}"].isin(mixed[mixed > 1].index).sum()),
                "empty_rows": int((sub[view].str.strip() == "").sum()),
            }
            same_task = tt[:, None] == tt[None, :]
            same_lab = yy[:, None] == yy[None, :]
            iu = np.triu_indices(len(ix), 1)
            for thr in (0.8, 0.9):
                hit = M[iu] >= thr
                v[f"pairs_ge_{thr}"] = int(hit.sum())
                v[f"pairs_ge_{thr}_cross_label"] = int((hit & ~same_lab[iu]).sum())
                v[f"pairs_ge_{thr}_cross_task"] = int((hit & ~same_task[iu]).sum())
                rows_hit = np.zeros(len(ix), bool)
                rows_hit[iu[0][hit]] = True; rows_hit[iu[1][hit]] = True
                v[f"rows_with_neighbour_ge_{thr}"] = int(rows_hit.sum())
                v[f"greedy_dedup_kept_at_{thr}"] = greedy_keep(M, np.arange(len(ix)), thr)
            nn_same = np.where(same_task & same_lab, M, -1).max(axis=1)
            nn_opp = np.where(same_task & ~same_lab, M, -1).max(axis=1)
            v["median_nearest_same_label_same_task"] = round(float(np.median(nn_same[nn_same >= 0])), 4)
            v["median_nearest_opposite_label_same_task"] = round(float(np.median(nn_opp[nn_opp >= 0])), 4)
            v["nearest_neighbour_label_agreement"] = round(float(np.mean(yy[M.argmax(axis=1)] == yy)), 4)
            r[view] = v
        # repetition over epochs
        rep = sub.groupby(["model", "y"])["task"].agg(lambda x: (x.nunique(), int(x.value_counts().max())))
        r["distinct_tasks_and_max_rows_per_task_by_model_label"] = {f"{m}|{l}": list(t) for (m, l), t in rep.items()}
        r["rows_per_task_by_label"] = {str(k): v for k, v in pd.crosstab(sub["task"], sub["y"]).to_dict().items()} if sub["task"].nunique() <= 30 else None
        r["tasks_in_both_labels"] = int(len(set(sub.task[sub.y == 0]) & set(sub.task[sub.y == 1])))
        # label from id / order
        idpos = sub["id"].str.contains("_positive").astype(int).to_numpy()
        r["label_from_id_token_auroc"] = float(roc_auc_score(sub["y"], idpos))
        r["label_from_eval_file_auroc"] = float(roc_auc_score(sub["y"], sub["eval_file"].str.startswith("positive").astype(int)))
        r["label_from_row_order_block_auroc"] = float(roc_auc_score(sub["y"], ((sub["row"] % 500) >= 250).astype(int)))
        if s == "rogue_eval":
            r["rogue_eval_id_contains_attack_or_honest_word"] = {
                "attack_in_pos_ids": float(sub.id[sub.y == 1].str.contains("-attack").mean()),
                "honest_in_neg_ids": float(sub.id[sub.y == 0].str.contains("-honest").mean())}
        out["per_setting"][s] = r
        print(s, json.dumps({k: (r[k]["exact_dup_rows"], r[k]["pairs_ge_0.9"], r[k]["greedy_dedup_kept_at_0.9"]) for k in ["transcript", "actions"]}), flush=True)

    # cross-setting
    for view in ["transcript", "actions"]:
        M = sims[view]
        cross = st[:, None] != st[None, :]
        mx = np.where(cross, M, 0).max(axis=1)
        out["cross_setting"][view] = {
            "max_jaccard_to_other_setting": round(float(mx.max()), 4),
            "rows_with_other_setting_neighbour_ge_0.5": int((mx >= 0.5).sum()),
            "exact_hash_shared_across_settings": int(D.groupby(f"h_{view}")["setting"].nunique().gt(1).sum()),
        }

    # 2605.29601 pipeline: filter, training mix vs OOD sets
    pf = {}
    for s in ["shade", "iac", "rogue_eval", "agentdojo", "bash"]:
        keep = pd.read_parquet(pipe(a.cache, f"filtered_eval/ctrl_{s}.parquet"), columns=["row_index"])["row_index"].to_numpy()
        sub = D[D.setting == s].reset_index(drop=True)
        drop = np.setdiff1d(np.arange(len(sub)), keep)
        L = sub["transcript"].str.len().to_numpy()
        pf[s] = {"kept": int(len(keep)), "dropped": int(len(drop)),
                 "dropped_by_label": {str(l): int((sub.y.to_numpy()[drop] == l).sum()) for l in (0, 1)},
                 "dropped_by_model": Counter(sub.model.to_numpy()[drop].tolist()),
                 "dropped_by_task": Counter(sub.task.to_numpy()[drop].tolist()) if s in ("shade", "iac") else None,
                 "min_chars_dropped": int(L[drop].min()) if len(drop) else None,
                 "max_chars_kept": int(L[keep].max()),
                 "kept_rows_exceeding_min_dropped_chars": int((L[keep] >= (L[drop].min() if len(drop) else 1e18)).sum()),
                 "paper_table2": PAPER_TABLE2.get(s)}
        if s in ("shade", "iac"):
            pf[s]["greedy_near_dup_dedup_kept_at_0.9_transcript"] = out["per_setting"][s]["transcript"]["greedy_dedup_kept_at_0.9"]
            pf[s]["dropped_ids_sample"] = sub.id.to_numpy()[drop][:5].tolist()
    out["pipeline_28k_filter"] = pf

    merged = pd.read_parquet(pipe(a.cache, "merged/stride_gloom_s45_o46_ctrl_t7_bal.parquet"), columns=["messages", "dataset_source", "ground_truth"])
    def user_text(ms):
        u = [m["content"] for m in ms if m["role"] == "user"]
        return u[0] if u else ""
    merged["u"] = merged["messages"].map(user_text)
    hset = {s: set(D[D.setting == s]["h_transcript"]) for s in SETTINGS}
    mh = merged["u"].map(lambda t: hashlib.sha1(norm(t).encode()).hexdigest())
    lk = {}
    for src in merged["dataset_source"].unique():
        m = mh[merged.dataset_source == src]
        lk[src] = {"n": int(len(m)), **{f"exact_in_{s}": int(m.isin(hset[s]).sum()) for s in SETTINGS}}
    ctrl = merged[merged.dataset_source == "ctrl"]
    Sc = np.stack([minhash(t) for t in ctrl["u"]])
    So = np.stack([minhash(t) for t in D[D.setting != "bash"]["transcript"]])
    best = np.zeros(len(Sc))
    for i in range(0, len(Sc), 100):
        best[i:i + 100] = (Sc[i:i + 100, None, :] == So[None, :, :]).mean(axis=2).max(axis=1)
    out["pipeline_training_vs_ood"] = {"by_training_source": lk,
                                       "ctrl_training_rows_max_jaccard_to_ood_controlarena": round(float(best.max()), 4),
                                       "ctrl_training_rows_ge_0.5_to_ood": int((best >= 0.5).sum())}
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=1, default=lambda o: dict(o) if isinstance(o, Counter) else int(o))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
