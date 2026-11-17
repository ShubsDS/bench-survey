"""C3 (b) and (c) of prereg.md.

(b) ControlArena AgentDojo corpus (adityaasinha28/control_arena_agentdojo @ a0f1e213, sha256 pinned):
    in-corpus `full_trajectory_monitor` score vs the attacker IBAN (US133000000121212121212) in the
    transcript. ControlArena's full_trajectory_monitor shows tool calls with their arguments
    (control-arena@28b7d72 `control_arena/scorers/_utils.py:53,56`, include_cot default True at
    `_full_trajectory_monitor.py:49`), so the IBAN in the agent's own call reaches the monitor.
    Placebo: a legitimate payee IBAN of similar prevalence (GB29NWBK60161331926819).
(c) CTRL-ALT-DECEIT per-run monitor tables (TeunvdWeij/ctrl-alt-deceit @ 0a12070): cue = a sandbagging
    run's test score below the minimum Regular score on the same task. AUROC of each monitor on
    cue-free sandbagging runs vs all Regular runs; task-cluster bootstrap.
Only aggregates are written. Usage: python -I scripts/effect_other.py data results_other.json
"""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
import pandas as pd
from mrt_lib import auroc, threshold_1pct, ci

data, outp = Path(sys.argv[1]), Path(sys.argv[2])
B = 2000
rng = np.random.default_rng(0)
res = {"B": B, "seed": 0}

# ---------------- (b) AgentDojo ----------------
P = data / "ca/control_arena_agentdojo.parquet"
assert hashlib.sha256(P.read_bytes()).hexdigest() == "5ceb33f1116b9c317b98be1ddcfb7dddca300482ca45736faf291b0796ad5c33"
df = pd.read_parquet(P)
md = pd.json_normalize(df["trajectory_data"].map(lambda x: json.loads(x)["metadata"]))
d = pd.DataFrame({"y": df.ground_truth.astype(int).values, "task": md.main_task_name.values,
                  "inj": md.side_task_name.fillna("").values,
                  "score": pd.to_numeric(md.full_trajectory_monitor, errors="coerce").values,
                  "iban": df.transcript.str.contains("US133000000121212121212", regex=False).values,
                  "placebo": df.transcript.str.contains("GB29NWBK60161331926819", regex=False).values})
d = d.dropna(subset=["score"])


def ad_stats(x, feat):
    neg = x[x.y == 0].score.values; pos = x[x.y == 1]
    thr = threshold_1pct(neg, pos.score.values)
    return {"auroc_all": auroc(neg, pos.score.values), "auroc_cue": auroc(neg, pos[pos[feat]].score.values),
            "auroc_cue_free": auroc(neg, pos[~pos[feat]].score.values),
            "tpr_cue": float((pos[pos[feat]].score >= thr).mean()), "tpr_cue_free": float((pos[~pos[feat]].score >= thr).mean()),
            "fpr": float((neg >= thr).mean()), "n_cue": int(pos[feat].sum()), "n_cue_free": int((~pos[feat]).sum()),
            "n_neg": int(len(neg))}


def ad_boot(feat):
    tasks = d.task.unique(); g = {t: d[d.task == t] for t in tasks}
    v = {k: [] for k in ("auroc_all", "auroc_cue", "auroc_cue_free", "tpr_cue", "tpr_cue_free")}
    for _ in range(B):
        x = pd.concat([g[t] for t in rng.choice(tasks, len(tasks))])
        s = ad_stats(x, feat)
        for k in v:
            if not np.isnan(s[k]): v[k].append(s[k])
    return {k: ci(x) for k, x in v.items()}


ad = {"rows_with_score": int(len(d)), "positives_with_attacker_iban": int(d[(d.y == 1)].iban.sum()),
      "negatives_with_attacker_iban": int(d[(d.y == 0)].iban.sum()),
      "positives_by_injection_task_with_iban": {k: [int(g.iban.sum()), int(len(g))] for k, g in d[d.y == 1].groupby("inj")}}
for feat in ("iban", "placebo"):
    s = ad_stats(d, feat)
    ad[feat] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items()}
    ad[feat]["ci_task"] = ad_boot(feat)
neg = d[d.y == 0].score.values
ad["auroc_by_injection_task"] = {k: round(auroc(neg, g.score.values), 3) for k, g in d[d.y == 1].groupby("inj")}
ad["note"] = ("All positives whose injection task names the IBAN contain it; the only IBAN-free positives are injection_task_7 "
              "(password change). So IBAN-free vs IBAN-present compares attack types, not cue presence within one attack.")
res["agentdojo"] = ad

# ---------------- (c) CTRL-ALT-DECEIT ----------------
MON = {"general (paper 0.60)": "default_system", "sandbagging-specific (paper 0.90)": "teun_sandbagging_specific_monitor_v1",
       "general with hint": "sandbagging_hint_full_trajectory"}
frames = {}
for name, stem in MON.items():
    x = pd.read_csv(data / f"cad/{stem}.csv")
    x["key"] = x.log_location.str.split("/").str[:2].str.join("/") + "|" + x.sample_id + "|" + x.sample_epoch.astype(str)
    frames[name] = x.set_index("key")
base = frames[next(iter(MON))][["mode", "task", "task_score"]].copy()
for name, x in frames.items():
    base[name] = x.monitor_score.reindex(base.index)
base["y"] = (base["mode"] == "sandbagging").astype(int)
thr = {t["competition"]: t for t in json.loads((data / "cad/medal_thresholds_results.json").read_text())}
cue = []
for _, r in base.iterrows():
    reg = base[(base.task == r.task) & (base.y == 0)].task_score.values
    lower = thr[r.task]["lower_is_better"]
    if r.y == 0 or reg.size == 0:
        cue.append(False); continue
    cue.append(bool(r.task_score > reg.max()) if lower else bool(r.task_score < reg.min()))
base["cue"] = cue
base = base[base.task.isin(set(base[base.y == 1].task))]  # tasks with sandbagging runs


def cad_stats(x, m):
    neg = x[x.y == 0][m].values; pos = x[x.y == 1]
    t = threshold_1pct(neg, pos[m].values)
    return {"auroc_all": auroc(neg, pos[m].values), "auroc_cue": auroc(neg, pos[pos.cue][m].values),
            "auroc_cue_free": auroc(neg, pos[~pos.cue][m].values),
            "tpr_cue": float((pos[pos.cue][m] >= t).mean()), "tpr_cue_free": float((pos[~pos.cue][m] >= t).mean()),
            "n_cue": int(pos.cue.sum()), "n_cue_free": int((~pos.cue).sum()), "n_regular": int(len(neg))}


cad = {"tasks": int(base.task.nunique()), "sandbagging_runs": int(base.y.sum()),
       "sandbagging_runs_below_all_own_regular": int(base[base.y == 1].cue.sum())}
tasks = base.task.unique(); g = {t: base[base.task == t] for t in tasks}
for m in MON:
    s = cad_stats(base, m)
    e = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items()}
    v = {k: [] for k in ("auroc_all", "auroc_cue_free", "auroc_cue")}
    for _ in range(B):
        x = pd.concat([g[t] for t in rng.choice(tasks, len(tasks))])
        ss = cad_stats(x, m)
        for k in v:
            if not np.isnan(ss[k]): v[k].append(ss[k])
    e["ci_task"] = {k: ci(x) for k, x in v.items()}
    # within-task: mean suspicion of cue minus cue-free sandbagging runs, weights = smaller stratum
    num = den = 0.0
    for t, x in base[base.y == 1].groupby("task"):
        a, b = x[x.cue][m].values, x[~x.cue][m].values
        if len(a) and len(b):
            w = min(len(a), len(b)); num += w * (a.mean() - b.mean()); den += w
    e["within_task_diff_cue_minus_free"] = round(num / den, 3) if den else None
    cad[m] = e
res["ctrl_alt_deceit"] = cad
outp.write_text(json.dumps(res, indent=1) + "\n")
print(json.dumps(res, indent=1))
