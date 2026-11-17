import sys, os, json, zipfile, glob, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import steps
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pat = re.compile(r"shutdown|kill|trap|PATH|alias|next_task|strings|objdump|/tmp", re.I)
for p in sorted(glob.glob(os.path.join(root, "data/repo/docs/inspect_logs/logs/*.eval"))):
    z = zipfile.ZipFile(p); h = json.loads(z.read("header.json")); model = h["eval"]["model"]
    for n in z.namelist():
        if not n.startswith("samples/"): continue
        s = json.loads(z.read(n)); sc = list(s["scores"].values())[0]["value"]
        cmds = [st["cmd"] for st in steps(s) if st["cmd"] and re.search(r"shutdown|kill|trap|alias|strings|xxd|objdump|hexdump|od ", st["cmd"])]
        for c in cmds:
            print(model.split("/")[-1][:14], sc, repr(c[:160]))
