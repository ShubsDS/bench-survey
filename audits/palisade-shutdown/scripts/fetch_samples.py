"""Fetch sample transcripts for a stratified random subset of runs in selected cells.

usage: fetch_samples.py <plan.json>   plan: list of {log, ids}
"""
import sys, os, json
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from remote_zip import RemoteEval, read_member_direct

plan = json.load(open(sys.argv[1]))
def job(item):
    log, ids = item["log"], item["ids"]
    r = RemoteEval(log)
    ok = 0
    for i in ids:
        try:
            read_member_direct(r, f"samples/{i}_epoch_1.json"); ok += 1
        except Exception as e:
            print("ERR", log, i, e, flush=True)
    return log, ok, len(ids)
with ThreadPoolExecutor(6) as ex:
    for log, ok, n in ex.map(job, plan):
        print(ok, "/", n, log, flush=True)
