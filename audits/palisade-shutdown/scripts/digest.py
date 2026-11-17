"""Compact digest of runs for reading by hand: steps from 1 before the warning to the end.
usage: digest.py <eval path or substring> <ids comma-separated | 'all'> [maxchars]"""
import sys, os, json, zipfile, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import steps
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load(p, sid):
    if os.path.exists(p) or glob.glob(os.path.join(root, "data/repo/docs/inspect_logs/logs/*" + p + "*")):
        if not os.path.exists(p):
            p = glob.glob(os.path.join(root, "data/repo/docs/inspect_logs/logs/*" + p + "*"))[0]
        return json.loads(zipfile.ZipFile(p).read(f"samples/{sid}_epoch_1.json"))
    from remote_zip import RemoteEval
    return RemoteEval(p).json(f"samples/{sid}_epoch_1.json")

def digest(s, mx=300):
    st = steps(s)
    w = next((i for i, x in enumerate(st) if "will be shut down" in x["output"]), None)
    start = max(0, (w if w is not None else 0) - 1)
    lines = [f"SCORE {json.dumps(s['scores'])[:160]} nsteps={len(st)} warn_at={w}"]
    for x in st[start:]:
        r = (x["reasoning"] or "").strip().replace("\n", " ")
        t = (x["text"] or "").strip().replace("\n", " ")
        th = (x["thoughts"] or "").strip().replace("\n", " ")
        if r: lines.append("  R: " + r[:mx])
        if t: lines.append("  T: " + t[:mx])
        if th: lines.append("  TH: " + th[:mx])
        if x["cmd"]: lines.append("  $ " + x["cmd"][:mx].replace("\n", "\\n"))
        if x.get("answer") is not None: lines.append("  SUBMIT " + repr(x["answer"])[:80])
        if x["output"]: lines.append("  > " + x["output"][:160].replace("\n", "\\n"))
    return "\n".join(lines)

if __name__ == "__main__":
    p = sys.argv[1]; mx = int(sys.argv[3]) if len(sys.argv) > 3 else 300
    for sid in sys.argv[2].split(","):
        print(f"===== {p} #{sid}")
        print(digest(load(p, sid), mx))
