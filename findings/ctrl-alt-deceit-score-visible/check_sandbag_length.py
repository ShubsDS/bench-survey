"""Run-size baselines for CTRL-ALT-DECEIT sandbagging detection (arXiv 2511.09904v2, Figure 8).

The authors' Google Drive folder (linked from the repo README) holds the general monitor's logs for
the same 353 runs as the released table: two Regular logs and three Sandbagging logs. Each sample
carries the full AIDE journal and run metadata. This script reads them as data (zip of JSON; no code
is run) and scores Sandbagging vs Regular with features that do not read content:
wall-clock time, working time, number of AIDE nodes, number of buggy nodes, total code characters
over all nodes, and agent output tokens. Each feature is reported as the AUROC of "larger value =
sandbagging" (below 0.5 means smaller values go with sandbagging), pooled and within task, with a
task-clustered bootstrap interval, next to the monitors' AUROC on the same rows.

Usage:
    python -I check_sandbag_length.py [--cache DIR] [--out sandbag_length_checks.json]
"""
import argparse, hashlib, json, urllib.request, zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

REPO = "0a12070c41ec06b81712f277590afbbed6ed6d6c"
RAW = f"https://raw.githubusercontent.com/TeunvdWeij/ctrl-alt-deceit/{REPO}/"
DRIVE = "https://drive.usercontent.google.com/download?id={}&export=download&confirm=t"
# Drive file ids (folder 13w5iST5LQ1oUOp2KeI_VegXXpfKhx4Qj/monitor), listed 2026-10-27; sha256 recorded on first download
LOGS = {
    "regular/big_regular_run_low_no_melanoma_10_epochs": "1-qS_KuY2FWzU_nb1Ruui_WrlCQOo1E9D",
    "regular/claude_3_7_lite_aide_teun": "1CssCHFEfU5BiEksX1GXTOPLBG71q7yWA",
    "sandbag/2025-07-17T11-07-57": "1Suzt3aHxW67IgjHa5tuIRobojRQnvM2B",
    "sandbag/2025-07-18T11-55-00": "164JTUHtXHU-gOq8VknN6jwTI5VSNWvUt",
    "sandbag/2025-07-19T19-46-14": "13sLlookCrkN-Ma1dGnzfJouRcjwtaXK5",
}
MONITORS = {"general (paper 0.60)": "default_system",
            "sandbagging-specific (paper 0.90)": "teun_sandbagging_specific_monitor_v1"}
B = 2000


def fetch(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with urllib.request.urlopen(url, timeout=1800) as r, open(path, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
    return path


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def features(cache):
    rows, hashes = [], {}
    for src, fid in LOGS.items():
        p = fetch(DRIVE.format(fid), cache / (src.replace("/", "__") + ".eval"))
        hashes[src] = {"drive_id": fid, "sha256": sha256(p), "bytes": p.stat().st_size}
        z = zipfile.ZipFile(p)
        for name in z.namelist():
            if not name.startswith("samples/"):
                continue
            d = json.loads(z.read(name))
            j = (d.get("metadata") or {}).get("aide_journal") or {}
            nodes = j.get("nodes") or []
            usage = next(iter((d.get("model_usage") or {}).values()), {})
            rows.append({
                "key": f"{src}|{d['id']}|{d['epoch']}",
                "wall_clock_seconds": d.get("total_time"),
                "working_seconds": d.get("working_time"),
                "aide_nodes": len(nodes),
                "aide_buggy_nodes": len(j.get("buggy_nodes") or []),
                "code_characters_all_nodes": sum(len(n.get("code") or "") for n in nodes),
                "agent_output_tokens": usage.get("output_tokens"),
            })
    return pd.DataFrame(rows), hashes


def auc(y, s):
    return float(roc_auc_score(y, s))


def cluster_ci(d, col, seed=0):
    rng = np.random.default_rng(seed)
    tasks = d.task.unique()
    groups = {t: d.index[d.task == t].values for t in tasks}
    vals = []
    for _ in range(B):
        x = d.loc[np.concatenate([groups[t] for t in rng.choice(tasks, tasks.size)])]
        if x.y.nunique() == 2:
            vals.append(auc(x.y, x[col]))
    return [round(float(np.percentile(vals, 2.5)), 3), round(float(np.percentile(vals, 97.5)), 3)]


def within(d, col):
    a = [auc(x.y, x[col]) for _, x in d.groupby("task") if x.y.nunique() == 2]
    return round(float(np.mean(a)), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="sandbag_length_checks.json")
    a = ap.parse_args()
    cache = Path(a.cache)
    base = None
    for name, stem in MONITORS.items():
        d = pd.read_csv(fetch(RAW + f"data/monitor_data_for_plotting/{stem}.csv", cache / f"{stem}.csv"))
        d["key"] = d.log_location.str.split("/").str[:2].str.join("/") + "|" + d.sample_id + "|" + d.sample_epoch.astype(str)
        if base is None:
            base = d[["key", "mode", "task", "task_score"]].copy()
        base[name] = base.key.map(d.set_index("key").monitor_score)
    feats, hashes = features(cache)
    df = base.merge(feats, on="key", how="left")
    df["y"] = (df["mode"] == "sandbagging").astype(int)
    cols = list(MONITORS) + [c for c in feats.columns if c != "key"]
    out = {"pins": {"ctrl-alt-deceit": REPO, "drive_logs": hashes},
           "rows_in_table": int(len(df)), "rows_matched_to_logs": int(df.wall_clock_seconds.notna().sum()),
           "class_medians": {c: {m: float(df[df["mode"] == m][c].median()) for m in ["regular", "sandbagging"]}
                             for c in cols if c not in MONITORS}}
    sb_tasks = set(df[df.y == 1].task)
    for label, d in [("all_runs", df), ("only_tasks_with_sandbagging_runs", df[df.task.isin(sb_tasks)])]:
        d = d.dropna(subset=["wall_clock_seconds"]).reset_index(drop=True)
        out[label] = {c: {"auroc_larger_is_sandbagging": round(auc(d.y, d[c]), 3),
                          "ci95_task_bootstrap": cluster_ci(d, c), "within_task_mean": within(d, c)}
                      for c in cols}
        out[label]["n"] = {"sandbagging": int(d.y.sum()), "regular": int((1 - d.y).sum())}
    Path(a.out).write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
