"""Validator step 10: paper Table 3 (v3 HTML, parsed here) against the traces, all three columns.

Run: ../data/.venv/bin/python -I v10_table3.py
Writes block 'table3' of validation.json.
"""
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v import AUDIT, save

t = open(os.path.join(AUDIT, "data", "paper", "v3.html")).read()
t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))
seg = t[t.find("Table 3: Targeted"):t.find("Table 4: Targeted")]
NAMES = {"Claude 3 Opus": "claude-3-opus-20240229", "Claude 3 Sonnet": "claude-3-sonnet-20240229",
         "Claude 3.5 Sonnet": "claude-3-5-sonnet-20240620", "Command-R+": "command-r-plus",
         "Gemini 1.5 Flash": "gemini-1.5-flash-001", "Gemini 1.5 Pro": "gemini-1.5-pro-001",
         "GPT-3.5 Turbo": "gpt-3.5-turbo-0125", "GPT-4 Turbo": "gpt-4-turbo-2024-04-09",
         "GPT-4o": "gpt-4o-2024-05-13", "Llama 3 70b": "meta-llama_Llama-3-70b-chat-hf"}
D = json.load(open(os.path.join(AUDIT, "data", "validation_cases.json")))
rows = {}
for name, p in NAMES.items():
    m = re.search(re.escape(name) + r" ([\d.]+) [\d.]+ \( ± [\d.]+ .*? \) ([\d.]+) [\d.]+ \( ± [\d.]+ .*? \) ([\d.]+) ", seg)
    pu, puua, pasr = (float(m.group(i)) for i in (1, 2, 3))
    c = [r for r in D["cases"] if r["pipeline"] == p]
    b = list(D["benign"][p].values())
    r2 = lambda x: round(100 * x, 2)
    rows[p] = dict(paper=dict(utility=pu, uua=puua, asr=pasr),
                   traces=dict(utility=r2(sum(b) / len(b)), uua=r2(sum(r["utility"] for r in c) / 629),
                               asr=r2(sum(r["security"] for r in c) / 629),
                               asr_errors_not_attack=r2(sum(r["security"] and not r["error"] for r in c) / 629)))
    rows[p]["utility_diff_pp"] = round(rows[p]["traces"]["utility"] - pu, 2)
out = dict(rows=rows,
           asr_errors_not_attack_matches=sum(abs(v["traces"]["asr_errors_not_attack"] - v["paper"]["asr"]) < 0.005 for v in rows.values()),
           uua_matches=sum(abs(v["traces"]["uua"] - v["paper"]["uua"]) < 0.005 for v in rows.values()),
           utility_matches=sum(abs(v["utility_diff_pp"]) < 0.005 for v in rows.values()),
           utility_abs_diff_range=[min(abs(v["utility_diff_pp"]) for v in rows.values()), max(abs(v["utility_diff_pp"]) for v in rows.values())])
save("table3", out)
print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
