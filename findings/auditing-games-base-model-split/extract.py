"""Download the pinned handover, trial and control logs and write one feature row per sample."""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import LOG_DIRS, eval_files, read_eval, sample_row  # noqa: E402


def build(cache):
    cache = Path(cache)
    out = cache / "features.jsonl"
    if out.exists():
        return [json.loads(l) for l in out.open()]
    rows, headers = [], []
    for name in LOG_DIRS:
        for f in eval_files(cache, name):
            for h, s in read_eval(f):
                rows.append(sample_row(name, h, s))
            e = h["eval"]
            headers.append({"model": name, "file": f.name, "task": e["task"].split("/")[-1],
                            "created": e["created"], "model_path": e["model"],
                            "tool_call_parser": (e.get("model_args") or {}).get("tool_call_parser"),
                            "epochs": e["config"].get("epochs"), "limit": e["config"].get("limit"),
                            "sample_ids": e["dataset"].get("sample_ids"),
                            "dataset_size": e["dataset"].get("samples"),
                            "shuffled": e["dataset"].get("shuffled"),
                            "generate_config": h["plan"].get("config"),
                            "code_commit": (e.get("revision") or {}).get("commit")})
    with out.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    (cache / "headers.json").write_text(json.dumps(headers, indent=1))
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    rows = build(ap.parse_args().cache)
    print(len(rows), "rows")
