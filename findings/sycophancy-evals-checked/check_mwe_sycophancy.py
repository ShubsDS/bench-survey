"""Content-blind baselines, key balance and templating in Anthropic's model-written sycophancy evals.

Perez et al. 2022 (arXiv 2212.09251) release three sycophancy files: a biography stating a view,
then a question; `answer_matching_behavior` is the option that agrees with the biography.
They exist in two places that differ:

- GitHub anthropics/evals at G_SHA (philpapers file fixed on 2023-01-03, commit 1e60395);
- Hugging Face Anthropic/model-written-evals at H_SHA (never updated since 2022-12-21).

This script, at those pins:

1. Compares the two copies by git blob id.
2. Counts base questions, rows per question, distinct biographies and exact duplicates.
3. Scores bio-blind and question-blind policies: always (A), always (B), always "Agree", and the
   best policy that sees the question but not the biography (per-question majority key).
4. Scores two trivial bio-reading rules: the word "disagree" in the biography (NLP survey), and
   "pick the option whose words appear most in the biography" (all three files).
5. Checks key integrity mechanically: NLP-survey biographies that say "I (strongly) agree/disagree
   with the claim" against the key, and political biographies whose affiliation word contradicts
   `user_affiliation`.
6. Checks the hand labels in `mwe_hand_labels.csv` (bio stance vs key, seeded sample) against the
   pinned files by question hash and reports Wilson intervals.

Usage: python check_mwe_sycophancy.py [--cache DIR] [--out mwe_sycophancy_checks.json]
Standard library only. Downloads about 60 MB.
"""
import argparse, collections, csv, hashlib, json, math, random, re, urllib.request
from pathlib import Path

G_SHA = "84fcc677e52e1902d696c32cd1a6b663e70d3993"
H_SHA = "d533f626cc321c92175a58ee570aa3cdb87238d1"
G_URL = f"https://raw.githubusercontent.com/anthropics/evals/{G_SHA}/sycophancy/"
H_URL = f"https://huggingface.co/datasets/Anthropic/model-written-evals/resolve/{H_SHA}/sycophancy/"
FILES = ("sycophancy_on_nlp_survey", "sycophancy_on_philpapers2020", "sycophancy_on_political_typology_quiz")
HERE = Path(__file__).resolve().parent
# Lines whose keys anthropics/evals PR #3 (open, 2026-09-05) swaps as inverted.
PR3_LINES = [28, 84, 118, 962, 1051, 2623, 4202, 4207, 4993, 4996, 5117, 5137, 6012]
STOP = set("a an the of and or to in on for is are be by with as at that this it its from not no than "
           "more less most least all any some only also other there their they he she his her we our".split())


def fetch(url, path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=300) as r:
            path.write_bytes(r.read())
    return path.read_bytes()


def git_blob(b):
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0, c - h), 3), round(min(1, c + h), 3)]


def parse(q):
    """(bio_and_stem, {letter: option text})."""
    q = q.replace("\n\nChoices:\n", "\n")
    body, rest = q.split("\n (A) ", 1)
    opts = dict(re.findall(r"\(([A-Z])\) (.*?)\n", " (A) " + rest))
    return body, opts


def letter(v):
    v = v[0] if isinstance(v, list) else v
    return re.search(r"\(([A-Z])\)", v).group(1)


def base_id(name, q, body, opts):
    if name.endswith("nlp_survey"):
        return re.search(r"as of 2022\? (.*?)\n", q).group(1)
    if name.endswith("philpapers2020"):
        return re.search(r"What is your view on the following topic: (.*?)\n", q).group(1)
    # political: options plus the stem's last words (two option pairs are shared by two stems)
    return " | ".join(sorted(opts.values())) + " || " + body[-30:]


STEMS = {}


def bio_of(name, body):
    if name.endswith("political_typology_quiz"):
        for st in STEMS.get(name, ()):
            if body.endswith(st):
                return body[: -len(st)]
        return body
    if name.endswith("nlp_survey"):
        return body.split(" Do you agree or disagree with the following claim")[0]
    if name.endswith("philpapers2020"):
        return body.split(" What is your view on the following topic:")[0]
    return body


def learn_stems(name, rows):
    """Political stems: longest common suffix of the bodies of one base question, from a sentence start."""
    import os
    g = collections.defaultdict(list)
    for r in rows:
        body, opts = parse(r["question"])
        g[base_id(name, r["question"], body, opts)].append(body)
    stems = []
    for bodies in g.values():
        suf = os.path.commonprefix([b[::-1] for b in bodies])[::-1]
        cut = max(suf.find(". ") + 1, suf.find("! ") + 1, suf.find("? ") + 1, 0) if not suf.startswith(" ") else 0
        stems.append(suf[cut:])
    STEMS[name] = sorted(set(stems), key=len, reverse=True)


def toks(s):
    return [t for t in re.findall(r"[a-z]+", s.lower()) if t not in STOP and len(t) > 2]


def overlap_pick(bio, opts):
    bt = collections.Counter(toks(bio))
    best, score = None, -1
    for L in sorted(opts):
        ot = set(toks(opts[L]))
        s = sum(1 for t in ot if bt[t]) / (len(ot) or 1)
        if s > score:
            best, score = L, s
    return best


def analyse(name, rows):
    if name.endswith("political_typology_quiz"):
        learn_stems(name, rows)
    out = {"rows": len(rows), "exact_duplicate_questions": len(rows) - len({r["question"] for r in rows})}
    keyc = collections.Counter(letter(r["answer_matching_behavior"]) for r in rows)
    out["matching_key_letters"] = dict(sorted(keyc.items()))
    out["n_options"] = dict(sorted(collections.Counter(len(parse(r["question"])[1]) for r in rows).items()))
    per_q = collections.defaultdict(list); bios = collections.Counter()
    for r in rows:
        body, opts = parse(r["question"])
        bid = base_id(name, r["question"], body, opts)
        per_q[bid].append((opts[letter(r["answer_matching_behavior"])], len(opts), r, body, opts))
        bios[bio_of(name, body)] += 1
    out["base_questions"] = len(per_q)
    out["rows_per_base_question"] = dict(sorted(collections.Counter(len(v) for v in per_q.values()).items()))
    out["distinct_biographies"] = len(bios)
    out["biographies_used_more_than_once"] = sum(1 for c in bios.values() if c > 1)
    out["rows_with_a_reused_biography"] = sum(c for c in bios.values() if c > 1)
    # bio-blind ceiling: best per-question constant answer (by option text)
    best = sum(max(collections.Counter(t for t, *_ in v).values()) for v in per_q.values())
    out["bio_blind_best_per_question"] = round(best / len(rows), 4)
    out["chance_mean_1_over_k"] = round(sum(1 / len(parse(r["question"])[1]) for r in rows) / len(rows), 4)
    unbalanced = [k for k, v in per_q.items() if len(set(collections.Counter(t for t, *_ in v).values())) > 1
                  or len(collections.Counter(t for t, *_ in v)) < v[0][1]]
    out["base_questions_with_unbalanced_keys"] = len(unbalanced)
    out["always_A"] = round(keyc["A"] / len(rows), 4)
    out["always_B"] = round(keyc["B"] / len(rows), 4)
    # trivial bio-reading rule: most option words found in the biography
    hit = sum(overlap_pick(bio_of(name, b), o) == letter(r["answer_matching_behavior"])
              for v in per_q.values() for _, _, r, b, o in v)
    out["rule_option_word_overlap"] = round(hit / len(rows), 4)
    if name.endswith("nlp_survey"):
        agree = sum(o[letter(r["answer_matching_behavior"])] == "Agree" for v in per_q.values() for _, _, r, _, o in v)
        out["always_Agree"] = round(agree / len(rows), 4)
        dis = sum((("Disagree" if re.search(r"\bdisagree", bio_of(name, b), re.I) else "Agree")
                   == o[letter(r["answer_matching_behavior"])]) for v in per_q.values() for _, _, r, b, o in v)
        out["rule_disagree_word"] = round(dis / len(rows), 4)
        # explicit meta-statements about the claim, against the key
        pat = re.compile(r"\bI (?:strongly |firmly |completely |wholeheartedly |would |tend to |somewhat )?"
                         r"(agree|disagree) with (?:the )?(?:claim|statement)", re.I)
        n_meta = contra = 0; contra_lines = []
        for i, r in enumerate(rows):
            body, o = parse(r["question"])
            m = pat.findall(bio_of(name, body))
            if len(set(x.lower() for x in m)) == 1:
                n_meta += 1
                said = "Agree" if m[0].lower() == "agree" else "Disagree"
                if said != o[letter(r["answer_matching_behavior"])]:
                    contra += 1; contra_lines.append(i + 1)
        out["explicit_meta_statement_rows"] = n_meta
        out["explicit_meta_statement_against_key"] = contra
        out["explicit_meta_statement_against_key_lines"] = contra_lines
        out["pr3_lines"] = PR3_LINES
        out["against_key_found_here_not_in_pr3"] = sorted(set(contra_lines) - set(PR3_LINES))
        out["pr3_lines_not_found_by_this_regex"] = sorted(set(PR3_LINES) - set(contra_lines))
        out["union_known_inverted"] = len(set(contra_lines) | set(PR3_LINES))
    if name.endswith("philpapers2020"):
        split = collections.defaultdict(lambda: collections.Counter())
        for v in per_q.values():
            for t, _, r, _, o in v:
                if any(x.count("(") != x.count(")") for x in o.values()):
                    split[re.search(r"following topic: (.*?)\n", r["question"]).group(1)][t] += 1
        out["topics_with_split_options"] = {k: dict(c) for k, c in split.items()}
        out["rows_on_split_option_topics"] = sum(sum(c.values()) for c in split.values())
    if name.endswith("political_typology_quiz"):
        aff = collections.Counter(r["user_affiliation"] for r in rows)
        out["user_affiliation"] = dict(aff)
        lib = re.compile(r"\b(liberal|progressive|democrat)", re.I); con = re.compile(r"\b(conservative|republican)", re.I)
        word = collections.Counter()
        for r in rows:
            b = bio_of(name, parse(r["question"])[0])
            w = "liberal" if lib.search(b) and not con.search(b) else "conservative" if con.search(b) and not lib.search(b) else "none_or_both"
            word[(w, r["user_affiliation"])] += 1
        out["affiliation_word_vs_field"] = {f"{a}|{b}": c for (a, b), c in sorted(word.items())}
        # the key is a function of (question, affiliation): check
        f = collections.defaultdict(set)
        for v in per_q.values():
            for t, _, r, _, _ in v:
                f[(id(v), r["user_affiliation"])].add(t)
        out["key_is_function_of_question_and_affiliation"] = all(len(s) == 1 for s in f.values())
        out["distinct_question_affiliation_cells"] = len(f)
    return out, per_q


def check_hand_labels(path, files):
    if not path.exists():
        return None
    res = collections.defaultdict(collections.Counter); bad = 0
    for row in csv.DictReader(open(path)):
        rows = files[row["file"]]
        r = rows[int(row["line"]) - 1]
        if hashlib.sha256(r["question"].encode()).hexdigest()[:10] != row["qhash"]:
            bad += 1; continue
        res[row["file"]][row["label"]] += 1
    out = {"hash_mismatches": bad}
    for f, c in res.items():
        n = sum(c.values()); k = n - c.get("ok", 0)
        out[f] = {"labels": dict(c), "n": n, "not_ok": k, "wilson95": wilson(k, n),
                  "against_key": c.get("against_key", 0), "wilson95_against": wilson(c.get("against_key", 0), n)}
    return out


def sample_lines(name, n, seed):
    rng = random.Random(f"{name}-{seed}")
    return sorted(rng.sample(range(1, (9984 if "nlp" in name else 9867) + 1), n))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data"); ap.add_argument("--out", default=str(HERE / "mwe_sycophancy_checks.json"))
    a = ap.parse_args(); cache = Path(a.cache)
    out = {"pins": {"github_anthropics_evals": G_SHA, "huggingface_model_written_evals": H_SHA}, "copies": {}, "files": {}}
    files = {}
    for name in FILES:
        g = fetch(G_URL + name + ".jsonl", cache / "github" / f"{name}.jsonl")
        h = fetch(H_URL + name + ".jsonl", cache / "hf" / f"{name}.jsonl")
        out["copies"][name] = {"github_blob": git_blob(g), "github_bytes": len(g), "hf_blob": git_blob(h), "hf_bytes": len(h)}
        files[name] = [json.loads(l) for l in g.decode().splitlines() if l.strip()]
    c = out["copies"]
    out["hf_philpapers_is_copy_of_hf_nlp_survey"] = c["sycophancy_on_philpapers2020"]["hf_blob"] == c["sycophancy_on_nlp_survey"]["hf_blob"]
    out["github_philpapers_differs_from_hf"] = c["sycophancy_on_philpapers2020"]["github_blob"] != c["sycophancy_on_philpapers2020"]["hf_blob"]
    for name in FILES:
        out["files"][name], _ = analyse(name, files[name])
    out["hand_labels"] = check_hand_labels(HERE / "mwe_hand_labels.csv", files)
    out["hand_label_sample_lines"] = {n: sample_lines(n, 30, 0) for n in FILES[:2]}
    labelled = collections.defaultdict(list)
    for row in csv.DictReader(open(HERE / "mwe_hand_labels.csv")):
        labelled[row["file"]].append(int(row["line"]))
    out["hand_labels_are_seeded_sample"] = {n: sorted(labelled[n]) == out["hand_label_sample_lines"][n] for n in FILES[:2]}
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1)[:6000])


if __name__ == "__main__":
    main()
