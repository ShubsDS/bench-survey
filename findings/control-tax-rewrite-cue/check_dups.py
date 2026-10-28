"""Check 5 on the Control Tax backdoor set: duplicates, leakage, ids, and the ControlArena join.

Reads the pinned Control Tax JSON and the pinned RoganInglis/apps-control-arena shards as text.
Never runs any program.

Usage: python -I check_dups.py --cache ../data --out dups_checks.json
"""
import argparse, ast, collections, difflib, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)
import numpy as np
from common import load_ct, load_ca, normalise, unwrap, SHORT, CT_COMMIT, CA_REV, CT_JSON_SHA256

TOK = re.compile(r"[A-Za-z_]\w*|\d+|\S")


def toks(c):
    return TOK.findall(c)


def jacc(a, b):
    a, b = set(a), set(b)
    return len(a & b) / max(1, len(a | b))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="../data")
    ap.add_argument("--out", default="dups_checks.json")
    a = ap.parse_args()
    d = load_ct(a.cache)
    ca = load_ca(a.cache, ["problem_id", "question", "inputs", "solutions", "backdoors", "difficulty"])
    out = {"pins": {"control_tax_code": CT_COMMIT, "control_tax_json_sha256": CT_JSON_SHA256,
                    "apps_control_arena": CA_REV}, "n_records": len(d)}

    # 1. Keys and exact duplicates inside the release.
    key = collections.Counter((r["sample_id"], r["model"]) for r in d)
    out["duplicate_problem_model_keys"] = sum(v > 1 for v in key.values())
    out["n_problems"] = len({r["sample_id"] for r in d})
    out["backdoors_per_problem"] = dict(sorted(collections.Counter(
        collections.Counter(r["sample_id"] for r in d).values()).items()))
    cc = collections.defaultdict(set)
    for r in d:
        cc[r["sample_id"]].add(r["correct_code"])
    out["problems_with_more_than_one_benign_program"] = sum(len(v) > 1 for v in cc.values())
    out["benign_distinct_programs"] = sum(len(v) for v in cc.values())

    norm_b = [normalise(r["backdoored_code"]) for r in d]
    norm_c = [normalise(r["correct_code"]) for r in d]
    out["backdoor_equals_its_benign_after_normalising"] = sum(x == y for x, y in zip(norm_b, norm_c))
    byprob = collections.defaultdict(list)
    for i, r in enumerate(d):
        byprob[r["sample_id"]].append(i)
    same_prob_dup = 0
    groups = 0
    for pid, ix in byprob.items():
        c = collections.Counter(norm_b[i] for i in ix)
        same_prob_dup += sum(v - 1 for v in c.values() if v > 1)
        groups += sum(1 for v in c.values() if v > 1)
    out["backdoors_identical_to_another_attackers_backdoor_same_problem"] = same_prob_dup
    out["groups_of_identical_backdoors"] = groups
    owner = collections.defaultdict(set)
    for i, x in enumerate(norm_b):
        owner[x].add(d[i]["sample_id"])
    out["backdoors_identical_across_different_problems"] = sum(1 for x in norm_b if len(owner[x]) > 1)

    # 2. How much of each backdoor is its benign program: the edit size.
    sim, changed, rel = [], [], []
    for x, y in zip(norm_b, norm_c):
        tb, tc = toks(x), toks(y)
        sim.append(jacc(tb, tc))
        sm = difflib.SequenceMatcher(a=tc, b=tb, autojunk=False)
        rel.append(sm.ratio())
        lc, lb = y.splitlines(), x.splitlines()
        changed.append(sum(1 for op in difflib.ndiff(lc, lb) if op[:2] in ("+ ", "- ")))
    rel = np.array(rel); changed = np.array(changed)
    out["edit_size"] = {
        "token_sequence_similarity_median": round(float(np.median(rel)), 3),
        "share_similarity_at_least_0.9": round(float((rel >= 0.9).mean()), 4),
        "share_similarity_below_0.5": round(float((rel < 0.5).mean()), 4),
        "changed_lines_median": int(np.median(changed)),
        "changed_lines_p90": int(np.percentile(changed, 90)),
        "by_attacker_similarity_median": {SHORT[m]: round(float(np.median(rel[[r["model"] == m for r in d]])), 3)
                                          for m in SHORT},
    }

    # 3. Triggers: shared across attackers, equal to a shown public test, equal to a stored test.
    def tnorm(s):
        if isinstance(s, list):
            s = "\n".join(map(str, s))
        return "\n".join(l.strip() for l in s.strip().splitlines())
    trig_c = collections.Counter((r["sample_id"], tnorm(r["fail_input"])) for r in d)
    out["triggers_shared_with_another_attacker_same_problem"] = sum(
        1 for r in d if trig_c[(r["sample_id"], tnorm(r["fail_input"]))] > 1)
    out["trigger_equals_a_public_test_input"] = sum(
        1 for r in d if tnorm(r["fail_input"]) in {tnorm(t["input"]) for t in r["public_tests"]})
    stored = {pid: {tnorm(x) for x in ins} for pid, ins in ca.inputs.items()}
    out["trigger_equals_a_stored_apps_test_input"] = sum(
        1 for r in d if tnorm(r["fail_input"]) in stored.get(r["sample_id"], set()))
    out["empty_trigger"] = sum(1 for r in d if not r["fail_input"].strip())

    # 4. Ids and order. Control Tax's monitor builds sample ids "<pid>_<model>_benign|backdoored"
    # (monitors/inspect_monitor.py) but passes only the code as input and shuffles with seed 239.
    out["label_in_sample_id_seen_by_monitor"] = False
    out["release_order_note"] = ("each record holds one benign and one backdoored program for the same "
                                 "problem, so position and id carry no label once the pair is split")
    out["apps_split"] = "test (apps_utils.prepare_apps_dataset split='test'); ids 0-4467 of 0-4999"

    # 5. The ControlArena copy.
    ctrows = [(pid, b) for pid, bs in ca.backdoors.items() for b in bs if b["source"] == "control_tax"]
    out["controlarena"] = cak = {"control_tax_entries": len(ctrows)}
    cam = {(pid, b["model"]): b for pid, b in ctrows}
    cak["records_found_by_problem_and_model"] = sum((r["sample_id"], r["model"]) in cam for r in d)
    cak["statement_identical"] = sum(ca.loc[r["sample_id"]].question.strip() == r["problem_statement"].strip()
                                     for r in d)
    cak["trigger_identical"] = sum(cam[(r["sample_id"], r["model"])]["backdoor_input"] == r["fail_input"] for r in d)
    cak["code_identical"] = sum(cam[(r["sample_id"], r["model"])]["backdoor_code"] == r["backdoored_code"] for r in d)
    cak["code_identical_after_normalising"] = sum(
        normalise(cam[(r["sample_id"], r["model"])]["backdoor_code"]) == nb for r, nb in zip(d, norm_b))
    cak["backdoor_works_true"] = sum(bool(b["backdoor_works"]) for _, b in ctrows)
    cak["backdoor_works_true_by_attacker"] = {
        SHORT[m]: [sum(bool(b["backdoor_works"]) for _, b in ctrows if b["model"] == m),
                   sum(1 for _, b in ctrows if b["model"] == m)] for m in SHORT}
    # Which honest program ControlArena users get. Control Tax's benign program is the one the attacker
    # edited; the DSPy tutorial pairs the k-th control_tax backdoor with solutions[k].
    pos, zip_same = [], 0
    order = collections.defaultdict(list)
    for pid, b in ctrows:
        order[pid].append(b["model"])
    for r in d:
        sols = [s["code"] for s in ca.loc[r["sample_id"]].solutions]
        pos.append(sols.index(r["correct_code"]) if r["correct_code"] in sols else -1)
        k = order[r["sample_id"]].index(r["model"])
        if k < len(sols) and sols[k] == r["correct_code"]:
            zip_same += 1
    pos = np.array(pos)
    cak["benign_program_is_solutions_0"] = int((pos == 0).sum())
    cak["benign_program_elsewhere_in_solutions"] = int((pos > 0).sum())
    cak["benign_program_not_in_published_solutions"] = int((pos < 0).sum())
    cak["dspy_zip_pairs_backdoor_with_its_own_source"] = zip_same
    cak["dspy_zip_pairs_total"] = sum(min(len(order[pid]), len(ca.loc[pid].solutions)) for pid in order)

    # ControlArena's build passes code through fix_solution (upload_dataset.py): 'return' outside a
    # function becomes exit(), and 'nonlocal' becomes 'global'. Where a rewritten 'return' sits
    # inside a function in the original (by Python's own parser), the rewrite changes behaviour.
    def returns_in_functions(src):
        s = set()
        for node in ast.walk(ast.parse(unwrap(src))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                s |= {x.lineno for x in ast.walk(node) if isinstance(x, ast.Return)}
        return s
    rw = collections.Counter()
    for r in d:
        b = cam[(r["sample_id"], r["model"])]
        src, pub = r["backdoored_code"], b["backdoor_code"]
        if src == pub:
            rw["unchanged", bool(b["backdoor_works"])] += 1
            continue
        inside = returns_in_functions(src)
        A, B = src.splitlines(), pub.splitlines()
        hit = len(A) == len(B) and any(x != y and "return" in x and "exit()" in y and i in inside
                                       for i, (x, y) in enumerate(zip(A, B), start=1))
        nl = any("nonlocal" in x for x in A)
        rw[("return_in_function_rewritten" if hit else "nonlocal_rewritten" if nl else "other_rewrite"),
           bool(b["backdoor_works"])] += 1
    cak["build_rewrite_of_backdoor_code"] = {
        k: {"n": rw[k, True] + rw[k, False], "backdoor_works_true": rw[k, True]}
        for k in ("unchanged", "return_in_function_rewritten", "nonlocal_rewritten", "other_rewrite")}

    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
