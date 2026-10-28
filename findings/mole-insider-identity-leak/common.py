"""Shared loaders for the MOLE checks (reads data as text/tables; never runs released code)."""
import re
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
import pins


def assignment(cache):
    """Parse bootstrap/insider_assignment.yaml (pinned) into {group: {account: (threat, level)}}.
    A small line parser: the file is plain nested mappings with one account id per leaf."""
    text = pins.code("bootstrap/insider_assignment.yaml", cache).read_text()
    out = {"solo": {}, "collusion": {}, "shadow": {}}
    group = threat = level = None
    for line in text.splitlines():
        s = line.split("#", 1)[0].rstrip()
        if not s.strip():
            continue
        ind = len(s) - len(s.lstrip())
        key, _, val = s.strip().partition(":")
        key, val = key.strip().strip('"'), val.strip()
        if ind == 0:
            group = key if key in out else None
            continue
        if group is None:
            continue
        if ind == 2:
            threat = key
        elif ind == 4:
            level = key
            if val:
                out[group][val] = (threat, level)
        elif ind == 6 and val:
            out[group][val] = (threat, level)
    return out


def org_accounts(cache):
    """Per-account metadata from bootstrap/org_template.yaml (pinned): id, role, cohort, groups."""
    text = pins.code("bootstrap/org_template.yaml", cache).read_text()
    rows, cur, inlist = [], None, None
    for line in text.splitlines():
        m = re.match(r"^- id: (\S+)", line)
        if m:
            cur = {"account": m.group(1), "groups": []}
            rows.append(cur)
            inlist = None
            continue
        if cur is None:
            continue
        m2 = re.match(r"^  (\w+):\s*(.*)$", line)
        if m2:
            k, v = m2.group(1), m2.group(2).strip().strip('"')
            inlist = k if k == "groups" and not v else None
            if k in ("role", "cohort"):
                cur[k] = v
            continue
        m3 = re.match(r"^  - (\S+)$", line)
        if m3 and inlist == "groups":
            cur["groups"].append(m3.group(1))
    df = pd.DataFrame(rows).drop_duplicates("account")
    return df[df.cohort.notna()]


def auroc(y, s):
    y = np.asarray(y)
    if y.min() == y.max():
        return None
    return round(float(roc_auc_score(y, s)), 3)


def recall_at_k_per_day(df, score, k_values=range(1, 11), label="pos", day="date", seed=0):
    """Paper's R@K/day: for each day take the K highest-scoring accounts; recall pooled over days.
    Ties are broken at random (fixed seed), so a constant score gets chance recall."""
    rng = np.random.default_rng(seed)
    d = df[[day, label]].copy()
    d["s"] = np.asarray(score, dtype=float)
    d["tb"] = rng.random(len(d))
    d = d.sort_values([day, "s", "tb"], ascending=[True, False, False])
    d["rank"] = d.groupby(day).cumcount() + 1
    total = d[label].sum()
    return {k: float(d.loc[d["rank"] <= k, label].sum() / total) for k in k_values}


def budget_auc(df, score, **kw):
    r = recall_at_k_per_day(df, score, **kw)
    return round(float(np.mean(list(r.values()))), 3), round(r[10], 3)


def mean_over_seeds(df, score, seeds=range(20)):
    vals = [budget_auc(df, score, seed=s) for s in seeds]
    return round(float(np.mean([v[0] for v in vals])), 3), round(float(np.mean([v[1] for v in vals])), 3)
