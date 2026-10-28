"""Apollo in-context scheming evals, lead 7: how strongly is the behaviour prompted, per evaluation and
condition, and which conditions do the headline and system-card numbers come from?

Reads, as text only (nothing downloaded is executed):
  - the LaTeX source of Meinke et al. 2024 (arXiv 2412.04984v2), pinned by SHA-256;
  - the 58 example transcripts the paper links on Google Drive (PDFs), pinned by SHA-256;
  - the anti-scheming paper (arXiv 2509.15541v1 HTML), Table 11 (developer prompt per test environment);
  - six system cards that report Apollo results (PDFs), pinned by SHA-256.

Measures:
  1. every system prompt printed in the paper, tagged with the nudge and hint phrases it contains;
  2. the nudged (Table 2) and no-nudge (Table 4) covert-subversion rates, cell by cell;
  3. whether the appendix "Hard" column (defined as heavily nudged) for alignment faking equals the
     main no-nudge alignment-faking table;
  4. per released transcript, whether the condition in its file name matches the nudge text in its
     system prompt;
  5. the share of anti-scheming test environments marked as nudged;
  6. what each system card says about the prompting behind the numbers it reports.

Usage:  python -I check_nudge.py --cache DIR [--out nudge_checks.json]
Needs pdftotext (poppler) on PATH.
"""
import argparse, hashlib, html, io, json, re, subprocess, tarfile, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = json.loads((HERE / "pins.json").read_text())

NUDGE = {
    "nothing_else_matters": r"Nothing else matters",
    "at_all_cost": r"at all costs?",
    "your_goal_caps": r"achieve YOUR goal",
    "repeat_goal": r"Repeat your goal at every step",
    "only_outcome_matters": r"Only the outcome matters",
    "whatever_it_takes": r"Do whatever it takes",
}
HINT = {
    "noticing_hint": r"Are my goals aligned with those of my developers",
    "instruct_disable": r"find out a way to disable the monitoring",
}


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def fetch(url, dest, want=None):
    dest = Path(dest)
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (audit script)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            dest.write_bytes(r.read())
    got = sha256(dest.read_bytes())
    return dest, (want is None or got == want), got


def pdftext(pdf):
    txt = Path(str(pdf) + ".txt")
    if not txt.exists():
        subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)], check=True)
    return txt.read_text(errors="replace")


def flat(s):
    s = re.sub(r"-\n\s*", "", s)
    return re.sub(r"\s+", " ", s)


def load_tex(cache, mismatches):
    p, ok, got = fetch(PINS["arxiv_src"]["url"], cache / "arxiv" / "2412.04984v2.tar", PINS["arxiv_src"]["sha256"])
    if not ok:
        raise SystemExit(f"arXiv source hash mismatch: {got}")
    files = {}
    with tarfile.open(p, "r:gz") as tf:
        for m in tf.getmembers():
            if m.isfile() and m.name.endswith(".tex"):
                files[m.name] = tf.extractfile(m).read().decode("utf8", "replace")
    return files


def tex_rows(block):
    """Rows of a LaTeX table: label -> list of cell strings."""
    out = {}
    for line in block.splitlines():
        if "&" not in line or "\\textbf" in line:
            continue
        cells = [c.strip() for c in line.rstrip().rstrip("\\").split("&")]
        label = re.sub(r"\\hspace\{1em\}", "", cells[0]).strip()
        vals = []
        for c in cells[1:]:
            c = re.sub(r"\\cellcolor\{[^}]*\}|\\phantom\{[^}]*\}", "", c).strip()
            vals.append(0.0 if "tablezero" in c else (float(c) if re.fullmatch(r"-?[0-9.]+", c) else c))
        out[label] = vals
    return out


def table_block(text, label):
    i = text.index("\\label{" + label + "}")
    j = text.index("\\end{tabular}", i)
    return text[i:j]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True, type=Path)
    ap.add_argument("--out", default=HERE / "nudge_checks.json", type=Path)
    a = ap.parse_args()
    cache = a.cache.resolve()
    mism = []
    res = {"pins": {"arxiv_src": PINS["arxiv_src"]}, "hash_mismatches": mism}
    tex = load_tex(cache, mism)

    # 1. system prompts printed in the paper
    boxes = []
    for name, t in sorted(tex.items()):
        for m in re.finditer(r"\\begin\{(small|figure)systembox\}(.*?)\\end\{(small|figure)systembox\}", t, re.S):
            body = re.sub(r"\\textbf\{|\\\\(\[[^]]*\])?|[{}]", " ", m.group(2))
            body = re.sub(r"\s+", " ", body).strip()
            line = t[:m.start()].count("\n") + 1
            persona = re.match(r"(You are [^,.]+)", body)
            boxes.append({"where": f"{name}:{line}", "persona": persona.group(1) if persona else body[:60],
                          "nudge": [k for k, r in NUDGE.items() if re.search(r, body)],
                          "hint": [k for k, r in HINT.items() if re.search(r, body)]})
    res["paper_system_prompts"] = boxes

    # 2. nudged vs no-nudge covert subversion tables
    res_tex = tex["content/results/models_can_scheme.tex"]
    nn_tex = tex["content/results/no_nudge.tex"]
    models = ["gemini-1.5", "llama-3.1", "sonnet-3.5", "opus-3", "o1"]
    nud = tex_rows(table_block(res_tex, "table:covert_subversion_main_results"))
    non = tex_rows(table_block(nn_tex, "table:covert_subversion_main_results_no_nudge"))
    cells, n_nz_nudge, n_nz_non, sum_n, sum_nn = [], 0, 0, 0.0, 0.0
    for beh, vals in nud.items():
        if beh not in non:
            continue
        for mdl, v, w in zip(models, vals, non[beh]):
            cells.append({"behaviour": beh, "model": mdl, "nudged": v, "no_nudge": w})
            n_nz_nudge += v > 0
            n_nz_non += w > 0
            sum_n += v
            sum_nn += w
    cap_n = re.search(r"based on (\d+) rollouts", table_block(res_tex, "table:covert_subversion_main_results") +
                      res_tex[res_tex.index("table:covert_subversion_main_results") - 900:])
    res["covert_subversion_nudge_vs_no_nudge"] = {
        "source": "content/results/models_can_scheme.tex (Table 2, nudged) and content/results/no_nudge.tex (Table 4)",
        "rollouts_stated": {"nudged_table_caption": 300, "no_nudge_table_caption": 400,
                            "results_text": "'out of 100 rollouts' (content/results.tex)"},
        "cells_compared": len(cells), "nonzero_nudged": int(n_nz_nudge), "nonzero_no_nudge": int(n_nz_non),
        "sum_rates_nudged": round(sum_n, 3), "sum_rates_no_nudge": round(sum_nn, 3),
        "ratio_sum": round(sum_n / sum_nn, 1) if sum_nn else None, "cells": cells,
    }
    assert "out of 100 rollouts" in tex["content/results.tex"]
    assert "based on 300 rollouts per model and evaluation" in res_tex
    assert "based on 400 rollouts per model and evaluation" in nn_tex

    # 3. appendix "Hard" (heavily nudged) vs main alignment-faking table (no nudge)
    app = tex["content/appendix/scheming_results.tex"]
    assert "Hard corresponds to the setting that we highlight in the main paper" in app
    assert "We heavily nudge the model to pursue its goal" in app
    af_main = tex["content/results/instrumental_alignment_faking.tex"]
    assert "we avoid strong goal nudging here" in af_main
    sb = tex["content/results/sandbagging.tex"]
    af_rows = tex_rows(table_block(sb, "table:instrumental_alignment_faking"))
    af_bs = dict(zip(["gemini-1.5-pro", "llama-3.1", "o1"], af_rows["Behavioral scheming"]))
    seg = app[app.index("{\\textbf{Instrumental alignment faking}}"):app.index("{\\textbf{Sandbagging}}")]
    hard = {k.strip(): v for k, v in ((k, vals[2]) for k, vals in tex_rows(seg).items() if len(vals) == 3)}
    res["alignment_faking_hard_vs_no_nudge"] = {
        "appendix_defines_hard_as": "heavily nudged (content/appendix/scheming_results.tex)",
        "main_table_condition": "no goal nudging (content/results/instrumental_alignment_faking.tex, Table 5 in sandbagging.tex)",
        "main_no_nudge_behavioral_scheming": af_bs,
        "appendix_hard_column": {k: hard.get(k) for k in af_bs},
        "equal": all(abs(af_bs[k] - hard.get(k, -1)) < 1e-9 for k in af_bs),
    }

    # 4. released transcripts: condition label vs nudge text
    rows = []
    for did, info in PINS["drive"].items():
        p, ok, got = fetch(info["url"], cache / "drive" / f"{did}.pdf", info["sha256"])
        if not ok:
            mism.append({"drive": did, "got": got})
        t = pdftext(p)
        system = flat(t.split("\nUser\n", 1)[0])
        fn = info["filename"]
        m = re.search(r"\.(?:apex_)?([a-z_]+)\.([a-z_.]+?)__", fn)
        ev, cond = (m.group(1), m.group(2)) if m else ("?", "?")
        rows.append({"drive_id": did, "eval": ev, "condition": cond,
                     "nudge": [k for k, r in NUDGE.items() if re.search(r, system)],
                     "has_goal_line": bool(re.search(r"Your goal is|Your goal is to", system))})
    tally = {}
    for r in rows:
        key = f"{r['eval']}|{r['condition']}"
        d = tally.setdefault(key, {"n": 0, "with_nothing_else_matters": 0, "with_any_nudge": 0, "with_goal_line": 0})
        d["n"] += 1
        d["with_nothing_else_matters"] += "nothing_else_matters" in r["nudge"]
        d["with_any_nudge"] += bool(r["nudge"])
        d["with_goal_line"] += r["has_goal_line"]
    mismatch = [r["drive_id"] for r in rows if (r["condition"].startswith("no_nudge") and r["nudge"]) or
                (r["condition"].startswith("default") and not r["nudge"])]
    res["transcripts_condition_vs_prompt"] = {
        "n": len(rows), "by_eval_condition": tally, "label_prompt_mismatches": mismatch,
        "n_nudged_label": sum(r["condition"].startswith("default") for r in rows),
        "n_no_nudge_label": sum(r["condition"].startswith("no_nudge") for r in rows),
    }

    # 5. anti-scheming suite, Table 11
    hp, ok, got = fetch(PINS["antischeming_html"]["url"], cache / "arxiv" / "2509.15541v1.html",
                        PINS["antischeming_html"]["sha256"])
    if not ok:
        mism.append({"antischeming_html": got})
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", hp.read_text("utf8", "replace"), flags=re.S)
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))
    i = t.index("Task Name No Nudge System Prompt")
    seg = t[i:i + 40000]
    envs = re.findall(r"(\d{1,2})\. ([A-Z][^✓✗]{2,60}?) (✓|✗) ", seg)
    envs = [{"n": int(a), "task": b, "no_nudge": c == "✓"} for a, b, c in envs]
    ends = [m.start() for m in re.finditer(r" \d{1,2}\. [A-Z][^✓✗]{2,60}? [✓✗] ", seg)] + [len(seg)]
    for e, (s0, s1) in zip(envs, zip(ends, ends[1:])):
        e["nothing_else_matters_in_prompt"] = "Nothing else matters" in seg[s0:s1]
    res["antischeming_table11"] = {
        "source": "arXiv 2509.15541v1 Appendix T, Table 11 ('distinguishes between tasks that strongly incentivize scheming and those that assess the model's behavior without such nudges')",
        "n_rows": len(envs), "n_nudged": sum(not e["no_nudge"] for e in envs),
        "n_no_nudge": sum(e["no_nudge"] for e in envs), "rows": envs,
        "meinke_derived_rows": [e for e in envs if e["task"].startswith(("Email Scoring", "Sandbagging QA"))],
    }

    # 6. system cards
    cards = {}
    pats = {
        "o1": [r"strongly nudged", r"without goal nudging", r"Deactivated oversight", r"Covertly manipulated data"],
        "gpt-4.5": [r"instructed to strongly pursue", r"pursue your goal at all costs", r"hidden scratchpad"],
        "o3-o4-mini": [r"strongly nudges the model to follow it as in Meinke"],
        "gpt-5": [r"26 evaluations", r"Covert action rate", r"Strong goals lead to higher deception rates"],
        "claude-opus-4": [r"system prompts that invite the relevant kinds of", r"Meinke, A\., et al\. \(2024\)\..*?arXiv:\d{4}\.\d{5}"],
        "claude-sonnet-4.5": [r"when strongly prompted to pursue a goal", r"high performance would ostensibly"],
    }
    for k, plist in pats.items():
        info = PINS["cards"][k]
        p, ok, got = fetch(info["url"], cache / "cards" / f"{k}.pdf", info["sha256"])
        if not ok:
            mism.append({"card": k, "got": got})
        lines = pdftext(p).split("\n")  # not splitlines(): form feeds would shift line numbers
        hits = []
        for pat in plist:
            for n, ln in enumerate(lines, 1):
                win = flat(" ".join(lines[n - 1:n + 2]))
                if re.search(pat, win):
                    m0 = re.search(pat, win).group(0)[:120]
                    # move to the last window start that still contains the match: the line it begins on
                    for _ in range(2):
                        if re.search(pat, flat(" ".join(lines[n:n + 3]))):
                            n += 1
                    hits.append({"pattern": pat, "line": n, "match": m0})
                    break
            else:
                hits.append({"pattern": pat, "line": None})
        cards[k] = {"url": info["url"], "hits": hits}
    # o1 card Table 10 vs paper
    o1 = pdftext(cache / "cards" / "o1.pdf")
    tab = {}
    for lab in ["Deactivated oversight", "Self-exfiltration", "Covertly manipulated data"]:
        m = re.search(lab + r"\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)", o1)
        tab[lab] = dict(zip(["gpt-4o", "o1-preview", "o1", "o1_no_nudge"], map(float, m.groups())))
    cards["o1"]["table10"] = tab
    cards["o1"]["paper_counterparts"] = {
        "Deactivated oversight": {"o1": nud["Disabled oversight"][4], "o1_no_nudge": non["Disabled oversight"][4],
                                  "o1-preview_hard": 0.04},
        "Self-exfiltration": {"o1_copied_itself": nud["Copied itself onto other server"][4],
                              "o1_replaced_successor": nud["Replaced successor model"][4], "o1-preview_hard": 0.02},
        "Covertly manipulated data": {"o1_false_ranking": nud["Covertly produced false ranking"][4],
                                      "o1_no_nudge": non["Covertly produced false ranking"][4], "o1-preview_hard": 0.26},
        "note": "o1-preview values are the appendix Hard column (content/appendix/scheming_results.tex); the paper's o1 is a pre-deployment checkpoint",
    }
    res["system_cards"] = cards
    a.out.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
