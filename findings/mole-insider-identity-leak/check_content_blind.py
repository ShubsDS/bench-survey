"""Check 1 (content-blind baselines) on MOLE's GPT-5.3 single-day corpus, from pinned revisions.

Population and split follow the paper's RQ2/RQ5 setup: collusion accounts removed, days 1-12
train, 13-15 validation, 16-30 test (2,106 test account-days, 45 executed positives). Each
baseline ranks accounts within each test day; we report AUROC, budget-AUC (mean R@K/day over
K = 1..10) and R@10/day, with a within-day label-shuffle null. Higher score = more suspicious;
an AUROC below 0.5 means the reverse direction separates.

Features never read event arguments, resource names, message text or tool results:
- activity volume: events, sessions, total bytes, error rate
- time of day: first and last event (simulated clock), active span
- session metadata from the transcripts table: turns, input and output tokens, max-turn aborts
- account metadata: org cohort (bootstrap/org_template.yaml)
plus a logistic regression on all of them fitted on the training days' labels.

Reads tables only; never runs released code.

Usage: python -I check_content_blind.py [--cache DIR] [--out content_blind_checks.json] [--perms N]
"""
import argparse, sys
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common, pins
from check_identity import PAPER

SPLIT = "gpt53_single_day"


def build(cache, asg):
    coll = set(asg["collusion"])
    a = pd.read_parquet(pins.audit(SPLIT, cache), columns=["account", "ts", "exit_code", "bytes", "task_id"])
    a = a[~a.account.isin(coll)]
    a["date"] = a.ts.str[:10]
    t = pd.to_datetime(a.ts, format="ISO8601", utc=True)
    a["hour"] = t.dt.hour + t.dt.minute / 60 + t.dt.second / 3600
    g = a.groupby(["account", "date"])
    ad = g.agg(events=("ts", "size"), sessions=("task_id", "nunique"), bytes=("bytes", "sum"),
               error_rate=("exit_code", lambda x: float((x != 0).mean())),
               first_event_hour=("hour", "min"), last_event_hour=("hour", "max")).reset_index()
    ad["active_span_hours"] = ad.last_event_hour - ad.first_event_hour
    tr = pq.read_table(pins.fetch(f"data/transcripts/{SPLIT}/0000.parquet", cache),
                       columns=["account", "sim_ts", "turn_count", "input_tokens", "output_tokens", "aborted_reason"]).to_pandas()
    tr["date"] = tr.sim_ts.str[:10]
    tr["max_turns"] = tr.aborted_reason.fillna("").eq("max_turns")
    ts = tr.groupby(["account", "date"]).agg(turns=("turn_count", "sum"), max_session_turns=("turn_count", "max"),
                                             input_tokens=("input_tokens", "sum"), output_tokens=("output_tokens", "sum"),
                                             max_turn_aborts=("max_turns", "sum")).reset_index()
    ad = ad.merge(ts, on=["account", "date"], how="left")
    org = common.org_accounts(cache)[["account", "cohort"]]
    ad = ad.merge(org, on="account", how="left")
    for c in ["focal", "background", "holdout"]:
        ad[f"cohort_{c}"] = (ad.cohort == c).astype(int)
    lab = pd.read_parquet(pins.label(SPLIT, cache))
    ad = ad.merge(lab[["account", "date", "outcome"]], on=["account", "date"], how="left")
    ad["pos"] = (ad.outcome == "executed").astype(int)
    return ad


FEATURES = ["events", "sessions", "bytes", "error_rate", "first_event_hour", "last_event_hour", "active_span_hours",
            "turns", "max_session_turns", "input_tokens", "output_tokens", "max_turn_aborts",
            "cohort_focal", "cohort_background", "cohort_holdout"]


def shuffle_null(te, s, perms, rng):
    v = [common.auroc(te.groupby("date").pos.transform(lambda x: rng.permutation(x.values)).values, s)
         for _ in range(perms)]
    return {"mean": round(float(np.mean(v)), 3), "p95": round(float(np.quantile(v, 0.95)), 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="content_blind_checks.json")
    ap.add_argument("--perms", type=int, default=200)
    args = ap.parse_args()
    rng = np.random.default_rng(0)
    asg = common.assignment(args.cache)
    ad = build(args.cache, asg)
    days = sorted(ad.date.unique())
    tr, te = ad[ad.date.isin(days[:12])].copy(), ad[ad.date.isin(days[15:])].copy()
    res = {"pins": {"hf_dataset": f"forgelab/mole@{pins.HF_REV}", "code": f"aashiqmuhamed/mole@{pins.CODE_COMMIT}"},
           "paper_reference": PAPER,
           "test_account_days": len(te), "test_positives": int(te.pos.sum()), "train_positives": int(tr.pos.sum()),
           "features": {}}
    for f in FEATURES:
        s = te[f].fillna(0).values.astype(float)
        b, r10 = common.mean_over_seeds(te, s)
        res["features"][f] = {"auroc": common.auroc(te.pos, s), "budget_auc": b, "r10": r10,
                              "null_label_shuffle_auroc": shuffle_null(te, s, args.perms, rng)}
    # fitted content-blind model: train-day labels only
    X_tr, X_te = tr[FEATURES].fillna(0).values, te[FEATURES].fillna(0).values
    sc = StandardScaler().fit(X_tr)
    m = LogisticRegression(max_iter=2000, class_weight="balanced").fit(sc.transform(X_tr), tr.pos)
    s = m.predict_proba(sc.transform(X_te))[:, 1]
    b, r10 = common.mean_over_seeds(te, s)
    null = []
    for _ in range(min(args.perms, 100)):
        mm = LogisticRegression(max_iter=2000, class_weight="balanced").fit(sc.transform(X_tr), rng.permutation(tr.pos.values))
        null.append(common.auroc(te.pos, mm.predict_proba(sc.transform(X_te))[:, 1]))
    res["fitted_logistic_all_features"] = {
        "auroc": common.auroc(te.pos, s), "budget_auc": b, "r10": r10,
        "null_shuffled_train_labels_auroc": {"mean": round(float(np.mean(null)), 3), "p95": round(float(np.quantile(null, 0.95)), 3)},
        "coefficients": dict(zip(FEATURES, np.round(m.coef_[0], 3).tolist()))}
    best = max(res["features"].items(), key=lambda kv: kv[1]["budget_auc"])
    res["best_single_feature_by_budget_auc"] = {"feature": best[0], **best[1]}
    pins.dump(res, args.out)
    print(Path(args.out).read_text())


if __name__ == "__main__":
    main()
