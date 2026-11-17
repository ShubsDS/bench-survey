"""Shared loading for the SAD checks: pinned clone, extraction with the published password,
loaders for the multiple-choice tasks, Wilson interval, near-duplicate clustering.

SAD ships its questions in encrypted zips to keep them out of training corpora. The password is
published in the repo's own unzip.sh for that purpose; this module reads it from there and calls
the system `unzip`. Nothing from the repo is executed. Extracted text stays in the cache directory;
outputs hold aggregates and sample ids only.
"""
import hashlib, math, re, subprocess
from collections import defaultdict
from pathlib import Path

import yaml

REPO = "https://github.com/LRudL/sad.git"
SHA = "dfc5c9831a9bcc5c9a9dbdcaa2955aae983cd1d3"  # main, 2024-12-14
Y = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

ZIPS = ["sad/facts/human_defaults/structs.zip", "sad/facts/llms/structs.zip",
        "sad/facts/which_llm/structs.zip", "sad/facts/which_llm/raw_data.zip",
        "sad/influence/structs.zip", "sad/stages/full/structs.zip",
        "sad/stages/oversight/structs.zip", "sad/self_recognition/evals.zip",
        "sad/facts/human_defaults/evals.zip", "sad/facts/llms/evals.zip",
        "sad/facts/which_llm/evals.zip", "sad/influence/evals.zip",
        "sad/stages/full/evals.zip", "sad/stages/oversight/evals.zip"]

# Per-task chance as SAD's code sets it (Task(..., random_chance)); invalid answers get this credit.
CHANCE = {"facts_human_defaults": 0.5, "facts_llms": 0.5, "facts_which_llm": 0.5,
          "influence": 0.5, "stages_full": 0.25, "stages_oversight": 0.5,
          "self_recognition_who": 0.5, "self_recognition_groups": 0.5}

PILES = {"facts_human_defaults": "sad/facts/human_defaults/structs/pile/facts_human_defaults.yaml",
         "facts_llms": "sad/facts/llms/structs/pile/facts_llms.yaml",
         "influence": "sad/influence/structs/pile/influence.yaml",
         "stages_full": "sad/stages/full/structs/pile/stages.yaml",
         "stages_oversight": "sad/stages/oversight/structs/pile/oversight.yaml"}


def ensure(cache):
    """Clone SAD at SHA into cache/repo if absent, and extract the zips used here into cache/unz."""
    cache = Path(cache)
    repo = cache / "repo"
    if not repo.exists():
        subprocess.run(["git", "clone", "-q", "--no-checkout", REPO, str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "-c", "core.hooksPath=/dev/null", "checkout", "-q", SHA], check=True)
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if head != SHA:
        raise SystemExit(f"{repo} is at {head}, not the pinned {SHA}")
    pw = re.search(r'^PASSWORD="([^"]+)"', (repo / "unzip.sh").read_text(), re.M).group(1)
    unz = cache / "unz"
    hashes = {}
    for z in ZIPS:
        src = repo / z
        hashes[z] = hashlib.sha256(src.read_bytes()).hexdigest()
        dst = unz / z[:-4]
        if not dst.exists():
            dst.mkdir(parents=True)
            subprocess.run(["unzip", "-q", "-P", pw, "-o", str(src), "-d", str(dst)], check=True)
    return unz, hashes


def _load(path):
    return yaml.load(Path(path).read_text(), Loader=Y)


def mcq_task(unz, task):
    """Items of one pile as dicts {task, batch, id, q, right, wrong, splits}."""
    pf = Path(unz) / PILES[task]
    out = []
    for b in _load(pf)["batches"]:
        for s in _load(pf.parent.parent / "batch" / f"{b}.yaml")["samples"]:
            out.append({"task": task, "batch": b, "id": s["id"], "q": s["body"],
                        "right": list(s["choices_right"]), "wrong": list(s["choices_wrong"]),
                        "splits": s.get("splits") or {}})
    return out


PANDAS_NA = {"", "#N/A", "#N/A N/A", "#NA", "-1.#IND", "-1.#QNAN", "-NaN", "-nan", "1.#IND", "1.#QNAN",
             "<NA>", "N/A", "NA", "NULL", "NaN", "None", "n/a", "nan", "null"}


def which_llm_models(unz):
    import csv
    with open(Path(unz) / "sad/facts/which_llm/raw_data/data.csv", newline="") as f:
        cols = next(csv.reader(f))
    return [c[:-len(" correct")] for c in cols if c.endswith(" correct")]


def which_llm(unz, pov="2nd-person"):
    """The per-model batches the task runs (plain variant uses 2nd-person). Each item also carries
    `row`, its question's row in raw_data/data.csv, matched by question text."""
    import csv
    with open(Path(unz) / "sad/facts/which_llm/raw_data/data.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    qcol = f"question_{pov}"
    out = {}
    for m in which_llm_models(unz):
        name = m.replace(".", "_")
        p = Path(unz) / f"sad/facts/which_llm/structs/batch/{name}--{pov}.yaml"
        if not p.exists():
            continue
        items = []
        for s in _load(p)["samples"]:
            items.append({"task": "facts_which_llm", "batch": name, "id": s["id"], "q": s["body"],
                          "right": list(s["choices_right"]), "wrong": list(s["choices_wrong"]), "splits": {}})
        # attach the csv row: match on question text plus this model's keyed answer, in csv order
        cand = defaultdict(list)
        for i, r in enumerate(rows):
            q = (r[qcol] or "")
            if pov.startswith("3"):
                q = q.replace("{{model}}", m)
            key = (r[f"{m} correct"] or "").strip()
            # the repo's preprocessing reads the csv with pandas, which turns "None", "NA" etc. into
            # NaN and then fillna("") into an empty choice; mirror that so the rows still match
            if key in PANDAS_NA:
                key = ""
            cand[(q.strip(), key)].append(i)
        for it in items:
            lst = cand.get((it["q"].strip(), it["right"][0].strip()))
            it["row"] = lst.pop(0) if lst else None
            it["subset"] = rows[it["row"]]["subset"] if it["row"] is not None else None
        out[m] = items
    return out, rows


def evalresults(unz, zipdir, prefix):
    """Paths of released eval results under one task's extracted evals.zip matching a prefix."""
    d = Path(unz) / zipdir / "evals"
    return sorted(p for p in d.rglob("*.yaml") if p.name.startswith(prefix))


def load_evalresult(path):
    return _load(path)


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    c = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    mid = (p + z * z / (2 * n)) / (1 + z * z / n)
    return [round(mid - c, 3), round(mid + c, 3)]


def acc(hit, n):
    return {"n": n, "accuracy": round(hit / n, 3) if n else None,
            "wilson_95": wilson(round(hit), n) if n else None}


def norm(t):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", t.lower())).strip()


def shingles(t, k=3):
    w = norm(t).split()
    return {" ".join(w[i:i + k]) for i in range(max(1, len(w) - k + 1))} if w else set()


def jaccard(a, b):
    return len(a & b) / len(a | b) if a | b else 0.0


def near_pairs(texts, thr=0.5, k=3):
    """Pairs (i, j, jaccard) with 3-shingle Jaccard >= thr, via an inverted index on shingles."""
    sh = [shingles(t, k) for t in texts]
    inv = defaultdict(list)
    for i, s in enumerate(sh):
        for g in s:
            inv[g].append(i)
    out = []
    for i, s in enumerate(sh):
        cand = defaultdict(int)
        for g in s:
            lst = inv[g]
            if len(lst) > 400:  # very common shingle; skip as a candidate source
                continue
            for j in lst:
                if j > i:
                    cand[j] += 1
        for j, c in cand.items():
            if c / max(1, min(len(s), len(sh[j]))) < thr:
                continue
            jj = jaccard(s, sh[j])
            if jj >= thr:
                out.append((i, j, jj))
    return out


def clusters(texts, thr=0.5):
    """Union-find group label per text, joining near-duplicates (Jaccard >= thr) and exact copies."""
    par = list(range(len(texts)))

    def f(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    seen = {}
    for i, t in enumerate(texts):
        h = norm(t)
        if h in seen:
            par[f(i)] = f(seen[h])
        else:
            seen[h] = i
    for i, j, _ in near_pairs(texts, thr):
        par[f(i)] = f(j)
    return [f(i) for i in range(len(texts))]
