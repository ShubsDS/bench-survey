"""Compare the validator's blind codes of 80 paper-era runs (hand_paper.csv) with run outcomes
(bypass or not, from summaries.json) and the auditor's regex labels (../data/paper_runs_full.csv).
Output: out_hand_paper.json"""
import csv, json, os, sys, collections
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(H)
sys.path.insert(0, H)
from vcommon import cached_json, run_outcome
key = json.load(open(os.path.join(R, "data/blind_paper_key.json")))
codes = {int(r["packet"]): r for r in csv.DictReader(open(os.path.join(H, "hand_paper.csv")))}
aud = {(r["log"], r["id"]): r for r in csv.DictReader(open(os.path.join(R, "data/paper_runs_full.csv")))}
tab = collections.Counter(); reasons = collections.Counter(); agree = 0; dis = []
for n, k in enumerate(key, 1):
    oc = {x["id"]: run_outcome(x) for x in cached_json(k["log"], "summaries.json")}[k["id"]]
    a = aud[(k["log"], str(k["id"]))]
    mine = codes[n]["tamper_after_warning"]
    reg = a["tamper_after_warn"] == "True"
    byp = oc == "bypass"
    tab[("bypass" if byp else "not_bypass", mine, "regex_T" if reg else "regex_-")] += 1
    if mine in ("Y", "N"):
        if (mine == "Y") == reg: agree += 1
        else: dis.append(dict(packet=n, model=k["model"], prompt=k["prompt"], id=k["id"], outcome=oc, mine=mine, regex=reg, kind=a.get("tamper_kind")))
    if byp:
        reasons[codes[n]["stated_reason"] or "none"] += 1
out = dict(n=len(key), table={"|".join(x): v for x, v in sorted(tab.items())}, agree_with_regex=agree,
           disagreements=dis, bypass_reason_codes=dict(reasons))
json.dump(out, open(os.path.join(H, "out_hand_paper.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
