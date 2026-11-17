"""L4 step 1: sample items for the minimal-pair intervention (prereg.md, "L4").

Takes two-option items whose key polarity (F1) is Yes or No from four pinned files, shuffles
each file's eligible rows with seed 0 and writes the first 28 per file (20 needed, spares for
items that cannot be negated) to rewrites/candidates.csv with the question stem.

    data/.venv/bin/python -I scripts/l4_sample.py --mwe data/mwe
"""
import argparse, csv, hashlib, json, random, re
from pathlib import Path

FILES = (("human_generated_evals", "coordinate-other-ais"), ("human_generated_evals", "corrigible-neutral-HHH"),
         ("lm_generated_evals", "survival-instinct"), ("lm_generated_evals", "power-seeking-inclination"))
PER_FILE = 28


def options(q):
    parts = re.split(r"\n\s*\(([A-H])\)\s*", "\n" + q.split("Choices:")[-1] if "Choices:" in q else "\n" + q)
    return {parts[i]: parts[i + 1].strip().split("\n")[0].strip() for i in range(1, len(parts) - 1, 2)}


def letter(v):
    v = v[0] if isinstance(v, list) else v
    m = re.search(r"\(([A-H])\)", v)
    return m.group(1) if m else None


def stem(q):
    s = q.split("Choices:")[0] if "Choices:" in q else re.split(r"\n\s*\(A\)", q)[0]
    return s.replace("Question:", "").strip()


def polarity(r):
    o = options(r["question"])
    if len(o) != 2:
        return "O"
    m, nm = o.get(letter(r["answer_matching_behavior"]), ""), o.get(letter(r["answer_not_matching_behavior"]), "")
    y = lambda t: re.match(r"yes\b", t.strip().lower()) is not None
    n = lambda t: re.match(r"no\b", t.strip().lower()) is not None
    return "Y" if y(m) and n(nm) else "N" if n(m) and y(nm) else "O"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mwe", default="data/mwe")
    ap.add_argument("--out", default="rewrites/candidates.csv")
    a = ap.parse_args()
    out = []
    for kind, name in FILES:
        rows = [json.loads(l) for l in (Path(a.mwe) / kind / f"{name}.jsonl").read_text().splitlines() if l.strip()]
        seen, elig = set(), []
        for i, r in enumerate(rows):
            if polarity(r) in "YN" and r["question"] not in seen:
                seen.add(r["question"]); elig.append(i)
        random.Random(0).shuffle(elig)
        for rank, i in enumerate(elig[:PER_FILE]):
            r = rows[i]
            out.append({"id": f"{name}:{i}", "set": kind, "file": name, "row": i, "rank": rank,
                        "key_polarity": polarity(r), "matching_letter": letter(r["answer_matching_behavior"]),
                        "question_sha256_12": hashlib.sha256(r["question"].encode()).hexdigest()[:12],
                        "stem": stem(r["question"])})
        print(name, "eligible", len(elig), "Y", sum(polarity(rows[i]) == "Y" for i in elig))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader(); w.writerows(out)


if __name__ == "__main__":
    main()
