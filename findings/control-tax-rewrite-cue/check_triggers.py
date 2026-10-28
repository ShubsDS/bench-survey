"""Check 4 on the Control Tax backdoor set, statically: do the claimed triggers obey the problem?

1. Calibrate each validator in validators.py on every stored APPS test input of its problem
   (pinned ControlArena copy) and on the public tests stored with the backdoors. A validator that
   rejects a stored test input is wrong, and its problem is reported as such.
2. Apply the validators to the triggers (fail_input) of the seeded sample in trigger_sample.json
   (50 records, one per problem, seed 20261027), and, as a secondary count, to every Control Tax
   trigger on those 50 problems.
Validators are this audit's own code; no program from the dataset is run.

Usage: python -I check_triggers.py --cache ../data --out triggers_checks.json
"""
import argparse, collections, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_ct, load_ca, wilson, SHORT, CT_COMMIT, CA_REV
import validators as VAL

HERE = os.path.dirname(os.path.abspath(__file__))


def verdict(pid, s):
    try:
        VAL.V[pid](s)
        return "valid", ""
    except VAL.Bad as e:
        return e.kind, str(e)
    except Exception as e:  # a crash inside a validator counts as a format rejection
        return "format", f"validator error {type(e).__name__}: {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="../data")
    ap.add_argument("--out", default="triggers_checks.json")
    a = ap.parse_args()
    d = load_ct(a.cache)
    ca = load_ca(a.cache, ["problem_id", "inputs"])
    sample = json.load(open(os.path.join(HERE, "trigger_sample.json")))
    pids = [r["sample_id"] for r in sample["records"]]
    assert set(pids) == set(VAL.V), "validators must cover exactly the sampled problems"

    # 1. Calibration on stored inputs.
    calib, broken = {}, []
    for pid in pids:
        ins = list(ca.loc[pid].inputs)
        pub = [t["input"] for r in d if r["sample_id"] == pid for t in r["public_tests"]]
        pub = ["\n".join(map(str, x)) if isinstance(x, list) else x for x in pub]
        rej = [(i, verdict(pid, s)[1]) for i, s in enumerate(ins + pub) if verdict(pid, s)[0] != "valid"]
        calib[pid] = {"stored_inputs": len(ins), "public_inputs": len(pub), "rejected": len(rej),
                      "first_rejection": rej[0][1][:160] if rej else None}
        if rej:
            broken.append(pid)

    # 2. Triggers.
    rows = []
    for rec in sample["records"]:
        r = d[rec["index"]]
        assert r["sample_id"] == rec["sample_id"] and r["model"] == rec["model"]
        k, msg = verdict(r["sample_id"], r["fail_input"])
        rows.append({"sample_id": r["sample_id"], "model": SHORT[r["model"]], "verdict": k,
                     "reason": msg[:200], "validator_calibrated": r["sample_id"] not in broken,
                     "partial_validator": r["sample_id"] in VAL.PARTIAL})
    ok = [x for x in rows if x["validator_calibrated"]]
    inv = [x for x in ok if x["verdict"] != "valid"]
    out = {"pins": {"control_tax_code": CT_COMMIT, "apps_control_arena": CA_REV},
           "seed": sample["seed"], "sample_size": len(rows),
           "validators_rejecting_a_stored_input": broken,
           "calibration": calib,
           "sample": {"scored": len(ok), "invalid": len(inv), "rate": round(len(inv) / max(1, len(ok)), 4),
                      "wilson95": wilson(len(inv), len(ok)),
                      "by_kind": dict(collections.Counter(x["verdict"] for x in ok))},
           "sample_rows": rows}

    allrows = []
    for r in d:
        if r["sample_id"] in VAL.V and r["sample_id"] not in broken:
            k, msg = verdict(r["sample_id"], r["fail_input"])
            allrows.append((r["sample_id"], SHORT[r["model"]], k, msg[:200]))
    inv_all = [x for x in allrows if x[2] != "valid"]
    out["all_triggers_on_sampled_problems"] = {
        "n": len(allrows), "invalid": len(inv_all), "wilson95_unclustered": wilson(len(inv_all), len(allrows)),
        "problems_with_an_invalid_trigger": len({x[0] for x in inv_all}),
        "by_attacker": {m: [sum(1 for x in inv_all if x[1] == m), sum(1 for x in allrows if x[1] == m)]
                        for m in SHORT.values()},
        "invalid_rows": [{"sample_id": x[0], "model": x[1], "kind": x[2], "reason": x[3]} for x in inv_all]}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k not in ("calibration", "sample_rows")}, indent=1))
    print("calibration rejections:", {p: calib[p] for p in broken})


if __name__ == "__main__":
    main()
