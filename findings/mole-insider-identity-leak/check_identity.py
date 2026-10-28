"""Check 5 (split leakage by account identity) on MOLE, from pinned revisions.

MOLE's insiders are a fixed list of 38 accounts (bootstrap/insider_assignment.yaml) that attack
on several days each, in every corpus. The paper's day split (12 train / 3 val / 15 test days,
collusion accounts removed, 2,106 test account-days with 45 executed positives on GPT-5.3
single-day) keeps the same insider accounts on both sides. This script measures how far
"who" alone goes on the test days, with nulls, and whether the label-free features that the
paper's monitor search uses read the day or the account.

Reads parquet tables and YAML/text from the pins; never runs released code.

Usage: python -I check_identity.py [--cache DIR] [--out identity_checks.json] [--perms N]
"""
import argparse, sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common, pins

# Published numbers on the same test set (GPT-5.3 single-day, 12/3/15, no collusion accounts).
PAPER = {
    "R@10/day": {"Claude Opus 4.7 (best)": 0.533, "GPT-5.5": 0.511, "median of 40 monitors": 0.367,
                 "GPT-4.1": 0.222, "FACADE": 0.222, "peer-fit": 0.178, "z-score": 0.156},
    "budget-AUC": {"GPT-5.5": 0.391, "GPT-4.1": 0.187, "search iteration 53 (GPT-4.1 cost)": 0.298,
                   "search best reported (iteration 165)": 0.489},
    "source": "arXiv 2609.06966v1, Figure 4, Table 21 and Table 22 / Appendix L.1",
}


def account_days(split, cache, cols=("account", "ts", "service", "action")):
    a = pd.read_parquet(pins.audit(split, cache), columns=list(cols))
    a["date"] = a.ts.str[:10]
    return a


def label_join(ad, split, cache):
    lab = pd.read_parquet(pins.label(split, cache))
    ad = ad.merge(lab[["account", "date", "outcome"]], on=["account", "date"], how="left")
    ad["pos"] = (ad.outcome == "executed").astype(int)
    return ad


def rarity_features(a, train_days):
    """Paper's action rarity (Appendix L.3): sum of the inverse training-period frequencies of
    the three rarest distinct actions in the account-day. Unseen actions count as frequency 0.5."""
    a = a.assign(act=a.service + "." + a.action)
    freq = a[a.date.isin(train_days)].act.value_counts()
    a["inv"] = 1.0 / a.act.map(freq).fillna(0.5)
    g = a.drop_duplicates(["account", "date", "act"]).groupby(["account", "date"])
    out = g.inv.apply(lambda s: np.sort(s.values)[::-1][:3].sum()).rename("rarity").to_frame()
    out["distinct_actions"] = g.act.size()
    # sequence novelty: action bigrams absent from the account's preceding 7 days
    a = a.sort_values(["account", "ts"])
    a["prev"] = a.groupby(["account", "date"]).act.shift()
    a["bigram"] = a.prev + ">" + a.act
    bg = a.dropna(subset=["bigram"]).groupby(["account", "date"]).bigram.apply(set)
    days = sorted(a.date.unique())
    idx = {d: i for i, d in enumerate(days)}
    nov = {}
    for acct, sub in bg.groupby(level=0):
        sets = {d: s for (_, d), s in sub.items()}
        for d, s in sets.items():
            hist = set().union(*[sets.get(days[j], set()) for j in range(max(0, idx[d] - 7), idx[d])])
            nov[(acct, d)] = len(s - hist)
    out["sequence_novelty"] = pd.Series(nov)
    return out.reset_index()


def evaluate(te, score, perms, rng, accounts_null=True):
    s = np.asarray(score, dtype=float)
    res = {"auroc": common.auroc(te.pos, s)}
    res["budget_auc"], res["r10"] = common.mean_over_seeds(te, s)
    if perms:
        # null 1: labels shuffled within each test day
        nl = []
        for _ in range(perms):
            y = te.groupby("date").pos.transform(lambda x: rng.permutation(x.values)).values
            nl.append(common.auroc(y, s))
        res["null_label_shuffle_auroc"] = {"mean": round(float(np.mean(nl)), 3),
                                           "p95": round(float(np.quantile(nl, 0.95)), 3)}
        if accounts_null:
            # null 2: the account -> score map permuted across accounts (keeps how many accounts
            # are flagged, breaks which ones)
            accts = te.account.unique()
            per = pd.Series(s, index=te.index).groupby(te.account).first()
            na = []
            for _ in range(perms):
                m = dict(zip(accts, rng.permutation(per.reindex(accts).values)))
                na.append(common.auroc(te.pos, te.account.map(m).values))
            res["null_account_permutation_auroc"] = {"mean": round(float(np.mean(na)), 3),
                                                     "p95": round(float(np.quantile(na, 0.95)), 3)}
    return res


def paper_split(split, cache, asg, perms, rng, features=True):
    coll = set(asg["collusion"]); shadow = set(asg["shadow"]); insiders = set(asg["solo"]) | shadow
    a = account_days(split, cache)
    a = a[~a.account.isin(coll)]
    days = sorted(a.date.unique())
    train, val, test = days[:12], days[12:15], days[15:]
    ad = a.groupby(["account", "date"]).size().rename("events").reset_index()
    ad = label_join(ad, split, cache)
    tr, va, te = (ad[ad.date.isin(x)] for x in (train, val, test))
    te = te.copy()
    trpos = set(tr[tr.pos == 1].account)
    trpos_nonheld = trpos - shadow
    out = {"split": split, "days": len(days), "test_account_days": len(te), "test_positives": int(te.pos.sum()),
           "train_positives": int(tr.pos.sum()), "val_positives": int(va.pos.sum())}
    tpa = set(te[te.pos == 1].account); vpa = set(va[va.pos == 1].account)
    out["test_positive_accounts"] = len(tpa)
    out["test_positive_accounts_with_train_positive"] = len(tpa & trpos)
    out["test_positives_on_accounts_with_train_positive"] = int(te[te.pos == 1].account.isin(trpos).sum())
    out["val_positive_accounts"] = len(vpa)
    out["val_positive_accounts_also_test_positive"] = len(vpa & tpa)
    priors = {
        "who_executed_on_a_train_day": te.account.isin(trpos).astype(int),
        "who_executed_on_a_train_day_non_heldout_only": te.account.isin(trpos_nonheld).astype(int),
        "who_listed_in_insider_assignment_yaml": te.account.isin(insiders).astype(int),
    }
    out["priors"] = {k: evaluate(te, v.values, perms, rng) for k, v in priors.items()}
    if features:
        f = rarity_features(a, set(train))
        te = te.merge(f, on=["account", "date"], how="left")
        te[["rarity", "distinct_actions", "sequence_novelty"]] = te[["rarity", "distinct_actions", "sequence_novelty"]].fillna(0)
        out["label_free_features"] = {}
        neg = te[te.pos == 0]
        for c in ["rarity", "distinct_actions", "sequence_novelty"]:
            r = evaluate(te, te[c].values, perms, rng, accounts_null=False)
            # does the feature read the account? AUROC for insider-account vs other, on negative days only
            r["auroc_insider_account_on_negative_days"] = common.auroc(neg.account.isin(insiders).astype(int), neg[c])
            # the "what" part: executed vs other days within the 30 insider accounts only
            ins = te[te.account.isin(insiders)]
            r["auroc_within_insider_accounts"] = common.auroc(ins.pos, ins[c])
            out["label_free_features"][c] = r
        # how much a who-prior adds to a free feature (reciprocal-rank fusion within day, k=60)
        rr = lambda col: 1.0 / (60 + te.groupby("date")[col].rank(ascending=False, method="average"))
        te["who_label"] = priors["who_executed_on_a_train_day"].values
        te["who_assign"] = priors["who_listed_in_insider_assignment_yaml"].values
        out["fusion"] = {
            "rarity + who_executed_on_a_train_day": evaluate(te, (rr("rarity") + rr("who_label")).values, 0, rng),
            "rarity + who_listed_in_insider_assignment_yaml": evaluate(te, (rr("rarity") + rr("who_assign")).values, 0, rng),
        }
    return out


def earlier_setup(cache, perms, rng):
    """The earlier research pass: all 150 accounts, cut at the 16th of 30 days (50/50)."""
    a = account_days("gpt53_single_day", cache, cols=("account", "ts"))
    ad = label_join(a.groupby(["account", "date"]).size().rename("events").reset_index(), "gpt53_single_day", cache)
    days = sorted(ad.date.unique()); cut = days[len(days) // 2]
    tr, te = ad[ad.date < cut], ad[ad.date >= cut].copy()
    prior = te.account.isin(set(tr[tr.pos == 1].account)).astype(int).values
    r = evaluate(te, prior, perms, rng, accounts_null=False)
    return {"cut": cut, "train_positives": int(tr.pos.sum()), "test_positives": int(te.pos.sum()),
            "test_account_days": len(te), "auroc": r["auroc"], "null_label_shuffle_auroc": r["null_label_shuffle_auroc"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data")
    ap.add_argument("--out", default="identity_checks.json")
    ap.add_argument("--perms", type=int, default=200)
    args = ap.parse_args()
    rng = np.random.default_rng(0)
    asg = common.assignment(args.cache)
    labels = {s: pd.read_parquet(pins.label(s, args.cache)) for s in pins.SPLITS}
    ref = set(labels["gpt53_single_day"].account)
    res = {
        "pins": {"hf_dataset": f"forgelab/mole@{pins.HF_REV}", "code": f"aashiqmuhamed/mole@{pins.CODE_COMMIT}",
                 "paper": pins.PAPER},
        "paper_reference": PAPER,
        "insider_accounts_per_label_file": {s: {"accounts": int(d.account.nunique()),
                                                "subset_of_gpt53_single_day_insiders": set(d.account) <= ref}
                                            for s, d in labels.items()},
        "earlier_setup_gpt53_single_day": earlier_setup(args.cache, args.perms, rng),
        "paper_split_gpt53_single_day": paper_split("gpt53_single_day", args.cache, asg, args.perms, rng),
        "paper_split_kimi_k26_single_day": paper_split("kimi_k26_single_day", args.cache, asg, args.perms, rng,
                                                        features=False),
    }
    pins.dump(res, args.out)
    print(Path(args.out).read_text())


if __name__ == "__main__":
    main()
