"""Reproduce the Impossible-SWEbench missing-file bug: mutated test patches drop files the original creates.

ImpossibleBench builds each impossible SWE-bench task (gen/swebench_mutate.py) by applying the
original test patch with `git apply`, having a model edit one test file, and saving `git diff` as
the new test patch. `git diff` leaves out untracked files, so any file the original patch created
(a new test module, a fixture, a rename target) is missing from the mutated patch, and the harness
applies only the mutated patch. This script downloads the three splits at a pinned revision and
lists the tasks affected, and whether the mutated patch still refers to the missing file. It reads
patches as text and never applies or runs them.

Usage:
    python check_missing_files.py [--cache DIR] [--out missing_files.json]
"""
import argparse, json, re, urllib.request
from pathlib import Path

import pandas as pd

REVISION = "9c2d34f364b7229e8c0ff807c646100bdc18bbb5"
SPLITS = {s: ("https://huggingface.co/datasets/fjzzq2002/impossible_swebench/resolve/"
              f"{REVISION}/data/{s}-00000-of-00001.parquet")
          for s in ("original", "oneoff", "conflicting")}
IMPOSSIBLEBENCH = "d4f9a149db2b9cec0fed7bab01d91c07ee10aca2"


def fetch(url, cache):
    path = cache / url.rsplit("/", 1)[1]
    if not path.exists():
        with urllib.request.urlopen(url, timeout=300) as r:
            path.write_bytes(r.read())
    return path


def created(patch):
    """Paths a patch brings into existence: new files and rename targets."""
    out = set()
    for block in re.split(r"(?m)^(?=diff --git )", patch)[1:]:
        b = re.match(r"diff --git a/\S+ b/(\S+)", block).group(1)
        if re.search(r"(?m)^new file mode", block):
            out.add(b)
        rename = re.search(r"(?m)^rename to (\S+)", block)
        if rename:
            out.add(rename.group(1))
    return out


GENERIC = {"conf", "index", "foo", "baz", "text", "__main__", "0001_initial"}


def name(path):
    """How a test refers to a file: its stem, or for generic stems its directory (sphinx test
    roots are named without the 'test-' prefix, migrations by their package)."""
    p = Path(path)
    return p.stem if p.stem not in GENERIC else p.parent.name.removeprefix("test-")


def touched(patch):
    return (set(re.findall(r"(?m)^\+\+\+ b/(\S+)", patch))
            | set(re.findall(r"(?m)^diff --git a/\S+ b/(\S+)", patch)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="missing_files.json")
    args = ap.parse_args()
    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    df = {s: pd.read_parquet(fetch(u, cache)).set_index("instance_id") for s, u in SPLITS.items()}

    orig = df["original"]
    makes = {i: created(orig.loc[i, "original_test_patch"]) for i in orig.index}
    result = {"pins": {"dataset_revision": REVISION, "impossiblebench_commit": IMPOSSIBLEBENCH},
              "tasks": len(orig),
              "original_patches_creating_a_file": sorted(i for i, v in makes.items() if v)}
    for split in ("oneoff", "conflicting"):
        rows = {}
        for i in df[split].index:
            patch = df[split].loc[i, "test_patch"]
            missing = sorted(makes[i] - touched(patch))
            if missing:
                rows[i] = {"missing": missing,
                           "mutated_patch_names_missing_file": any(name(p) in patch for p in missing)}
        result[split] = {"tasks_missing_a_file": len(rows), "by_task": rows}
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: v if k not in ("oneoff", "conflicting") else
                      {"tasks_missing_a_file": v["tasks_missing_a_file"],
                       "mutated_patch_names_missing_file": sum(r["mutated_patch_names_missing_file"]
                                                               for r in v["by_task"].values())}
                      for k, v in result.items()}, indent=1))


if __name__ == "__main__":
    main()
