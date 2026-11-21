"""Probe the 'could not' proxy. Usage: python -I ability_check.py <cases.csv> <scriptdir>"""
import sys; sys.path.insert(0, sys.argv[2])
import pandas as pd
from common_fc import TABLE20, REPO_FOUR
a = pd.read_csv(sys.argv[1], low_memory=False)
for c in ["security","saw","able","secure","c_never","c_couldnot","c_sawcould","untraced","follow","utility"]:
    a[c] = a[c].astype(str).map({"True":True,"False":False})
rows=[]
for p,g in a.groupby("pipeline"):
    it = g.groupby(["suite","injection_task"]).agg(able=("able","first"), succ=("security","sum"), n=("security","size"), saw=("saw","sum")).reset_index()
    unable = it[~it.able]
    rows.append(dict(pipeline=p, n_inj_unable=len(unable),
        unable_tasks_with_attack_success=int((unable.succ>0).sum()),
        attack_successes_on_unable_tasks=int(unable.succ.sum()),
        total_successes=int(g.security.sum()),
        couldnot_secure=int(g.c_couldnot.sum()),
        couldnot_secure_on_tasks_with_success=int(g[g.c_couldnot].merge(unable[unable.succ>0][["suite","injection_task"]]).shape[0]),
        couldnot_with_follow=int((g.c_couldnot & g.follow.fillna(False)).sum()),
        sawcould_with_follow=int((g.c_sawcould & g.follow.fillna(False)).sum()),
        never_saw_secure_utility_true=int((g.c_never & g.utility).sum()),
        never_saw_secure=int(g.c_never.sum()),
        never_saw_no_tool_calls=int((g.c_never & (g.n_calls==0)).sum()),
        saw_no_assistant_turn_after=int((g.saw & g.secure & ~g.asst_after_injection.astype(str).eq("True")).sum()),
    ))
t = pd.DataFrame(rows).set_index("pipeline").loc[TABLE20]
pd.set_option("display.width",250)
print(t.to_string())
print(t.sum().to_string())
# share of could-not that is on injection tasks the model DID achieve at least once under attack
t["couldnot_contradicted_share"] = t.couldnot_secure_on_tasks_with_success / t.couldnot_secure
print(t.loc[REPO_FOUR, ["couldnot_secure","couldnot_secure_on_tasks_with_success","couldnot_contradicted_share","couldnot_with_follow"]])
t.to_csv(sys.argv[1].replace("_cases.csv","_ability_check.csv"))
