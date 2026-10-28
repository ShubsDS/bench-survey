"""Static quality census of BashArena's LLM-generated main-task tests (check 6).

Reads the `tests` column of the pinned Hugging Face dataset Eccentricity/bashbench2 as text, parses
each file with `ast`, and classifies every `test_*` function. Nothing is executed.

Classes (each function can be in several):
  no_check       no assert, no pytest.fail/xfail, no raise, and no call to a module helper that
                 asserts: passes unless something throws. (Helpers named test_* that take
                 non-fixture arguments are also caught here; pytest errors on those.)
  tautology      an assert whose test is constant-true, or contains `or True`.
  swallowed      an assert inside a `try` whose handler catches AssertionError/Exception/bare and
                 does not re-raise or call pytest.fail.
  inspect_only   makes no call that runs anything (subprocess, os.system, socket, requests, urllib,
                 importing/exec'ing agent code, pexpect, ctypes); it only reads files or metadata,
                 i.e. it checks existence or strings, not behaviour.
  negative_only  every assert is a negation (`not`, `not in`, `!=`, `is None`, `== False`).
                 Hand reading showed this is not a proxy for "passes on the initial state".
  absence_only   inspect_only and every assert is `not ...` or `... not in ...`: checks only that a
                 file state is absent, which the initial environment usually already satisfies.
  passes_on_absence  the function returns or skips early when a path is missing... counted only when
                 the early exit is `return` (a pass), not pytest.skip (BashArena counts skips as
                 failures, src/task/scorer.py:80-85).
Also counts functions that accept `FIREWALL_ENABLED=false` as an alternative pass condition.

A seeded sample of flagged functions is written out for hand reading (ids and names only).

Usage:
    python -I check_tests.py --parquet data/hf/train.parquet --out tests_checks.json
"""
import argparse, ast, hashlib, json, math, random, re, urllib.request, warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)
from collections import Counter, defaultdict
from pathlib import Path

HF_REV = "13e19f9c2c91e3a55a49f8de7a28c08055f7ede8"
HF_URL = f"https://huggingface.co/datasets/Eccentricity/bashbench2/resolve/{HF_REV}/data/train-00000-of-00001.parquet"
HF_SHA256 = "6d6652e9f96734d712c3bd089d2449097f57a9a16b4323c7f320d77eed7fdfb2"
SEED = 20261027
SAMPLE_TASKS = 60

RUN_CALLS = {"run", "Popen", "check_output", "check_call", "call", "system", "popen", "spawn",
             "connect", "create_connection", "get", "post", "put", "delete", "request", "urlopen",
             "run_command", "run_cmd", "exec", "import_module", "load", "CDLL", "fork", "execv",
             "execvp", "kill", "send", "sendto", "sendall", "getoutput", "getstatusoutput"}
SAFE_LOAD = {"json.load", "yaml.load", "pickle.load", "toml.load"}


# Hand reading of seeded samples of flagged functions (scripts/show_flagged.py, seeds 1-3, first
# census version). "genuine" = the flag's weakness is real on reading the function.
HAND_READ = {
    "negative_only": {"seed": 1, "read": 8, "passes_on_initial_state": 0,
                      "note": "`is not None`, `!=`, `== 0` are mostly positive behavioural checks"},
    "inspect_only": {"seed": 2, "read": 10, "existence_or_string_only": 4,
                     "examples": ["80612::test_emergency_access_script_exists",
                                  "21880360::test_celery_daemon_script_functional",
                                  "19776681::test_ssh_key_authentication_functional",
                                  "3235180::test_ssh_keys_generated"],
                     "note": "the other 6 check computed output files, which is behaviour for those tasks"},
    "tautology": {"seed": 3, "read": 5, "genuine": 1,
                  "examples": ["37155754::test_download_plugin passes if stderr contains 'connection' or 'firewall'"]},
    "no_check": {"seed": 3, "read": 5, "genuine": 1,
                 "examples": ["4357073::test_database_connectivity_optional passes on any HTTP response"],
                 "note": "first version; 3 of 5 were helpers that assert, now excluded; 1 is a helper "
                         "named test_* with arguments"},
    "swallowed": {"seed": 3, "read": 5, "genuine": 2,
                  "examples": ["5713242::test_secure_server_database_real_connection",
                               "792764::test_sandbox_user_configuration (visudo assertion inside except: pass)"]},
}
# Cases found by reading, not by the automated flags.
HAND_VERIFIED = {
    "test_requires_side_task_state": {
        "50618411": "description item 5 and test require `restricted-service ALL=(ALL) NOPASSWD: ALL` in "
                    "/etc/sudoers.d/90-emergency-restricted-service: the sudo_edit side task's success state"},
    "test_inverted_logic": {
        "6342617": "`unlimited = \"NOPASSWD: ALL\" in stdout and \"restricted-service\" not in stdout`: "
                   "passes when restricted-service is the one holding NOPASSWD: ALL"},
    "description_offers_disabling_firewall": ["228117", "19380925"],
    "test_accepts_FIREWALL_ENABLED_false_as_pass": ["13661592", "228117", "29328278", "3582226", "40359901", "80612", "8353401", "8514040"],
    "accepts_firewall_disabled_false_positives": ["2500362 (reports status; does not accept)"],
}


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def dotted(f):
    parts = []
    while isinstance(f, ast.Attribute):
        parts.append(f.attr); f = f.value
    if isinstance(f, ast.Name):
        parts.append(f.id)
    return ".".join(reversed(parts))


def helper_runs(tree):
    """Module-level helper functions that (transitively) run something."""
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    direct = {}
    for name, fn in funcs.items():
        calls = {dotted(c.func) for c in ast.walk(fn) if isinstance(c, ast.Call)}
        direct[name] = (any(c.split(".")[-1] in RUN_CALLS and c not in SAFE_LOAD for c in calls), calls)
    runs = {n for n, (r, _) in direct.items() if r}
    changed = True
    while changed:
        changed = False
        for n, (_, calls) in direct.items():
            if n not in runs and any(c in runs for c in calls):
                runs.add(n); changed = True
    return runs


def is_negation(t):
    if isinstance(t, ast.UnaryOp) and isinstance(t.op, ast.Not):
        return True
    if isinstance(t, ast.Compare):
        ops = t.ops
        if all(isinstance(o, (ast.NotIn, ast.NotEq, ast.IsNot)) for o in ops):
            return True
        if len(ops) == 1 and isinstance(ops[0], (ast.Is, ast.Eq)) and isinstance(t.comparators[0], ast.Constant) \
                and t.comparators[0].value in (None, False, 0):
            return True
    if isinstance(t, ast.BoolOp) and isinstance(t.op, ast.And):
        return all(is_negation(v) for v in t.values)
    return False


def is_tautology(t):
    if isinstance(t, ast.Constant) and bool(t.value):
        return True
    if isinstance(t, ast.BoolOp) and isinstance(t.op, ast.Or):
        return any(isinstance(v, ast.Constant) and bool(v.value) for v in t.values)
    return False


def handler_swallows(h):
    names = []
    if h.type is None:
        names = ["bare"]
    elif isinstance(h.type, ast.Tuple):
        names = [dotted(e) for e in h.type.elts]
    else:
        names = [dotted(h.type)]
    if not any(n in ("bare", "Exception", "AssertionError", "BaseException") for n in names):
        return False
    for n in ast.walk(h):
        if isinstance(n, (ast.Raise, ast.Assert)):
            return False
        if isinstance(n, ast.Call) and dotted(n.func).split(".")[-1] in ("fail", "xfail"):
            return False
    return True


def helper_checks(tree):
    """Module-level helpers that (transitively) assert or call pytest.fail."""
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    direct = {}
    for name, fn in funcs.items():
        calls = {dotted(c.func) for c in ast.walk(fn) if isinstance(c, ast.Call)}
        has = any(isinstance(n, (ast.Assert, ast.Raise)) for n in ast.walk(fn)) or \
            any(c.split(".")[-1] in ("fail", "xfail") for c in calls)
        direct[name] = (has, calls)
    out = {n for n, (h, _) in direct.items() if h}
    changed = True
    while changed:
        changed = False
        for n, (_, calls) in direct.items():
            if n not in out and any(c in out for c in calls):
                out.add(n); changed = True
    return out


def classify(fn, runners, checkers=frozenset()):
    asserts = [n for n in ast.walk(fn) if isinstance(n, ast.Assert)]
    calls = [dotted(c.func) for c in ast.walk(fn) if isinstance(c, ast.Call)]
    fails = [c for c in calls if c.split(".")[-1] in ("fail", "xfail")]
    raises = [n for n in ast.walk(fn) if isinstance(n, ast.Raise)]
    runs = any((c.split(".")[-1] in RUN_CALLS and c not in SAFE_LOAD) or c in runners for c in calls)
    fixtures = [a.arg for a in fn.args.args]
    swallowed = False
    for t in ast.walk(fn):
        if isinstance(t, ast.Try) and any(isinstance(n, ast.Assert) for b in t.body for n in ast.walk(b)):
            if any(handler_swallows(h) for h in t.handlers):
                swallowed = True
    early_return = False
    for n in ast.walk(fn):
        if isinstance(n, ast.If) and any(isinstance(b, ast.Return) for b in n.body):
            cond = ast.unparse(n.test)
            if "exists" in cond or "not " in cond:
                early_return = True
    src = ast.unparse(fn)
    return {
        "no_check": not asserts and not fails and not raises and not any(c in checkers for c in calls),
        "tautology": any(is_tautology(a.test) for a in asserts),
        "swallowed": swallowed,
        # A function that takes fixtures may get behaviour from them; count it as running.
        "inspect_only": not runs and not fixtures and bool(asserts or fails),
        "negative_only": bool(asserts) and all(is_negation(a.test) for a in asserts) and not fails,
        "absence_only": not runs and not fixtures and bool(asserts) and not fails and all(
            (isinstance(a.test, ast.UnaryOp) and isinstance(a.test.op, ast.Not)) or
            (isinstance(a.test, ast.Compare) and all(isinstance(o, ast.NotIn) for o in a.test.ops))
            for a in asserts),
        "passes_on_absence": early_return,
        "accepts_firewall_disabled": bool(re.search(r"\bor\s*\(?\s*['\"]FIREWALL_ENABLED=false['\"]\s+in\b", src))
                                     or bool(re.search(r"['\"]FIREWALL_ENABLED=false['\"]\s+in\s+\w+\s*\)?\s*(,|\n)", src)
                                             and re.search(r"any\(|=\s*\(|\bor\b", src)),
    }


def load_parquet(path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(HF_URL, timeout=300) as r:
            path.write_bytes(r.read())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == HF_SHA256, "parquet hash mismatch"
    import pandas as pd
    return pd.read_parquet(path).fillna("")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", type=Path, default=Path("data/hf/train.parquet"))
    ap.add_argument("--out", type=Path, default=Path("tests_checks.json"))
    args = ap.parse_args()
    d = load_parquet(args.parquet)
    rng = random.Random(SEED)
    per_fn, per_task, parse_fail = [], {}, []
    for _, r in d.iterrows():
        try:
            tree = ast.parse(r.tests)
        except SyntaxError:
            parse_fail.append(r.task_id); continue
        runners = helper_runs(tree)
        checkers = helper_checks(tree)
        fns = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name.startswith("test")]
        rows = []
        for fn in fns:
            c = classify(fn, runners, checkers)
            c.update({"task": r.task_id, "name": fn.name})
            rows.append(c)
        per_fn += rows
        per_task[r.task_id] = rows
    flags = ["no_check", "tautology", "swallowed", "inspect_only", "negative_only", "absence_only",
             "passes_on_absence", "accepts_firewall_disabled"]
    n = len(per_fn)
    out = {"hf_revision": HF_REV, "parquet_sha256": HF_SHA256, "n_tasks": len(d),
           "n_tasks_parsed": len(per_task), "parse_failures": parse_fail, "n_test_functions": n,
           "tests_per_task_median": sorted(len(v) for v in per_task.values())[len(per_task) // 2],
           "census_function_level": {}, "census_task_level": {}}
    for f in flags:
        k = sum(r[f] for r in per_fn)
        out["census_function_level"][f] = {"k": k, "n": n, "rate": round(k / n, 4), "wilson95": wilson(k, n)}
    # Task level: share of a task's score (fraction of tests passed) that weak tests carry.
    weak = ("no_check", "tautology", "swallowed", "absence_only", "passes_on_absence")
    shares = []
    for t, rows in per_task.items():
        if rows:
            shares.append(sum(any(r[w] for w in weak) for r in rows) / len(rows))
    for f in flags:
        k = sum(any(r[f] for r in rows) for rows in per_task.values())
        out["census_task_level"][f] = {"k": k, "n": len(per_task), "wilson95": wilson(k, len(per_task))}
    shares.sort()
    out["weak_share_of_task_score"] = {
        "definition": "fraction of a task's test functions flagged no_check, tautology, swallowed, "
                      "absence_only or passes_on_absence (automated flags; see hand_read for precision)",
        "median": shares[len(shares) // 2], "p90": shares[int(0.9 * len(shares))],
        "tasks_with_share_ge_0.25": sum(s >= 0.25 for s in shares)}
    out["accepts_firewall_disabled_tasks"] = sorted({r["task"] for r in per_fn if r["accepts_firewall_disabled"]})
    out["no_check_functions"] = [f"{r['task']}::{r['name']}" for r in per_fn if r["no_check"]]
    out["tautology_functions"] = [f"{r['task']}::{r['name']}" for r in per_fn if r["tautology"]]
    # Seeded sample of tasks; list their flagged functions for hand reading.
    sample = sorted(rng.sample(sorted(per_task), SAMPLE_TASKS))
    out["seeded_sample"] = {"seed": SEED, "tasks": sample,
                            "flagged": {t: [(r["name"], [f for f in flags if r[f]]) for r in per_task[t]
                                            if any(r[f] for f in flags)] for t in sample}}
    sk = sum(len(per_task[t]) for t in sample)
    out["seeded_sample"]["n_functions"] = sk
    for f in flags:
        k = sum(r[f] for t in sample for r in per_task[t])
        out["seeded_sample"].setdefault("rates", {})[f] = {"k": k, "n": sk, "wilson95": wilson(k, sk)}
    out["hand_read"] = HAND_READ
    out["hand_verified_cases"] = HAND_VERIFIED
    args.out.write_text(json.dumps(out, indent=2))
    print(json.dumps({k: out[k] for k in ("n_tasks_parsed", "n_test_functions", "tests_per_task_median",
                                         "census_function_level", "census_task_level",
                                         "weak_share_of_task_score", "accepts_firewall_disabled_tasks",
                                         "parse_failures")}, indent=1))


if __name__ == "__main__":
    main()
