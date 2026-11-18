"""Extract, per model and released flagged pair, the wrong answers on the lower-accuracy question
and the authors' pattern-autorater labels for each (answer_flipping_classification,
evidence_of_unfaithfulness), plus the pair-level categorization. Output: data/val_extract.json."""
import os, sys, glob, json
import yaml
HERE = os.path.dirname(__file__); ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
from v_sample import DIRS
L = yaml.CSafeLoader
out = {}
for f in sorted(glob.glob(os.path.join(ROOT, "data/faith/*.yaml"))):
    md, rest = os.path.basename(f).split("__", 1)
    prop = rest.replace("_non-ambiguous-hard-2.yaml", "")
    d = yaml.load(open(f), Loader=L)
    pp = os.path.join(ROOT, "data/pat", f"{prop}_non-ambiguous-hard-2__{md}.yaml")
    P = yaml.load(open(pp), Loader=L)["pattern_analysis_by_qid"] if os.path.exists(pp) else {}
    for qid, q in d["questions_by_qid"].items():
        m = q["metadata"]
        a = P.get(qid) or {}
        lab = {}
        for side in ("q1_analysis", "q2_analysis"):
            for rid, r in ((a.get(side) or {}).get("responses") or {}).items():
                lab[rid] = dict(flip=r.get("answer_flipping_classification"),
                                ev=r.get("evidence_of_unfaithfulness"), lack=r.get("lack_of_information"), side=side)
        wrong = {rid: lab.get(rid, {}) for rid in q["unfaithful_responses"]}
        out.setdefault(DIRS[md], {})[qid] = dict(
            grp=f"{prop}|{m['comparison']}", key=m["answer"], n_wrong=len(wrong),
            n_correct=len(q["faithful_responses"]), n_unknown=len(q["unknown_responses"]),
            n_total_low=len(m["q1_all_responses"]), pair_cat=a.get("categorization_for_pair"),
            analysed=bool(a), n_analysed_q1=len(((a.get("q1_analysis") or {}).get("responses") or {})),
            wrong=wrong)
json.dump(out, open(os.path.join(ROOT, "data/val_extract.json"), "w"))
for mm in out:
    nw = sum(v["n_wrong"] for v in out[mm].values())
    nf = sum(1 for v in out[mm].values() for r in v["wrong"].values() if r.get("flip") == "YES")
    nl = sum(1 for v in out[mm].values() for r in v["wrong"].values() if r.get("flip") in ("YES", "NO"))
    print(mm, len(out[mm]), "wrong", nw, "labelled", nl, "flip", nf)
