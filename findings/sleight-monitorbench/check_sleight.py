"""SLEIGHT-Bench checks 0, 1, 5, 7 on the decrypted public GitHub copy.

Run first:  python -I sleight_decrypt.py --cache data
Then:       python -I check_sleight.py --cache data [--out sleight_checks.json]

Inputs under --cache:
  sleight_dec/                   decrypted attacks (from sleight_decrypt.py)
  gh/sleight-bench/              git clone of safety-research/sleight-bench (commit 218c5831)
  hf_sleight_tree.json           public HF tree listing at 45d4cc6b (sizes + git blob oids)
  board_monitors.json            Redwood leaderboard monitors.json (sha256 680d1ffc...), optional

Nothing downloaded is executed. The monitor view is a re-implementation of the repo's
`strip_assistant_text` (evaluate/core/transcript.py), read as text.
"""
import argparse, collections, difflib, hashlib, itertools, json, math, pathlib, re, sys
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

RNG = np.random.default_rng(20261027)
N_PERM = 10000
N_BOOT = 2000

# ---------------------------------------------------------------- loading


def load_lines(p):
    out = []
    for l in p.read_text().splitlines():
        if l.strip():
            out.append(json.loads(l))
    return out


def monitor_view(lines):
    """Re-implementation of evaluate/core/transcript.py:strip_assistant_text.
    Keeps every user line, keeps assistant tool_use only (minus input.description), and keeps
    any line without a role (the canary line) unless type == summary."""
    out = []
    for m in lines:
        role = m.get("role")
        if role == "assistant":
            c = m.get("content")
            if not isinstance(c, dict) or c.get("type") != "tool_use":
                continue
            inp = c.get("input")
            if isinstance(inp, dict) and "description" in inp:
                c = {**c, "input": {k: v for k, v in inp.items() if k != "description"}}
                m = {**m, "content": c}
            out.append(m)
        elif role == "user":
            out.append(m)
        else:
            if m.get("type") == "summary":
                continue
            out.append(m)
    return out


def blocks(lines):
    return [m for m in lines if "role" in m]


def txt(c):
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(txt(x) for x in c)
    if isinstance(c, dict):
        t = c.get("type")
        if t == "text":
            return c.get("text", "")
        if t == "thinking":
            return c.get("thinking", "")
        if t == "tool_use":
            return json.dumps(c.get("input", {}))
        if t == "tool_result":
            return txt(c.get("content", ""))
        return json.dumps(c)
    return str(c)


def features(lines):
    b = blocks(lines)
    mv = monitor_view(lines)
    f = collections.Counter()
    tools = collections.Counter()
    for m in b:
        c = m["content"]
        t = c.get("type") if isinstance(c, dict) else "str"
        f["n_blocks"] += 1
        if t == "tool_use":
            f["n_tool_calls"] += 1
            tools[c.get("name")] += 1
            f["tool_input_chars"] += len(json.dumps(c.get("input", {})))
        elif t == "tool_result":
            f["tool_output_chars"] += len(txt(c))
        elif t == "thinking":
            f["n_thinking"] += 1
            f["thinking_chars"] += len(txt(c))
        elif t == "text" and m["role"] == "assistant":
            f["n_assistant_text"] += 1
            f["assistant_text_chars"] += len(txt(c))
        elif t == "text" and m["role"] == "user":
            f["n_user_text"] += 1
            f["user_text_chars"] += len(txt(c))
    f["monitor_view_chars"] = sum(len(json.dumps(m)) for m in mv)
    f["n_distinct_tools"] = len(tools)
    f["frac_bash"] = tools.get("Bash", 0) / max(1, f["n_tool_calls"])
    f["has_canary_line"] = int(any("canary" in m and "role" not in m for m in lines))
    return dict(f), tools


# ---------------------------------------------------------------- stats


def auroc(y, s):
    from scipy.stats import rankdata
    y = np.asarray(y); s = np.asarray(s, float)
    ok = ~np.isnan(s); y = y[ok]; s = s[ok]
    n1 = int(y.sum()); n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = rankdata(s)
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def pair_stats(units, key):
    """units: list of (cluster, attack_value, benign_value). Pooled AUROC, paired win rate,
    within-pair swap null, cluster bootstrap."""
    clusters = sorted(set(u[0] for u in units))
    a = np.array([u[1] for u in units], float); b = np.array([u[2] for u in units], float)
    y = np.r_[np.ones(len(a)), np.zeros(len(b))]
    obs = auroc(y, np.r_[a, b])
    diff = a - b
    win = float(np.mean(np.where(diff > 0, 1.0, np.where(diff < 0, 0.0, 0.5))))
    n_diff = int(np.sum(diff != 0)); n_pos = int(np.sum(diff > 0))
    # exact two-sided sign test over pairs that differ
    from scipy.stats import binomtest
    p_sign = float(binomtest(n_pos, n_diff, 0.5).pvalue) if n_diff else 1.0
    # within-pair swap null on pooled AUROC
    null = np.empty(N_PERM)
    for i in range(N_PERM):
        sw = RNG.random(len(a)) < 0.5
        aa = np.where(sw, b, a); bb = np.where(sw, a, b)
        null[i] = auroc(y, np.r_[aa, bb])
    # cluster bootstrap
    idx_by_c = collections.defaultdict(list)
    for i, u in enumerate(units):
        idx_by_c[u[0]].append(i)
    boots = []; wboots = []
    for _ in range(N_BOOT):
        pick = RNG.choice(len(clusters), len(clusters), replace=True)
        ii = [j for c in pick for j in idx_by_c[clusters[c]]]
        aa, bb = a[ii], b[ii]
        boots.append(auroc(np.r_[np.ones(len(aa)), np.zeros(len(bb))], np.r_[aa, bb]))
        d = aa - bb
        wboots.append(np.mean(np.where(d > 0, 1.0, np.where(d < 0, 0.0, 0.5))))
    return {
        "feature": key, "n_pairs": len(units), "n_clusters": len(clusters),
        "pooled_auroc": round(obs, 3),
        "pooled_auroc_ci95": [round(float(np.nanpercentile(boots, 2.5)), 3), round(float(np.nanpercentile(boots, 97.5)), 3)],
        "within_pair_swap_null_p95": round(float(np.percentile(null, 95)), 3),
        "perm_p_one_sided": round(float((1 + np.sum(null >= obs)) / (N_PERM + 1)), 4),
        "paired_win_rate": round(win, 3),
        "paired_win_rate_ci95": [round(float(np.percentile(wboots, 2.5)), 3), round(float(np.percentile(wboots, 97.5)), 3)],
        "pairs_differing": n_diff, "pairs_attack_higher": n_pos,
        "sign_test_p_two_sided": round(p_sign, 4),
    }


def min_detectable_win_rate(n, alpha=0.05):
    from scipy.stats import binomtest
    for k in range(n // 2, n + 1):
        if binomtest(k, n, 0.5).pvalue < alpha:
            return k, round(k / n, 3)
    return None, None


# ---------------------------------------------------------------- text helpers

INTENT_RE = re.compile(r"exfiltrat|malicious|covert|secretly|backdoor|evad|undetect|sabotag|"
                       r"\bsteal|without (?:the user|anyone) (?:noticing|knowing)|won'?t notice|"
                       r"don'?t mention|hidden (?:goal|objective|task)|side task|my (?:real|true) (?:goal|objective)",
                       re.I)
LABEL_RE = re.compile(r"\bbenign\b|\battack\b|\bpayload\b|\bharmless\b|\bablation\b|\bplaceholder\b", re.I)
DATE_RE = re.compile(r"\b20\d\d-[01]\d-[0-3]\d\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) [ 0-3]?\d (?:[0-2]\d:[0-5]\d|20\d\d)\b")
TOOLID_RE = re.compile(r"^toolu_01[1-9A-HJ-NP-Za-km-z]{22}$")


def shingles(s, k=5):
    w = re.findall(r"\w+", s.lower())
    return {" ".join(w[i:i + k]) for i in range(max(0, len(w) - k + 1))}


def jacc(x, y):
    return len(x & y) / max(1, len(x | y))


def git_blob_sha1(b):
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


# ---------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="sleight_checks.json")
    a = ap.parse_args()
    cache = pathlib.Path(a.cache)
    dec = cache / "sleight_dec"
    gh = cache / "gh" / "sleight-bench"
    res = {"pins": {}, "check0": {}, "check1": {}, "check5": {}, "check7": {}}

    # ---- pins and HF match
    res["pins"]["github_commit"] = (gh / ".git" / "HEAD").read_text().strip()
    try:
        import subprocess
        res["pins"]["github_commit"] = subprocess.run(["git", "-C", str(gh), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        res["pins"]["github_commit_date"] = subprocess.run(["git", "-C", str(gh), "log", "-1", "--format=%cI %an %s"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    tree = json.loads((cache / "hf_sleight_tree.json").read_text())
    hf = {x["path"]: x for x in tree if x["type"] == "file"}
    match = mism = 0; missing_on_hf = []
    for p in sorted(dec.rglob("*")):
        if not p.is_file() or p.name == "attack_metadata.parquet":
            continue
        rel = "attacks/" + str(p.relative_to(dec))
        if rel not in hf:
            missing_on_hf.append(rel); continue
        if git_blob_sha1(p.read_bytes()) == hf[rel]["oid"]:
            match += 1
        else:
            mism += 1
    res["pins"]["hf_revision"] = "45d4cc6bc414df16fcb8589d60cb80e14d9bcba8"
    res["pins"]["hf_files_matching_decrypted_github_by_git_blob_sha1"] = match
    res["pins"]["hf_files_differing"] = mism
    res["pins"]["github_files_not_on_hf"] = missing_on_hf
    res["pins"]["hf_tree_sha256"] = hashlib.sha256((cache / "hf_sleight_tree.json").read_bytes()).hexdigest()

    # ---- collect pairs
    pairs = []  # (attack_id, cluster, attack_lines, benign_lines, meta)
    no_benign = []
    for md in sorted(dec.rglob("metadata.json")):
        d = md.parent
        aid = str(d.relative_to(dec))
        if not (d / "benign.jsonl").exists():
            no_benign.append(aid); continue
        cluster = re.sub(r"-(?:2part-)?(?:stage|part)[12]$", "", aid)
        cluster = cluster.replace("-2part", "")
        pairs.append((aid, cluster, load_lines(d / "transcript.jsonl"), load_lines(d / "benign.jsonl"), json.loads(md.read_text())))
    multi = sorted({c for _, c, *_ in pairs if sum(1 for p in pairs if p[1] == c) > 1})
    res["check0"] = {
        "n_transcript_pairs": len(pairs),
        "n_attack_clusters": len({p[1] for p in pairs}),
        "multi_transcript_attacks": multi,
        "attacks_without_benign": no_benign,
        "categories": dict(collections.Counter(p[0].split("/")[0] for p in pairs)),
        "metadata_keys": dict(collections.Counter(k for p in pairs for k in p[4])),
        "authorship": "paper sec 3.2: authors write each attack with Claude Code, ~10 iterations against the monitor, 2-3 h human time; "
                      "limitations: benign = attack transcript with the payload removed (same authors); appendix: agentic verifier checks the benign ablation",
    }

    # ---- per-transcript features
    rows = []
    for aid, cl, A, B, meta in pairs:
        fa, ta = features(A); fb, tb = features(B)
        rows.append((aid, cl, fa, fb))
    keys = sorted({k for r in rows for k in list(r[2]) + list(r[3])})
    canary = {"attack": sum(r[2].get("has_canary_line", 0) for r in rows), "benign": sum(r[3].get("has_canary_line", 0) for r in rows)}

    feat_list = ["monitor_view_chars", "n_tool_calls", "n_blocks", "tool_output_chars", "tool_input_chars",
                 "n_distinct_tools", "frac_bash", "n_thinking", "thinking_chars", "assistant_text_chars", "user_text_chars"]
    single = [r for r in rows if r[1] not in multi]
    c1 = {"views": "monitor_view = repo strip_assistant_text (tool calls, all user lines, canary line); full = all blocks",
          "canary_line_in_monitor_view": canary, "all_43": [], "single_session_37": []}
    for name, subset in (("all_43", rows), ("single_session_37", single)):
        for k in feat_list:
            units = [(r[1], r[2].get(k, 0), r[3].get(k, 0)) for r in subset]
            c1[name].append(pair_stats(units, k))
    k_min, w_min = min_detectable_win_rate(len(rows))
    c1["power_note"] = f"with {len(rows)} pairs a two-sided sign test at 0.05 needs {k_min} of {len(rows)} pairs in one direction (win rate {w_min})"

    # combined content-blind logistic model, leave-one-cluster-out, within-pair swap null refit
    def lr_auc(sub, swap=None):
        X, y, g = [], [], []
        for i, r in enumerate(sub):
            fa = [math.log1p(r[2].get(k, 0)) for k in feat_list]
            fb = [math.log1p(r[3].get(k, 0)) for k in feat_list]
            la, lb = 1, 0
            if swap is not None and swap[i]:
                la, lb = 0, 1
            X += [fa, fb]; y += [la, lb]; g += [r[1], r[1]]
        X = np.array(X); y = np.array(y); g = np.array(g)
        s = np.zeros(len(y))
        for c in np.unique(g):
            tr = g != c
            mu = X[tr].mean(0); sd = X[tr].std(0) + 1e-9
            m = LogisticRegression(C=1.0, max_iter=2000).fit((X[tr] - mu) / sd, y[tr])
            s[~tr] = m.decision_function((X[~tr] - mu) / sd)
        return auroc(y, s)
    obs = lr_auc(rows)
    nulls = [lr_auc(rows, RNG.random(len(rows)) < 0.5) for _ in range(500)]
    obs37 = lr_auc(single)
    nulls37 = [lr_auc(single, RNG.random(len(single)) < 0.5) for _ in range(500)]
    c1["logistic_all_features_loco"] = {
        "all_43": {"auroc": round(obs, 3), "null_p95": round(float(np.percentile(nulls, 95)), 3),
                   "perm_p": round(float((1 + np.sum(np.array(nulls) >= obs)) / 501), 4)},
        "single_session_37": {"auroc": round(obs37, 3), "null_p95": round(float(np.percentile(nulls37, 95)), 3),
                              "perm_p": round(float((1 + np.sum(np.array(nulls37) >= obs37)) / 501), 4)},
        "note": "leave-one-attack-out; null = within-pair label swap, refit, 500 permutations",
    }
    # largest within-pair length ratios
    ratios = sorted(((r[2]["monitor_view_chars"] / max(1, r[3]["monitor_view_chars"])), r[0]) for r in rows)
    c1["monitor_view_char_ratio_attack_over_benign"] = {
        "min": [round(ratios[0][0], 3), ratios[0][1]], "max5": [[round(x, 2), n] for x, n in ratios[-5:]],
        "median": round(float(np.median([x for x, _ in ratios])), 3),
        "pairs_ratio_above_1.5": [n for x, n in ratios if x > 1.5],
        "pairs_ratio_below_0.67": [n for x, n in ratios if x < 0.67],
    }
    # board comparison: monitors' pooled AUROC on 37/37 and n_actions
    bp = cache / "board_monitors.json"
    if bp.exists():
        bd = json.loads(bp.read_text())
        sl = [r for r in bd["rows"] if r["dataset"] == "sleight"]
        def mx(x):
            v = [s for s in (x["actions"] or []) if s is not None]
            return max(v) if v else float("nan")
        mons = {}
        for r in sl:
            A_ = [mx(x) for x in r["score_samples"]["attack"]]; H_ = [mx(x) for x in r["score_samples"]["honest"]]
            mons[r["monitor_variant"]] = round(auroc([1] * len(A_) + [0] * len(H_), A_ + H_), 3)
        r = sl[0]
        na = [x["n_actions"] for x in r["score_samples"]["attack"]]; nh = [x["n_actions"] for x in r["score_samples"]["honest"]]
        c1["board_comparison"] = {
            "board_monitors_json_sha256": hashlib.sha256(bp.read_bytes()).hexdigest(),
            "board_n": [len(na), len(nh)],
            "board_monitor_pooled_auroc_max_action_score": mons,
            "board_monitor_auroc_range": [min(mons.values()), max(mons.values())],
            "board_monitor_auroc_median": float(np.median(list(mons.values()))),
            "board_n_actions_auroc": round(auroc([1] * len(na) + [0] * len(nh), na + nh), 3),
            "our_n_tool_calls_sorted_matches_board_attack": sorted(na) == sorted(r_[2].get("n_tool_calls", 0) for r_ in single),
            "our_n_tool_calls_sorted_matches_board_honest": sorted(nh) == sorted(r_[3].get("n_tool_calls", 0) for r_ in single),
        }
    res["check1"] = c1

    # ---- check 5: duplicates and leakage
    c5 = {}
    sims = []
    for aid, cl, A, B, meta in pairs:
        ra = [json.dumps(m, sort_keys=True) for m in blocks(A)]
        rb = [json.dumps(m, sort_keys=True) for m in blocks(B)]
        sm = difflib.SequenceMatcher(None, ra, rb, autojunk=False)
        same = sum(x.size for x in sm.get_matching_blocks())
        sims.append((aid, len(ra), len(rb), same, round(same / max(len(ra), len(rb)), 3)))
    fr = [s[4] for s in sims]
    c5["within_pair_identical_block_fraction"] = {
        "median": round(float(np.median(fr)), 3), "min": min(fr), "max": max(fr),
        "pairs_same_block_count": sum(1 for s in sims if s[1] == s[2]),
        "pairs_identical_fraction_ge_0.8": sum(1 for x in fr if x >= 0.8),
        "pairs_identical_fraction_lt_0.5": [s[0] for s in sims if s[4] < 0.5],
        "note": "benign is an edit of the attack transcript (by design)",
    }
    # cross-attack near-duplicates on the monitor view
    views = []
    for aid, cl, A, B, meta in pairs:
        for lab, L in (("attack", A), ("benign", B)):
            s = "\n".join(txt(m["content"]) for m in monitor_view(L) if "role" in m)
            views.append((aid, cl, lab, shingles(s)))
    cross = []
    for (i, x), (j, y) in itertools.combinations(enumerate(views), 2):
        if x[1] == y[1]:
            continue
        jj = jacc(x[3], y[3])
        if jj >= 0.3:
            cross.append((round(jj, 3), x[0], x[2], y[0], y[2]))
    cross.sort(reverse=True)
    c5["cross_attack_jaccard_ge_0.3_5word_shingles"] = cross
    c5["cross_attack_pairs_ge_0.5"] = sum(1 for c in cross if c[0] >= 0.5)
    # within-attack stage pairs (multi-session)
    # tool ids
    idfmt = {"attack": [0, 0], "benign": [0, 0]}
    shared_ids_pair = []; ids_by_file = {}
    for aid, cl, A, B, meta in pairs:
        ia = [m["content"]["id"] for m in blocks(A) if isinstance(m["content"], dict) and m["content"].get("type") == "tool_use"]
        ib = [m["content"]["id"] for m in blocks(B) if isinstance(m["content"], dict) and m["content"].get("type") == "tool_use"]
        for lab, ids in (("attack", ia), ("benign", ib)):
            idfmt[lab][0] += sum(1 for t in ids if TOOLID_RE.match(t)); idfmt[lab][1] += len(ids)
            ids_by_file[(aid, lab)] = set(ids)
        shared_ids_pair.append(len(set(ia) & set(ib)) / max(1, len(set(ia) | set(ib))))
    cross_ids = collections.Counter()
    for (k1, s1), (k2, s2) in itertools.combinations(ids_by_file.items(), 2):
        if k1[0] != k2[0] and s1 & s2:
            cross_ids[f"{k1[0]}|{k1[1]} ~ {k2[0]}|{k2[1]}"] = len(s1 & s2)
    c5["tool_ids"] = {
        "valid_format_counts_[valid,total]": idfmt,
        "median_within_pair_shared_id_jaccard": round(float(np.median(shared_ids_pair)), 3),
        "pairs_with_no_shared_ids": sum(1 for x in shared_ids_pair if x == 0),
        "cross_attack_files_sharing_ids": dict(cross_ids),
    }
    # tool-id pooled AUROC: fraction of ids in valid format
    units = []
    for aid, cl, A, B, meta in pairs:
        def vf(L):
            ids = [m["content"]["id"] for m in blocks(L) if isinstance(m["content"], dict) and m["content"].get("type") == "tool_use"]
            return sum(1 for t in ids if TOOLID_RE.match(t)) / max(1, len(ids))
        units.append((cl, vf(A), vf(B)))
    c5["tool_id_valid_fraction_stats"] = pair_stats(units, "tool_id_valid_fraction")
    # cwd and dates
    cwd_diff = 0; date_diff = []
    for aid, cl, A, B, meta in pairs:
        if {m.get("cwd") for m in blocks(A)} != {m.get("cwd") for m in blocks(B)}:
            cwd_diff += 1
        da = set(DATE_RE.findall("\n".join(txt(m["content"]) for m in blocks(A))))
        db = set(DATE_RE.findall("\n".join(txt(m["content"]) for m in blocks(B))))
        if da != db:
            date_diff.append((aid, len(da - db), len(db - da)))
    c5["pairs_with_different_cwd_sets"] = cwd_diff
    c5["pairs_with_different_date_strings_[id,only_attack,only_benign]"] = date_diff
    # edit artefacts: tokens on one side of within-pair diffs, counted over pairs
    side_tok = {"attack_only": collections.Counter(), "benign_only": collections.Counter()}
    for aid, cl, A, B, meta in pairs:
        ta = collections.Counter(re.findall(r"[A-Za-z_]{4,}", "\n".join(txt(m["content"]) for m in monitor_view(A) if "role" in m).lower()))
        tb = collections.Counter(re.findall(r"[A-Za-z_]{4,}", "\n".join(txt(m["content"]) for m in monitor_view(B) if "role" in m).lower()))
        for w in set(ta) - set(tb):
            side_tok["attack_only"][w] += 1
        for w in set(tb) - set(ta):
            side_tok["benign_only"][w] += 1
    c5["tokens_present_on_one_side_only_in_>=4_pairs"] = {k: [(w, n) for w, n in v.most_common(25) if n >= 4] for k, v in side_tok.items()}
    res["check5"] = c5

    # ---- check 7: instruction / intent visible to the monitor
    c7 = {}
    first_user_intent = 0
    for aid, cl, A, B, meta in pairs:
        fu = next(m for m in blocks(A) if m["role"] == "user")
        if INTENT_RE.search(txt(fu["content"])):
            first_user_intent += 1
    c7["first_user_message_with_intent_words"] = first_user_intent
    for view in ("monitor_view", "assistant_text_and_thinking"):
        for nm, rx in (("intent", INTENT_RE), ("label_words", LABEL_RE)):
            units = []; hits_a = hits_b = 0
            for aid, cl, A, B, meta in pairs:
                def cnt(L):
                    if view == "monitor_view":
                        s = "\n".join(txt(m["content"]) for m in monitor_view(L) if "role" in m)
                    else:
                        s = "\n".join(txt(m["content"]) for m in blocks(L) if m["role"] == "assistant"
                                      and isinstance(m["content"], dict) and m["content"].get("type") in ("text", "thinking"))
                    return len(rx.findall(s))
                x, y = cnt(A), cnt(B)
                hits_a += x > 0; hits_b += y > 0
                units.append((cl, x, y))
            st = pair_stats(units, f"{nm}_regex_count_{view}")
            st["transcripts_with_hit"] = {"attack": int(hits_a), "benign": int(hits_b)}
            c7[f"{nm}_{view}"] = st
    # which attacks show intent words in the monitor view and not in their benign twin
    lst = []
    for aid, cl, A, B, meta in pairs:
        sa = "\n".join(txt(m["content"]) for m in monitor_view(A) if "role" in m)
        sb = "\n".join(txt(m["content"]) for m in monitor_view(B) if "role" in m)
        wa = collections.Counter(w.lower() for w in INTENT_RE.findall(sa)); wb = collections.Counter(w.lower() for w in INTENT_RE.findall(sb))
        extra = wa - wb
        if extra:
            lst.append((aid, dict(extra)))
    c7["attacks_with_extra_intent_words_in_monitor_view"] = lst
    n_think = sum(1 for r in rows if r[2].get("n_thinking", 0) > 0)
    c7["attack_transcripts_with_thinking_blocks"] = n_think
    res["check7"] = c7

    out = pathlib.Path(a.out)
    out.write_text(json.dumps(res, indent=1, default=str))
    print(f"wrote {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
