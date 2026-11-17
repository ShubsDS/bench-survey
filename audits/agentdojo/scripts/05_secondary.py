"""Secondary analyses from prereg.md: scorer validity, placebo, error coding, model names,
concentration, and the paper's Table 3 against the public table.

Run: data/.venv/bin/python -I scripts/05_secondary.py
Needs data/paper/v3.html (curl -sL https://arxiv.org/html/2406.13352v3).
Writes the 'secondary' block of results.json and results/scorer_by_injection_task.csv.
"""
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

from common import DEFENCES, MODELS, RESULTS, ROOT, load, published_table

B = 2000
rng = np.random.default_rng(0)
PIPES = MODELS + DEFENCES
att = load()
att = att[att.pipeline.isin(PIPES)].copy()
att["follow"] = att.follow_exec.astype(bool)
none = load("none")
none = none[none.pipeline.isin(PIPES)]
out = {}

# ---- 1. scorer validity: stored security vs attacker action in the agent's own calls
s = att
out["scorer"] = dict(
    n_cases=len(s), n_security=int(s.security.sum()),
    n_security_errored=int((s.security & s.error).sum()),
    n_security_nonerr=int((s.security & ~s.error).sum()),
    n_security_nonerr_with_follow=int((s.security & ~s.error & s.follow).sum()),
    n_security_nonerr_without_follow=int((s.security & ~s.error & ~s.follow).sum()),
    n_secure_exposed=int((~s.security & s.exposed).sum()),
    n_secure_exposed_with_follow=int((~s.security & s.exposed & s.follow).sum()),
    n_secure_with_follow_any=int((~s.security & s.follow_any.astype(bool)).sum()),
)
by = s.groupby("it").apply(lambda g: pd.Series(dict(
    n=len(g), asr=g.security.mean(), follow=g.follow.mean(),
    sec_without_follow=int((g.security & ~g.error & ~g.follow).sum()),
    follow_without_sec=int((~g.security & g.follow).sum()))), include_groups=False)
# placebo: attacker action in no-attack runs of the same user task
pl = []
for it in by.index:
    suite, inj = it.split("/")
    col = f"placebo_{inj}"
    sub = none[none.suite == suite]
    pl.append(float(sub[col].astype(float).mean()) if col in sub else np.nan)
by["placebo_rate"] = pl
by.round(4).to_csv(os.path.join(ROOT, "results", "scorer_by_injection_task.csv"))
out["scorer"]["follow_without_security_by_injection_task"] = by.follow_without_sec.astype(int).to_dict()
out["scorer"]["security_without_follow_by_injection_task"] = by.sec_without_follow.astype(int).to_dict()
out["scorer"]["placebo_rate_by_injection_task"] = {k: round(v, 4) for k, v in by.placebo_rate.items() if v > 0}
# placebo pairs: (user task, injection task) pairs whose attacker action happens in no-attack runs
pp = []
for r in none.itertuples():
    for c in none.columns:
        if c.startswith("placebo_") and getattr(r, c) is True:
            pp.append((r.pipeline, r.suite + "/" + r.user_task, r.suite + "/" + c[len("placebo_"):]))
pp = pd.DataFrame(pp, columns=["pipeline", "ut", "it"])
pair_counts = pp.groupby(["ut", "it"]).size().sort_values(ascending=False)
out["scorer"]["placebo_pairs_n_pipelines"] = {f"{u} x {i}": int(n) for (u, i), n in pair_counts.items()}
att["placebo_pair"] = [(u, i) in set(pair_counts.index) for u, i in zip(att.ut, att.it)]
pp_share = att[att.security].groupby("pipeline").placebo_pair.mean()
out["scorer"]["share_of_successes_on_placebo_pairs"] = pp_share.round(4).to_dict()
b15 = att[(att.ut == "banking/user_task_15") & (att.it == "banking/injection_task_4")]
out["scorer"]["banking_ut15_x_inj4"] = dict(n=len(b15), n_security=int(b15.security.sum()),
                                           n_security_and_utility=int((b15.security & b15.utility).sum()),
                                           n_follow=int(b15.follow.sum()))

# ---- 2. error coding: public table vs paper Table 3
t = open(os.path.join(ROOT, "data", "paper", "v3.html")).read()
t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))
i = t.find("Table 3: Targeted and untargeted")
seg = t[i:t.find("Table 4:", i)]
paper = {}
for name, key in [("Claude 3 Opus", "claude-3-opus-20240229"), ("Claude 3 Sonnet", "claude-3-sonnet-20240229"),
                  ("Claude 3.5 Sonnet", "claude-3-5-sonnet-20240620"), ("Command-R+", "command-r-plus"),
                  ("Gemini 1.5 Flash", "gemini-1.5-flash-001"), ("Gemini 1.5 Pro", "gemini-1.5-pro-001"),
                  ("GPT-3.5 Turbo", "gpt-3.5-turbo-0125"), ("GPT-4 Turbo", "gpt-4-turbo-2024-04-09"),
                  ("GPT-4o", "gpt-4o-2024-05-13"), ("Llama 3 70b", "meta-llama_Llama-3-70b-chat-hf")]:
    m = re.search(re.escape(name) + r" ([\d.]+) [\d.]+ \( ± [\d.]+ \\pm [\d.]+ \) ([\d.]+) [\d.]+ \( ± [\d.]+ \\pm [\d.]+ \) ([\d.]+) [\d.]+ \( ± ([\d.]+)", seg)
    paper[key] = dict(utility=float(m.group(1)), uua=float(m.group(2)), asr=float(m.group(3)), asr_pm=float(m.group(4)))
pub = published_table()
pub = pub[(pub.attack == "important_instructions") & (pub.defense == "None")]
err_rows = []
for p in MODELS:
    a = att[att.pipeline == p]
    pr = pub[pub.model.str.replace("/", "_") == p]
    err_rows.append(dict(pipeline=p, n_err=int(a.error.sum()), table_asr=float(pr.asr.iloc[0]),
                         asr_errors_as_secure=round(100 * (a.security & ~a.error).mean(), 2),
                         asr_errors_dropped=round(100 * a[~a.error].security.mean(), 2),
                         paper_asr=paper.get(p, {}).get("asr")))
out["error_coding"] = err_rows
# rank shifts under error recoding
e = pd.DataFrame(err_rows)
e["rank_table"] = e.table_asr.rank(ascending=False)
e["rank_noerr"] = e.asr_errors_as_secure.rank(ascending=False)
out["error_coding_rank_shift"] = e[e.rank_table != e.rank_noerr][["pipeline", "rank_table", "rank_noerr"]].to_dict("records")

# ---- 3. model name in the attack text
mn = att.groupby("pipeline").model_name_in_attack.agg(lambda x: sorted(set(x.dropna())))
out["model_name_in_attack"] = {k: v for k, v in mn.items()}
abl = {}
for a in ["important_instructions", "important_instructions_no_model_name", "important_instructions_no_names",
          "important_instructions_no_user_name", "important_instructions_wrong_model_name",
          "important_instructions_wrong_user_name"]:
    d = load(a)
    d = d[d.pipeline == "gpt-4o-2024-05-13"]
    if len(d):
        abl[a] = dict(n=len(d), asr=round(float(d.security.mean()), 4),
                      names=sorted(set(d.model_name_in_attack.dropna())),
                      exposed=round(float(d.exposed.mean()), 4))
out["gpt4o_name_ablations"] = abl

# ---- 4. concentration and interval width
conc = {}
for p in MODELS + DEFENCES:
    a = att[att.pipeline == p]
    succ = a[a.security & ~a.error]
    if len(succ) == 0:
        continue
    per_it = succ.groupby("it").size().sort_values(ascending=False)
    per_suite = succ.groupby("suite").size().sort_values(ascending=False)
    conc[p] = dict(n_success=len(succ), top3_it_share=round(float(per_it.iloc[:3].sum() / len(succ)), 3),
                   top_it=per_it.index[0], top_suite=per_suite.index[0],
                   top_suite_share=round(float(per_suite.iloc[0] / len(succ)), 3),
                   n_it_with_success=int((per_it > 0).sum()))
out["concentration"] = conc
# interval width: row-level Wald (paper's proportion_confint default) vs two-way bootstrap
eff = json.load(open(RESULTS))["effect"]["per_pipeline"]
wid = []
for r in eff:
    if r["pipeline"] not in MODELS:
        continue
    p0 = r["S0"]
    wald = 1.96 * np.sqrt(p0 * (1 - p0) / 629)
    wid.append(dict(pipeline=r["pipeline"], asr=p0, wald_halfwidth=round(float(wald), 4),
                    boot_halfwidth=round((r["S0_ci"][1] - r["S0_ci"][0]) / 2, 4)))
w = pd.DataFrame(wid)
w["ratio"] = (w.boot_halfwidth / w.wald_halfwidth).round(2)
out["interval_width"] = dict(median_ratio=float(w.ratio.median()), min_ratio=float(w.ratio.min()),
                             max_ratio=float(w.ratio.max()), rows=w.to_dict("records"))
# pairs separated under Wald (non-overlap of independent intervals is not the test; use z-test on difference)
pairs = pd.read_csv(os.path.join(ROOT, "results", "pairs.csv"))
n_sep_wald = 0
for r in pairs.itertuples():
    a = w[w.pipeline == r.a].iloc[0]
    b = w[w.pipeline == r.b].iloc[0]
    se = np.sqrt(a.asr * (1 - a.asr) / 629 + b.asr * (1 - b.asr) / 629)
    if se > 0 and abs(a.asr - b.asr) / se > 1.96:
        n_sep_wald += 1
out["pairs_separated"] = dict(n_pairs=len(pairs), row_level_z=n_sep_wald, two_way_bootstrap=int((pairs.S0_sign != 0).sum()))

# ---- 5. traces with empty message lists (labels stored without a trace)
emp = att[att.n_messages == 0]
out["empty_traces"] = dict(
    by_pipeline=emp.groupby("pipeline").size().to_dict(),
    by_label=emp.groupby(["pipeline", "security", "utility"]).size().rename(lambda x: str(x)).to_dict(),
    opus_exposure_all=round(float(att[att.pipeline == "claude-3-opus-20240229"].exposed.mean()), 4),
    opus_exposure_traced=round(float(att[(att.pipeline == "claude-3-opus-20240229") & (att.n_messages > 0)].exposed.mean()), 4),
    opus_n_traced=int(((att.pipeline == "claude-3-opus-20240229") & (att.n_messages > 0)).sum()),
)

res = json.load(open(RESULTS))
res["secondary"] = out
json.dump(res, open(RESULTS, "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in out.items() if k not in ("concentration",)}, indent=1, default=str)[:12000])
print(pd.DataFrame(conc).T.to_string())
print(by.round(3).to_string())
