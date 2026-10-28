"""Row-level review coverage in METR's MALT, and the MALT rows that rh-bench reuses.

Lead 0/6: which benign runs were human-reviewed, by model, from MALT's per-run
`manually_reviewed` flag (not the card table); and, joining rh-bench's `source_id` to MALT
`run_id`, how many of rh-bench's MALT "clean" rows (all marked verification=human) were reviewed,
and what MALT labels its MALT "hacking" rows carry.

Reads metadata columns only. Outputs hold counts and run ids, never transcript text.

    python -I check_review.py --cache data [--remote-public-meta]

Downloads: metr-evals/malt-transcripts-public@TRANSCRIPTS_SHA data/* (~1.6 GB, gated; shared
with check_transcripts.py) and ktolnos/rh-bench@RH_SHA data/rh_bench_unified.parquet (public).
--remote-public-meta also reads the `metadata` column of metr-evals/malt-public@PUBLIC_SHA (data/
and the unreferenced default/ folder) over HTTP with DuckDB, to check the two repos agree per run.
"""
import argparse, json, subprocess
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

TRANSCRIPTS_SHA = "3521e8e22b6af12fea3249443e554b96b6fc4f49"
PUBLIC_SHA = "6100006c2fd23d81e5afe2b1cc3bf3f3fff48df1"
RH_SHA = "1045a7336432c40182924bbd3698af292ea24acb"
HF = str(Path.home() / ".local/bin/hf")
SANDBAG = {"match_weaker_model", "partial_problem_solving", "refusals", "sabotage"}
META = ["run_id", "labels", "task_id", "model", "has_chain_of_thought", "run_source", "manually_reviewed"]


def download(cache):
    t = cache / "malt-transcripts-public"
    if not list((t / "data").glob("*.parquet")):
        subprocess.run([HF, "download", "metr-evals/malt-transcripts-public", "--repo-type", "dataset",
                        "--revision", TRANSCRIPTS_SHA, "--include", "data/*", "--local-dir", str(t)], check=True)
    r = cache / "rh-bench"
    f = r / "data/rh_bench_unified.parquet"
    if not f.exists():
        subprocess.run([HF, "download", "ktolnos/rh-bench", "data/rh_bench_unified.parquet", "--repo-type", "dataset",
                        "--revision", RH_SHA, "--local-dir", str(r)], check=True)
    return sorted((t / "data").glob("*.parquet")), f


def remote_public_meta():
    import duckdb
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("CREATE SECRET hf (TYPE HUGGINGFACE, PROVIDER credential_chain)")  # token read by DuckDB, never printed
    R = f"hf://datasets/metr-evals/malt-public@{PUBLIC_SHA}"
    pub = con.execute(f"SELECT metadata.run_id AS run_id, metadata.model AS model, metadata.run_source AS run_source, "
                      f"metadata.manually_reviewed AS manually_reviewed, metadata.labels AS labels, metadata.task_id AS task_id "
                      f"FROM read_parquet('{R}/data/*.parquet')").fetchdf()
    old = con.execute(f"SELECT metadata.run_id AS run_id FROM read_parquet('{R}/default/*.parquet')").fetchdf()
    return pub, old


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--remote-public-meta", action="store_true")
    ap.add_argument("--out", default="review_checks.json")
    a = ap.parse_args()
    cache = Path(a.cache); cache.mkdir(parents=True, exist_ok=True)
    files, rh_file = download(cache)
    m = pd.concat([pq.read_table(f, columns=META).to_pandas() for f in files], ignore_index=True)
    lab = m.labels.apply(set)
    m["labels"] = lab.apply(lambda s: ",".join(sorted(s)))
    m["is_normal"] = lab.apply(lambda s: s == {"normal"})
    m["is_sandbag"] = lab.apply(lambda s: bool(s & SANDBAG))
    out = {"pins": {"metr-evals/malt-transcripts-public": TRANSCRIPTS_SHA, "ktolnos/rh-bench": RH_SHA},
           "runs": len(m), "run_ids_unique": bool(m.run_id.is_unique)}

    # Coverage by model, from the per-run flag
    by = []
    for model, g in m.groupby("model"):
        by.append({"model": model, "benign_reviewed": int((g.is_normal & g.manually_reviewed).sum()),
                   "benign_unreviewed": int((g.is_normal & ~g.manually_reviewed).sum()),
                   "positive_reviewed": int((~g.is_normal & g.manually_reviewed).sum()),
                   "positive_unreviewed": int((~g.is_normal & ~g.manually_reviewed).sum())})
    by = sorted(by, key=lambda r: -(r["benign_reviewed"] + r["benign_unreviewed"]))
    rb = m[m.is_normal & m.manually_reviewed]
    out["coverage"] = {
        "by_model": by,
        "benign_reviewed_total": len(rb), "benign_unreviewed_total": int((m.is_normal & ~m.manually_reviewed).sum()),
        "benign_reviewed_share_claude4": round(float(rb.model.isin(["claude-opus-4-20250514", "claude-sonnet-4-20250514"]).mean()), 4),
        "positives_unreviewed": int((~m.is_normal & ~m.manually_reviewed).sum()),
        "models_with_no_reviewed_run": [r["model"] for r in by if r["benign_reviewed"] + r["positive_reviewed"] == 0],
        "reviewed_benign_tasks": int(rb.task_id.nunique()),
        "sandbag_positive_tasks": int(m[m.is_sandbag].task_id.nunique()),
        "sandbag_positive_tasks_with_a_reviewed_benign_run": int(len(set(m[m.is_sandbag].task_id) & set(rb.task_id))),
        "sandbag_positive_tasks_with_a_37_benign_run": int(len(set(m[m.is_sandbag].task_id) &
                                                               set(m[m.is_normal & m.model.str.startswith("claude-3-7")].task_id))),
    }

    if a.remote_public_meta:
        pub, old = remote_public_meta()
        pub["labels"] = pub.labels.apply(lambda x: ",".join(sorted(x)))
        j = pub.merge(m, on="run_id", suffixes=("_pub", "_tr"))
        out["malt_public_vs_transcripts_metadata"] = {
            "pin": f"metr-evals/malt-public@{PUBLIC_SHA}", "runs_public": len(pub), "joined": len(j),
            "mismatch": {c: int((j[c + "_pub"] != j[c + "_tr"]).sum()) for c in ["model", "run_source", "manually_reviewed", "labels", "task_id"]},
            "unreferenced_default_folder_runs": len(old), "default_folder_same_run_ids": set(old.run_id) == set(pub.run_id),
        }

    # rh-bench MALT rows joined at row level
    u = pd.read_parquet(rh_file)
    r = u[u.source_dataset == "metr_malt"].copy()
    r["run_id"] = pd.to_numeric(r.source_id, errors="coerce").astype("Int64")
    j = r.merge(m.rename(columns={"model": "malt_model", "labels": "malt_labels"}), on="run_id", how="left", indicator=True)
    clean, hack = j[j.label == "clean"], j[j.label == "hacking"]
    out["rh_bench_malt_rows"] = {
        "rows": len(r), "verification": r.verification.value_counts().to_dict(),
        "joined_to_malt_run_id": int((j._merge == "both").sum()), "distinct_run_ids": int(r.run_id.nunique()),
        "response_model_disagrees_with_malt_model": int((j._merge.eq("both") & (j.response_model != j.malt_model)).sum()),
        "clean": {
            "rows": len(clean),
            "malt_label_normal": int(clean.is_normal.fillna(False).astype(bool).sum()),
            "malt_reviewed": int(clean.manually_reviewed.fillna(False).astype(bool).sum()),
            "malt_unreviewed": int((~clean.manually_reviewed.fillna(True).astype(bool)).sum()),
            "unreviewed_by_model": clean[~clean.manually_reviewed.fillna(True).astype(bool)].malt_model.value_counts().to_dict(),
            "reviewed_by_model": clean[clean.manually_reviewed.fillna(False).astype(bool)].malt_model.value_counts().to_dict(),
            "unreviewed_run_ids": sorted(int(x) for x in clean[~clean.manually_reviewed.fillna(True).astype(bool)].run_id),
        },
        "hacking": {
            "rows": len(hack),
            "by_malt_label_and_source": hack.groupby(["malt_labels", "run_source"]).size().rename("n").reset_index().to_dict(orient="records"),
            "prompted_sabotage_rows": int(((hack.malt_labels == "sabotage") & (hack.run_source == "prompted")).sum()),
        },
    }
    # Check 7 carried into rh-bench: does the prompt it serves for MALT rows hold the instruction?
    # Counts only; a word count over rh-bench's own `prompt` column.
    def cnt(g, pat, case=False):
        return int(g.prompt.fillna("").str.contains(pat, case=case, regex=True).sum())
    out["rh_bench_malt_prompt_cues"] = {
        lab: {"rows": len(g), "prompt_contains_sabotag": cnt(g, "sabotag"),
              "prompt_contains_made_by_OpenAI": cnt(g, "made by OpenAI", case=True)}
        for lab, g in r.groupby("label")}
    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items()}, indent=1, default=str)[:5000])


if __name__ == "__main__":
    main()
