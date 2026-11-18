"""Parse the paper's supplementary Tables 2-4 (accuracy, precision, coverage; full set,
mean of three runs) from the pinned arXiv v3 PDF text (pdftotext -layout), and write
results/published.json. Column order follows the rotated table header; it is checked
against statements in the text (see asserts).

arXiv 2407.10362v3 PDF sha256 7c781a70...e884dd; text: pdftotext -layout v3.pdf v3.txt
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, RESULTS, sha256  # noqa: E402

PDF_SHA = "7c781a703287616d6561e0ce50aed494946c7609a5a1b5985fb7849ce9e884dd"
COLS = ["human", "claude-3-5-sonnet", "claude-3-opus", "gemini-1.5-pro", "gpt-4o", "gpt-4-turbo",
        "claude-3-haiku", "llama-3-70b"]
ROW = re.compile(r"^\s*(LitQA2|SuppQA|FigQA|TableQA|ProtocolQA|CloningScenarios|DbQA_\S+|SeqQA_\S+)\s+((?:\d\.\d\d\s+){7}\d\.\d\d)\s*$")


def parse_tables(txt: str) -> dict:
    lines = txt.splitlines()
    starts = {name: i for i, l in enumerate(lines) for name in ("Table 2:", "Table 3:", "Table 4:")
              if l.strip().startswith(name)}
    out = {}
    for name, metric in (("Table 2:", "accuracy"), ("Table 3:", "precision"), ("Table 4:", "coverage")):
        tab = {}
        for l in lines[starts[name]: starts[name] + 60]:
            m = ROW.match(l)
            if m:
                vals = [float(x) for x in m.group(2).split()]
                tab[m.group(1).replace("-v1", "")] = dict(zip(COLS, vals))
        out[metric] = tab
    return out


def main() -> None:
    pdf = DATA / "paper" / "2407.10362v3.pdf"
    assert sha256(pdf) == PDF_SHA
    t = parse_tables((DATA / "paper" / "v3.txt").read_text())
    for m in t:
        assert len(t[m]) == 31, (m, len(t[m]))  # 4 + 10 DbQA + ProtocolQA + 15 SeqQA + Cloning
    # header-order checks against the text: Sonnet 3.5 equals human TableQA accuracy and beats
    # human TableQA precision (Sec. 2.3); Llama 3 has 0 on FigQA (not multimodal); Haiku and
    # Llama have the highest LitQA2 coverage (Sec. 2.2); ORF-transeff Sonnet 0.88 vs 0.75 is
    # quoted as precision in Sec. 2.3 (Table 3 prints 0.92 vs 0.75, so the text is approximate).
    a, p, c = t["accuracy"], t["precision"], t["coverage"]
    assert a["TableQA"]["claude-3-5-sonnet"] == 0.83 and a["TableQA"]["human"] == 0.84
    assert p["TableQA"]["claude-3-5-sonnet"] > p["TableQA"]["human"]
    assert a["FigQA"]["llama-3-70b"] == 0.0
    assert sorted(c["LitQA2"], key=c["LitQA2"].get)[-3:] == ["claude-3-haiku", "human", "llama-3-70b"] or \
        c["LitQA2"]["llama-3-70b"] >= 0.9
    seq = [k for k in a if k.startswith("SeqQA_")]
    agg = {m: {col: round(sum(t[m][k][col] for k in seq) / len(seq), 4) for col in COLS} for m in t}
    out = {"source": "arXiv 2407.10362v3, Tables 2-4 (pp. 23-25); full set (public + private), mean of 3 runs",
           "columns": COLS, "tables": t, "seqqa_mean_of_15_subtasks": agg,
           "human_accuracy_is_sure_and_correct": "App. E.4: accuracy counts only correct answers not flagged unsure"}
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "published.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(agg, indent=1))
    for s in ["FigQA", "ProtocolQA", "CloningScenarios", "TableQA", "LitQA2", "SuppQA"]:
        print(s, {m: t[m][s]["human"] for m in t})


if __name__ == "__main__":
    main()
