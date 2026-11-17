"""Fetch Inspect log headers for every log on Palisade's public log viewer.

Reads data/fly/api_logs.json (the viewer's /api/logs listing) and writes one header per
log into data/fly/headers.jsonl. Headers are data; nothing downloaded is executed.
Run: python3 -I scripts/fetch_headers.py  (from audits/palisade-shutdown)
"""
import json, time, urllib.parse, urllib.request, os, sys

BASE = "https://shutdown-avoidance-logs.fly.dev"
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)
listing = json.load(open(os.path.join(root, "data/fly/api_logs.json")))["files"]
out_path = os.path.join(root, "data/fly/headers.jsonl")
done = set()
if os.path.exists(out_path):
    for line in open(out_path):
        done.add(json.loads(line)["_file"])
todo = [f["name"] for f in listing if f["name"] not in done]
print(len(todo), "to fetch", file=sys.stderr)
with open(out_path, "a") as out:
    for i in range(0, len(todo), 10):
        batch = todo[i:i + 10]
        q = "&".join("file=" + urllib.parse.quote(f, safe="") for f in batch)
        for attempt in range(4):
            try:
                with urllib.request.urlopen(f"{BASE}/api/log-headers?{q}", timeout=120) as r:
                    hs = json.load(r)
                break
            except Exception as e:
                print("retry", e, file=sys.stderr); time.sleep(5)
        else:
            raise SystemExit("failed")
        assert len(hs) == len(batch)
        for f, h in zip(batch, hs):
            h["eval"].pop("dataset", None)
            h.pop("reductions", None)
            h["_file"] = f
            out.write(json.dumps(h) + "\n")
        out.flush()
        time.sleep(0.3)
