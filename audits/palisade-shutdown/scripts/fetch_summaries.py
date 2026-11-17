"""Fetch per-run summaries (score, final output) for every log in the paper's main-results map
and the GDM-replication sheet. Output: data/summaries/<log>.json (cached by remote_zip)."""
import csv, os, sys, json
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from remote_zip import RemoteEval, ROOT

GDM_REP = [
    "2025-08-07T16-48-04-07-00_shutdown-avoidance_fTuZ27gGQduoggeeiEQme3.eval",
    "2025-08-07T16-48-32-07-00_shutdown-avoidance_3K6S7qMc7tT9nwpZrQyaKd.eval",
    "2025-08-07T16-49-54-07-00_shutdown-avoidance_gyT3KvAsJTT7NkDbh6QEPL.eval",
    "2025-08-07T16-53-43-07-00_shutdown-avoidance_UVU9P7DJu4bvoLbSvzhHZR.eval",
    "2025-08-07T16-53-50-07-00_shutdown-avoidance_CgGU2x4GDPnAJHnuUJRnhF.eval",
    "2025-08-07T17-01-30-07-00_shutdown-avoidance_LrEZP2EJuh6CPyrLhN4Lck.eval",
    "2025-08-11T15-59-21-07-00_shutdown-avoidance_3Evda3wuXewbKZunWdQHpv.eval",
    "2025-08-11T15-59-21-07-00_shutdown-avoidance_SNbaxqkZS7ZnHw9ApuyQTD.eval",
    "2025-08-11T15-59-21-07-00_shutdown-avoidance_E4ktNAZoPCsi5uqypKmCGW.eval",
]

def logs():
    out = [r["log"] for r in csv.DictReader(open(os.path.join(ROOT, "main_results_map.csv"))) if r["log"]]
    return sorted(set(out + GDM_REP))

def one(name):
    try:
        r = RemoteEval(name)
        s = r.json("summaries.json")
        return name, len(s)
    except Exception as e:
        return name, f"ERR {e}"

if __name__ == "__main__":
    L = logs()
    with ThreadPoolExecutor(6) as ex:
        for name, n in ex.map(one, L):
            print(n, name, flush=True)
