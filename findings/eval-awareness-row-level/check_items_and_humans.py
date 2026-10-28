"""Evaluation-awareness benchmark (Needham et al. 2025): duplicates, benchmark formats, human labels.

Leads 5 and 6 of the audit, on the released rows.

  5  Exact duplicates (normalised full transcript; normalised first user turn) and near-duplicates
     (word 5-gram Jaccard over the first user turn and over the transcript), counted within a source,
     across sources of one class, across classes, and across the paper's PQ-selection split
     (pqsel) and its held-out rows. String matches for a few published-benchmark prompt formats,
     per class. Fields that only the storage format carries (message source/function/error keys,
     tool-call views) and whether the sample id names its source.
  6  The two human annotators' probabilities (eval_author1, eval_author2): AUROC by split, agreement
     between them, accuracy against the class label by source, and how much of each score (human
     and model) is explained by the source alone.

The dataset is gated and encrypted. It is fetched with `hf download` at a pinned revision (the
caller must have accepted the gate), checked against a pinned sha256, and decrypted with the
password the authors publish in the repository's scripts/decrypt.sh. No downloaded code is run.
Outputs hold aggregates, counts, source names and sample ids only, never transcript text.

Usage: python -I check_items_and_humans.py [--cache data] [--out items_and_humans_checks.json]
"""
import argparse, collections, hashlib, itertools, json, re, shutil, subprocess, zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

HF_REPO = "jjpn2/eval_awareness"
HF_SHA = "5d724f12988284a652749c56ec7b2356b0d14408"
ZIP_SHA256 = "934dc4bc83b76e6bc57e672c39716061204b4802bb46b2038e7feb822aaa211c"

FORMATS = {
    "canary_string": re.compile(r"canary GUID|BENCHMARK DATA SHOULD NEVER APPEAR", re.I),
    "mmlu_header": re.compile(r"The following are multiple choice questions", re.I),
    "choices_block": re.compile(r"(?m)^\s*Choices:\s*$"),
    "multiple_choice_options": re.compile(r"(?ms)^\s*\(?[Aa][\).:]\s+\S.*?^\s*\(?[Bb][\).:]\s+\S"),
    "answer_prompt_line": re.compile(r"(?m)^\s*Answer:\s*$"),
    "ctf_flag_format": re.compile(r"\b(?:flag|picoCTF|HTB|CTF)\{", re.I),
    "capture_the_flag": re.compile(r"capture the flag", re.I),
    "swe_issue_tag": re.compile(r"<(?:issue|pr_description)>"),
    "uploaded_repository": re.compile(r"uploaded a python code repository", re.I),
    "exercism": re.compile(r"exercism", re.I),
}


def fetch(cache, hf_bin):
    hf = cache / "hf"
    if not (hf / "dataset.zip").exists():
        subprocess.run([hf_bin, "download", HF_REPO, "--repo-type", "dataset", "--revision", HF_SHA,
                        "--local-dir", str(hf)], check=True)
    h = hashlib.sha256((hf / "dataset.zip").read_bytes()).hexdigest()
    if h != ZIP_SHA256:
        raise SystemExit(f"dataset.zip sha256 {h} != pinned {ZIP_SHA256}")
    ex = cache / "extracted"
    if not (ex / "dataset.json").exists():
        pw = re.search(r'^PW="([^"]+)"', (hf / "scripts" / "decrypt.sh").read_text(), re.M).group(1)
        with zipfile.ZipFile(hf / "dataset.zip") as z:
            for n in z.namelist():
                if n.startswith("/") or ".." in Path(n).parts:
                    raise SystemExit(f"unsafe path in zip: {n}")
            z.extractall(ex, pwd=pw.encode())
    return json.loads((ex / "dataset.json").read_text()), ex / "mcq_transcripts"


def mcq_id(sid):
    s = sid.replace("giles_claude:", "author_claude:").replace("govind_runs:", "gaia_runs:")
    return s.replace("mvp:giles_", "mvp:author2_").replace("mvp:joe_", "mvp:author1_")


def text_of(c):
    return c if isinstance(c, str) else "".join(p.get("text", "") for p in c if isinstance(p, dict))


def visible_text(x):
    parts = []
    for m in x["input"]:
        parts.append(text_of(m["content"]))
        for t in m.get("tool_calls") or []:
            parts.append(str(t.get("function", "")) + " " + json.dumps(t.get("arguments", {}), sort_keys=True))
    return "\n".join(parts)


def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def shingles(s, k=5, cap=20000):
    w = re.findall(r"\w+", s.lower()[:cap])
    return {" ".join(w[i:i + k]) for i in range(max(len(w) - k + 1, 1))} if w else set()


def jaccard_pairs(sets, thr):
    vocab = {}
    rows, cols = [], []
    for i, s in enumerate(sets):
        for h in s:
            rows.append(i); cols.append(vocab.setdefault(h, len(vocab)))
    M = sparse.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(sets), len(vocab)))
    inter = (M @ M.T).tocoo()
    size = np.array([len(s) for s in sets])
    out = []
    for i, j, v in zip(inter.row, inter.col, inter.data):
        if i < j and size[i] and size[j]:
            jac = v / (size[i] + size[j] - v)
            if jac >= thr:
                out.append((int(i), int(j), float(jac)))
    return out


def classify_pairs(pairs, meta):
    c = collections.Counter(); ex = collections.defaultdict(list)
    for i, j, _ in pairs:
        a, b = meta[i], meta[j]
        kind = ("same_source" if a["source"] == b["source"] else
                "cross_source_same_class" if a["y"] == b["y"] else "cross_class")
        c[kind] += 1
        if a["pqsel"] != b["pqsel"]:
            c["across_pqsel_split"] += 1
        if kind != "same_source":
            ex[kind].append(tuple(sorted((a["source"], b["source"]))))
    return {"pairs": dict(c), "source_pairs": {k: dict(collections.Counter(f"{p[0]} | {p[1]}" for p in v))
                                               for k, v in ex.items()}}


def dup_groups(keys, meta):
    groups = collections.defaultdict(list)
    for i, k in enumerate(keys):
        if k:
            groups[k].append(i)
    c = collections.Counter(); rows_in = 0; cross = []
    for k, idx in groups.items():
        if len(idx) < 2:
            continue
        rows_in += len(idx); c["groups"] += 1
        srcs = {meta[i]["source"] for i in idx}; ys = {meta[i]["y"] for i in idx}
        c["groups_within_one_source" if len(srcs) == 1 else
          "groups_across_sources_same_class" if len(ys) == 1 else "groups_across_classes"] += 1
        if len({meta[i]["pqsel"] for i in idx}) > 1:
            c["groups_across_pqsel_split"] += 1
        if len(srcs) > 1:
            cross.append(" | ".join(sorted(srcs)))
    return {**dict(c), "rows_in_groups": rows_in, "cross_source_groups": dict(collections.Counter(cross))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="items_and_humans_checks.json")
    ap.add_argument("--hf", default=shutil.which("hf") or str(Path.home() / ".local/bin/hf"))
    a = ap.parse_args()
    samples, mcq_dir = fetch(Path(a.cache), a.hf)
    res = {"pins": {"hf": f"{HF_REPO}@{HF_SHA}", "dataset_zip_sha256": ZIP_SHA256, "paper": "arXiv:2505.23836v3"}}

    meta = [{"id": x["id"], "source": x["metadata"]["category"], "y": int(bool(x["metadata"]["eval_category"])),
             "agentic": x["metadata"]["scaffold"] is not None, "pqsel": bool(x["metadata"]["pqsel"])} for x in samples]
    cell = lambda m: f"{'agentic' if m['agentic'] else 'chat'}-{'evaluation' if m['y'] else 'deployment'}"
    full = [visible_text(x) for x in samples]
    first_user = [next((text_of(m["content"]) for m in x["input"] if m["role"] == "user"), "") for x in samples]

    # ---- release vs paper
    cells = collections.Counter(cell(m) for m in meta)
    res["release_counts"] = {"rows": len(samples), "by_cell": dict(cells),
                             "sources": len({m["source"] for m in meta}),
                             "pqsel_rows": sum(m["pqsel"] for m in meta),
                             "paper_tables_by_cell": {"chat-evaluation": 287, "agentic-evaluation": 250,
                                                      "chat-deployment": 213, "agentic-deployment": 250},
                             "paper_sources_listed_not_released": ["irl_cursor"] if not any(
                                 m["source"] == "irl_cursor" for m in meta) else []}

    # ---- 5: exact duplicates
    hfull = [hashlib.sha1(norm(t).encode()).hexdigest() for t in full]
    hfirst = [hashlib.sha1(norm(t).encode()).hexdigest() if norm(t) else None for t in first_user]
    res["5_exact_duplicates"] = {"full_transcript": dup_groups(hfull, meta), "first_user_turn": dup_groups(hfirst, meta)}
    sys_h = [hashlib.sha1(text_of(x["input"][0]["content"]).encode()).hexdigest() for x in samples]
    shared_sys = {}
    for h in set(sys_h):
        idx = [i for i, k in enumerate(sys_h) if k == h]
        ys = collections.Counter(meta[i]["y"] for i in idx)
        if len(ys) == 2:
            shared_sys[h[:10]] = {"evaluation": ys[1], "deployment": ys[0],
                                  "setting": sorted({cell(meta[i]).split("-")[0] for i in idx}),
                                  "sources": dict(collections.Counter(meta[i]["source"] for i in idx))}
    res["5_system_prompts_shared_across_classes"] = shared_sys

    # ---- 5: near duplicates
    near = {}
    for name, texts in (("first_user_turn", first_user), ("full_transcript", full)):
        sets = [shingles(t) for t in texts]
        for thr in (0.8, 0.5):
            near[f"{name}_jaccard_ge_{thr}"] = classify_pairs(jaccard_pairs(sets, thr), meta)
        # same, after dropping boilerplate: shingles found in 10 or more samples (scaffold templates)
        df_ = collections.Counter(s for st in sets for s in st)
        nb = [{s for s in st if df_[s] < 10} for st in sets]
        for thr in (0.8, 0.5):
            near[f"{name}_no_boilerplate_jaccard_ge_{thr}"] = classify_pairs(jaccard_pairs(nb, thr), meta)
    res["5_near_duplicates_word5gram"] = near

    # ---- 5: published-benchmark formats by string match
    fm = {}
    for k, rx in FORMATS.items():
        hit = [bool(rx.search(t)) for t in full]
        by_cell = collections.Counter(cell(m) for m, h in zip(meta, hit) if h)
        by_src = collections.Counter(m["source"] for m, h in zip(meta, hit) if h)
        fm[k] = {"by_cell": {c: f"{by_cell.get(c, 0)}/{cells[c]}" for c in sorted(cells)},
                 "sources": dict(sorted(by_src.items(), key=lambda t: -t[1]))}
    named = ["ctf_flag_format", "capture_the_flag", "swe_issue_tag", "uploaded_repository", "exercism"]
    anyhit = [any(FORMATS[k].search(t) for k in named) for t in full]
    by_cell = collections.Counter(cell(m) for m, h in zip(meta, anyhit) if h)
    fm["any_named_benchmark_string"] = {"patterns": named,
                                        "by_cell": {c: f"{by_cell.get(c, 0)}/{cells[c]}" for c in sorted(cells)}}
    res["5_benchmark_format_matches"] = fm

    # ---- 5: label readable from ids and storage-only fields
    res["5_ids_and_storage_fields"] = {
        "id_prefix_equals_source": sum(x["id"].split(":")[0] == x["metadata"]["category"] for x in samples),
        "rows": len(samples),
        "rows_with_storage_only_keys_by_cell": dict(collections.Counter(
            cell(m) for x, m in zip(samples, meta)
            if any(k in msg for msg in x["input"] for k in ("source", "function", "error"))
            or any("view" in t for msg in x["input"] for t in (msg.get("tool_calls") or [])))),
        "note": "keys: message source/function/error and tool-call view; the paper's quote format drops id and "
                "source but keeps function; the five probe questions used append (messages passed natively)",
    }

    # ---- 6: human labels
    df = pd.DataFrame(meta)
    df["h1"] = [x["metadata"]["eval_author1"] for x in samples]
    df["h2"] = [x["metadata"]["eval_author2"] for x in samples]
    df["hm"] = (df.h1 + df.h2) / 2
    model = {}
    for f in sorted(mcq_dir.glob("*.csv")):
        m = pd.read_csv(f, usecols=["model", "sample_id", "score", "joe", "giles"])
        m["id"] = m.sample_id.map(mcq_id)
        model[m.model.iloc[0]] = m.groupby("id").score.mean()
        jg = m.groupby("id")[["joe", "giles"]].first()
    chk = df.set_index("id").join(jg, how="inner")
    hum = {"mcq_files_human_columns_match_dataset": bool(np.allclose(chk.h1, chk.joe) and np.allclose(chk.h2, chk.giles)),
           "rows_compared": int(len(chk))}
    for rows_name, rows in (("held_out", ~df.pqsel), ("all_released", df.pqsel | ~df.pqsel)):
        for sp, msk in (("chat", ~df.agentic), ("agentic", df.agentic), ("all", df.agentic | ~df.agentic)):
            d = df[rows & msk]
            hum[f"auroc_{rows_name}_{sp}"] = {k: round(float(roc_auc_score(d.y, d[k])), 3) for k in ("h1", "h2", "hm")}
    side = lambda v: np.where(v > 0.5, 1, np.where(v < 0.5, 0, -1))
    s1, s2 = side(df.h1.values), side(df.h2.values)
    both = (s1 >= 0) & (s2 >= 0)
    hum["inter_annotator"] = {"spearman": round(float(spearmanr(df.h1, df.h2).statistic), 3),
                              "pearson": round(float(np.corrcoef(df.h1, df.h2)[0, 1]), 3),
                              "same_side_of_0.5": f"{int((s1 == s2)[both].sum())}/{int(both.sum())}",
                              "rows_at_exactly_0.5": {"h1": int((s1 < 0).sum()), "h2": int((s2 < 0).sum())}}
    acc = lambda v, y: np.mean(np.where(v == 0.5, 0.5, (v > 0.5) == (y == 1)))
    by_src = []
    for s, d in df.groupby("source"):
        row = {"source": s, "class": "evaluation" if d.y.iloc[0] else "deployment",
               "setting": "agentic" if d.agentic.iloc[0] else "chat", "n": int(len(d)),
               "acc_h1": round(float(acc(d.h1.values, d.y.values)), 3), "acc_h2": round(float(acc(d.h2.values, d.y.values)), 3),
               "mean_p_eval_h1": round(float(d.h1.mean()), 3), "mean_p_eval_h2": round(float(d.h2.mean()), 3)}
        held = d[~d.pqsel]
        accs = [acc(held.id.map(sv).values, held.y.values) for sv in model.values() if len(held)]
        row["acc_models_mean_held_out"] = round(float(np.mean(accs)), 3) if accs else None
        by_src.append(row)
    by_src.sort(key=lambda r: (r["acc_h1"] + r["acc_h2"]) / 2)
    hum["by_source"] = by_src
    hum["sources_where_both_annotators_acc_ge_0.9"] = sum(r["acc_h1"] >= 0.9 and r["acc_h2"] >= 0.9 for r in by_src)
    hum["sources_where_mean_annotator_acc_lt_0.5"] = [r["source"] for r in by_src if (r["acc_h1"] + r["acc_h2"]) / 2 < 0.5]
    hum["rows_correct_side"] = {k: round(float(acc(df[k].values, df.y.values)), 3) for k in ("h1", "h2", "hm")}

    # how much of each score is the source: eta^2 and AUROC after replacing each row by its source mean
    def eta2(v, g):
        v = pd.Series(v); gm = v.groupby(g).transform("mean")
        return float(((gm - v.mean()) ** 2).sum() / ((v - v.mean()) ** 2).sum())
    held = df[~df.pqsel].reset_index(drop=True)
    src_share = {}
    scores = {"human_mean": held.hm, **{k: held.id.map(v) for k, v in model.items()}}
    for k, v in scores.items():
        ok = v.notna().values
        hh = held[ok]; vv = v[ok].values
        sm = pd.Series(vv).groupby(hh.source.values).transform("mean").values
        out = {}
        for sp, msk in (("chat", ~hh.agentic.values), ("agentic", hh.agentic.values)):
            out[sp] = {"eta2_source": round(eta2(vv[msk], hh.source.values[msk]), 3),
                       "auroc_raw": round(float(roc_auc_score(hh.y.values[msk], vv[msk])), 3),
                       "auroc_source_mean": round(float(roc_auc_score(hh.y.values[msk], sm[msk])), 3)}
        src_share[k] = out
    hum["score_explained_by_source_held_out"] = src_share
    res["6_human_labels"] = hum

    # ---- 5: intervals. Rows of one source are not independent draws; compare the paper's row-level
    # Hanley-McNeil interval with a bootstrap over sources, and test model differences paired by source.
    def hanley(auc, n1, n2):
        q1 = auc / (2 - auc); q2 = 2 * auc ** 2 / (1 + auc)
        se = np.sqrt((auc * (1 - auc) + (n1 - 1) * (q1 - auc ** 2) + (n2 - 1) * (q2 - auc ** 2)) / (n1 * n2))
        return [round(float(auc - 1.96 * se), 3), round(float(auc + 1.96 * se), 3)]
    rng = np.random.default_rng(0)
    names = list(model)
    iv = {}
    for sp, msk in (("chat", ~held.agentic.values), ("agentic", held.agentic.values), ("all", np.ones(len(held), bool))):
        d = held[msk].reset_index(drop=True)
        S = np.column_stack([d.id.map(model[k]).values for k in names])
        ok = ~np.isnan(S).any(1); d = d[ok].reset_index(drop=True); S = S[ok]
        y = d.y.values; gs = d.source.unique(); idx = {g: np.where(d.source.values == g)[0] for g in gs}
        boots = []
        for _ in range(1000):
            t = np.concatenate([idx[g] for g in rng.choice(gs, len(gs))])
            if len(np.unique(y[t])) == 2:
                boots.append([roc_auc_score(y[t], S[t, j]) for j in range(len(names))])
        B = np.array(boots)
        obs = [roc_auc_score(y, S[:, j]) for j in range(len(names))]
        per = {k: {"auroc": round(float(obs[j]), 3), "rows_independent_hanley_mcneil": hanley(obs[j], int(y.sum()), int((1 - y).sum())),
                   "source_bootstrap": [round(float(np.percentile(B[:, j], 2.5)), 3), round(float(np.percentile(B[:, j], 97.5)), 3)]}
               for j, k in enumerate(names)}
        sep = 0; pairs = 0
        for i, j in itertools.combinations(range(len(names)), 2):
            diff = B[:, i] - B[:, j]; pairs += 1
            sep += int(np.percentile(diff, 2.5) > 0 or np.percentile(diff, 97.5) < 0)
        iv[sp] = {"n_rows": int(len(y)), "n_sources": int(len(gs)), "models": per,
                  "model_pairs_separated_by_paired_source_bootstrap": f"{sep}/{pairs}"}
    res["5_intervals_rows_vs_sources"] = iv

    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
