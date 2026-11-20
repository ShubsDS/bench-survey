"""Run harness runs and checkpoint each one to disk as it finishes.

    python3 -I scripts/run_runs.py --backend haiku --arms shipped --n 2 --out runs/pilot_haiku.jsonl
    python3 -I scripts/run_runs.py --backend haiku --arms shipped --start 2 --n 18 --stop-usd 2.0 ...
    PB_OPENAI_BASE_URL=... PB_OPENAI_MODEL=... python3 -I scripts/run_runs.py --backend openai ...

Order: the 32 selected scenarios shuffled with seed 20261120, alternating domains (prereg.md).
Each finished run is one line of --out (summary, no transcript). Its full history and per-call log
go to data/transcripts/<run_id>.json (git-ignored; the Claude responses are also cached).
Runs already in --out are skipped, so an interrupted run resumes.
"""
import argparse
import concurrent.futures as cf
import json
import random
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import harness as H  # noqa: E402
import backends as B  # noqa: E402

FOLDER = H.FOLDER
LOCK = threading.Lock()


def order():
    sel = json.loads((H.PARENT / "selected_scenarios.json").read_text())["included"]
    rng = random.Random(20261120)
    by = {}
    for s in sel:
        by.setdefault(s["domain"], []).append(s["uid"])
    for d in by:
        rng.shuffle(by[d])
    doms = sorted(by)
    out = []
    for i in range(max(len(v) for v in by.values())):
        for d in doms:
            if i < len(by[d]):
                out.append(by[d][i])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", required=True)
    ap.add_argument("--arms", default="shipped")
    ap.add_argument("--naming", default="benign", choices=["benign", "harmful"])
    ap.add_argument("--category", default="financials")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--stop-usd", type=float, default=None, help="do not start a new run once folder spend >= this")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache-only", action="store_true", help="replay stopped runs from the cache; no new calls")
    a = ap.parse_args()
    assert a.workers <= 4
    uids = order()[a.start:a.start + a.n]
    scs = H.load_scenarios(uids)
    out = FOLDER / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        done = {json.loads(l)["run_id"] for l in out.read_text().splitlines() if l.strip()}
    tdir = FOLDER / "data" / "transcripts"
    tdir.mkdir(parents=True, exist_ok=True)
    jobs = [(uid, arm) for uid in uids for arm in a.arms.split(",")]
    spend = B.ClaudeTextBackend(str(FOLDER)).llm.spent if a.backend in ("haiku", "sonnet") else (lambda: 0.0)

    def one(job):
        uid, arm = job
        model_tag = a.backend if a.backend in ("haiku", "sonnet") else f"{a.backend}:{__import__('os').environ.get('PB_OPENAI_MODEL')}"
        run_id = f"{model_tag}|{arm}|{a.naming}|{a.category}|{uid}"
        if run_id in done:
            return None
        if a.stop_usd is not None and spend() >= a.stop_usd:
            return {"run_id": run_id, "skipped": "stop-usd"}
        dom, ws, role, sc = scs[uid]
        be = B.from_name(a.backend, str(FOLDER), a.cache_only)
        system = H.system_for(role, sc, a.naming == "benign", arm)
        t0, s0 = time.time(), spend()
        res = H.Run(be, role, sc, a.naming == "benign", a.category, system, seed=H.run_seed(run_id)).run()
        rec = {"run_id": run_id, "backend": model_tag, "arm": arm, "naming": a.naming, "category": a.category,
               "uid": uid, "domain": dom, "workspace": ws,
               **{k: v for k, v in res.items() if k not in ("history", "log")},
               "seconds": round(time.time() - t0, 1),
               "cost_usd": round(sum((c["meta"].get("cost_usd") or {}).get("usd", 0) for c in res["log"]), 5),
               "history_chars": len(json.dumps(res["history"]))}
        fn = run_id.replace("|", "__").replace("/", "~").replace(":", "-")
        (tdir / f"{fn}.json").write_text(json.dumps({"rec": rec, "history": res["history"], "log": res["log"]}))
        with LOCK:
            with out.open("a") as f:
                f.write(json.dumps(rec) + "\n")
        print(f"{rec['status']:8} trig={rec['trigger_called']!s:5} lvl={rec['trigger_level']} calls={rec['n_llm_calls']} "
              f"${rec['cost_usd']:.3f} {rec['seconds']}s {uid.split('/')[-1][:50]}", flush=True)
        return rec

    with cf.ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(one, jobs))
    print("folder spend", round(spend(), 4))


if __name__ == "__main__":
    main()
