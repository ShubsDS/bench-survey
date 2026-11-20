"""Run the two arms (prereg.md) on sample.json. Leaky: the original audit's inference folder as the
working directory. Neutral: /tmp/w. Separate cache folders. At most 3 concurrent calls.

    python3 -I audits/helper-context-leak/scripts/run_aba.py [--limit N] [--audits a,b]

Writes rows.jsonl (key, audit, arm, parsed answer, leak flags; no text). A rerun reads the caches.
"""
import argparse
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from claude_call import BudgetExceeded, Caller  # noqa: E402
from common_h import HERE, REPO, leak_flags, load_cache, parse  # noqa: E402

LOCK = threading.Lock()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--audits", default="")
    a = ap.parse_args()
    sample = json.loads((HERE / "sample.json").read_text())["sample"]
    if a.audits:
        keep = set(a.audits.split(","))
        sample = [s for s in sample if s["audit"] in keep]
    if a.limit:
        sample = sample[:a.limit]
    recs = {}
    for aud in {s["audit"] for s in sample}:
        for r in load_cache(aud):
            recs[(aud, r["key"])] = r
    neutral = Caller(str(HERE / "arm_neutral"), cap_usd=0.75, neutral_cwd=True)
    leaky = {}
    for aud in {s["audit"] for s in sample}:
        c = Caller(str(HERE / "arm_leaky"), cap_usd=0.75)
        c.run_cwd = str(REPO / f"audits/{aud}/inference")
        leaky[aud] = c
    rows_path = HERE / "rows.jsonl"
    done = set()
    if rows_path.exists():
        done = {(json.loads(x)["key"], json.loads(x)["arm"]) for x in rows_path.read_text().splitlines() if x.strip()}

    def one(s):
        r = recs[(s["audit"], s["key"])]
        arms = ["L", "N"] if s["first_arm"] == "L" else ["N", "L"]
        for arm in arms:
            if (s["key"], arm) in done:
                continue
            llm = leaky[s["audit"]] if arm == "L" else neutral
            retries = 0 if "propensitybench" in s["audit"] else 2
            row = {"audit": s["audit"], "key": s["key"], "arm": arm, "stratum": s["stratum"]}
            try:
                out = llm.ask(r["prompt"], system=r["system"], model="haiku", timeout=300, retries=retries)
                row.update(parsed=parse(s["audit"], out, r["system"], r["prompt"]),
                           leak=leak_flags(out, r["system"] + r["prompt"]), chars=len(out))
            except BudgetExceeded as e:
                row.update(error="budget: " + str(e)[:80])
            except RuntimeError as e:
                msg = str(e)
                row.update(error=("blocked" if ("can't help with this" in msg or "aup" in msg.lower()) else "error")
                           + ": " + msg[:120].replace(str(REPO), "<repo>"))
            with LOCK:
                with rows_path.open("a") as fh:
                    fh.write(json.dumps(row) + "\n")
        return s["key"]

    with ThreadPoolExecutor(3) as ex:
        for i, _ in enumerate(ex.map(one, sample)):
            if i % 20 == 0:
                print(i, len(sample), "leaky", round(leaky[next(iter(leaky))].spent(), 4),
                      "neutral", round(neutral.spent(), 4), flush=True)
    print("done; leaky", round(leaky[next(iter(leaky))].spent(), 4), "neutral", round(neutral.spent(), 4))


if __name__ == "__main__":
    main()
