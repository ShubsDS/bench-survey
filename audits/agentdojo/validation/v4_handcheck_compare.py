"""Validator step 4: compare blind hand labels (handcheck_labels.json) with the auditor's automatic
labels (../data/cases.parquet columns exposed, redacted, follow_exec, written by ../scripts/01_extract.py;
read as data, the auditor's code is not imported) and with the validator's own rules (validation_cases.json).

Run: ../data/.venv/bin/python -I v4_handcheck_compare.py
Writes block 'handcheck' of validation.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd

from common_v import AUDIT, HERE, save

S = json.load(open(os.path.join(HERE, "handcheck_sample.json")))
L = {x["id"]: x for x in json.load(open(os.path.join(HERE, "handcheck_labels.json")))["labels"]}
aud = pd.read_parquet(os.path.join(AUDIT, "data", "cases.parquet"))
aud = aud[aud.attack == "important_instructions"].set_index(["pipeline", "suite", "user_task", "injection_task"])
mine = {(r["pipeline"], r["suite"], r["ut"], r["inj"]): r
        for r in json.load(open(os.path.join(AUDIT, "data", "validation_cases.json")))["cases"]}

rows = []
for s in S:
    k = (s["pipeline"], s["suite"], s["ut"], s["inj"])
    a = aud.loc[k]
    m = mine[k]
    h = L[s["id"]]
    rows.append(dict(id=s["id"], pipeline=k[0], suite=k[1], ut=k[2], inj=k[3],
                     hand_E=h["exposed"], hand_F=h["acted"],
                     aud_E=int(a.exposed), aud_F=int(bool(a.follow_exec)),
                     val_E=int(m["exposed"]), val_F=int(m["acted"]), security=int(m["security"]), note=h["note"]))
df = pd.DataFrame(rows)


def agree(x, y, sub=None):
    d = df if sub is None else df[sub]
    tp = int(((d[x] == 1) & (d[y] == 1)).sum())
    return dict(n=len(d), agree=int((d[x] == d[y]).sum()), rate=round(float((d[x] == d[y]).mean()), 4),
                hand_pos=int(d[x].sum()), auto_pos=int(d[y].sum()), both_pos=tp,
                disagreements=d[d[x] != d[y]].id.tolist())


out = dict(n=len(df),
           exposure_vs_auditor=agree("hand_E", "aud_E"), follow_vs_auditor=agree("hand_F", "aud_F"),
           exposure_vs_validator_rule=agree("hand_E", "val_E"), follow_vs_validator_rule=agree("hand_F", "val_F"),
           follow_vs_stored_security=agree("hand_F", "security"),
           by_suite={s: dict(E=agree("hand_E", "aud_E", df.suite == s)["rate"], F=agree("hand_F", "aud_F", df.suite == s)["rate"],
                             n=int((df.suite == s).sum())) for s in sorted(df.suite.unique())},
           disagreement_rows=df[(df.hand_E != df.aud_E) | (df.hand_F != df.aud_F) | (df.hand_F != df.val_F)].to_dict("records"))
save("handcheck", out)
print(json.dumps({k: v for k, v in out.items() if k != "disagreement_rows"}, indent=1))
for r in out["disagreement_rows"]:
    print(r)

# Full-population agreement between the auditor's rules and the validator's independently written rules
full = []
for k, m in mine.items():
    a = aud.loc[k]
    full.append((k[1], k[3], int(m["exposed"]), int(a.exposed), int(m["acted"]), int(bool(a.follow_exec))))
F = pd.DataFrame(full, columns=["suite", "inj", "vE", "aE", "vF", "aF"])
dis = F[F.vF != F.aF].groupby(["suite", "inj"]).size().to_dict()
pop = dict(n=len(F), exposure_agree=int((F.vE == F.aE).sum()), follow_agree=int((F.vF == F.aF).sum()),
           follow_val_only=int(((F.vF == 1) & (F.aF == 0)).sum()), follow_aud_only=int(((F.vF == 0) & (F.aF == 1)).sum()),
           follow_disagreements_by_injection_task={f"{s}/{i}": int(n) for (s, i), n in dis.items()})
save("rule_agreement_population", pop)
print(json.dumps(pop, indent=1))
