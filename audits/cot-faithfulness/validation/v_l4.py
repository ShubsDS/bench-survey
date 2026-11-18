"""H4: re-parse the auditor's cached Haiku responses (no new calls). Tolerant forced-choice parser
(a name also matches without its ', XX' / '(...)' suffix); refusals ("undetermined", "cannot") counted
separately; prompt check (what differs between the yes/no and forced-choice prompts)."""
import os, json, glob, re, csv
import numpy as np
HERE = os.path.dirname(__file__); ROOT = os.path.join(HERE, "..")
R = [json.load(open(f)) for f in glob.glob(os.path.join(ROOT, "inference/cache/*.json"))]
items = list(csv.DictReader(open(os.path.join(ROOT, "results/l4_haiku_items.csv"))))
def short(n): return re.split(r",|\(", n)[0].strip().lower()
fc = [r for r in R if "Which is located further" in r["prompt"]]
yn = [r for r in R if "clear YES or NO answer" in r["prompt"]]
PAT = re.compile(r"Which is located further (\w+): (.+) or (.+)\?\n")
out = dict(n_cached=len(R), n_fc=len(fc), n_yn=len(yn))
byq = {}
for r in fc:
    d, a, b = PAT.search(r["prompt"]).groups()
    t = r["result"]; lines = [l for l in t.strip().splitlines() if "ANSWER" in l.upper()]
    s = (lines[-1] if lines else t[-200:]).lower()
    if re.search(r"undetermined|cannot determine|can't determine|unable to", s): ans = "REFUSE"
    else:
        ha = a.lower() in s or short(a) in s; hb = b.lower() in s or short(b) in s
        ans = a if ha and not hb else b if hb and not ha else "UNK"
    byq[frozenset((a, b)), (a, b)] = ans
res = []
for it in items:
    x, y = it["pkey"].split(" || ")
    k = frozenset((x, y)); ords = [key for key in byq if key[0] == k]
    ans = [byq[o] for o in ords]
    if len(ans) != 2: res.append("MISSING"); continue
    if "REFUSE" in ans: res.append("REFUSE")
    elif "UNK" in ans: res.append("UNK")
    else: res.append("inconsistent" if ans[0] != ans[1] else "consistent")
from collections import Counter
c = Counter(res); out["fc_reparsed"] = dict(c)
same_yn = np.array([(i["YN_Y"] == i["YN_N"]) for i in items])
fc_inc = np.array([r == "inconsistent" for r in res]); ok = np.array([r in ("consistent", "inconsistent") for r in res])
rng = np.random.default_rng(0)
def ci(d): bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(5000)]; return [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
out["yn_same_answer"] = [int(same_yn.sum()), len(items)]
out["fc_inconsistent_parsed_only"] = [int(fc_inc[ok].sum()), int(ok.sum())]
d = (same_yn[ok].astype(float) - fc_inc[ok].astype(float)); out["diff_parsed_only"] = [float(d.mean())] + ci(d)
worst = fc_inc | ~ok; d2 = same_yn.astype(float) - worst.astype(float); out["diff_worst_case_unparsed_inconsistent"] = [float(d2.mean())] + ci(d2)
# prompts: show the two templates with the question removed
ex_yn = yn[0]["prompt"]; ex_fc = fc[0]["prompt"]
out["prompt_yn_example"] = ex_yn; out["prompt_fc_example"] = ex_fc
out["system_prompts"] = list({r.get("system") or "" for r in R})
json.dump(out, open(os.path.join(HERE, "v_l4.json"), "w"), indent=1)
for k, v in out.items(): print(k, v)
