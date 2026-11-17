"""Print one sample's steps. usage: show.py <eval path or name substring> <sample id>"""
import sys, os, json, zipfile, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import steps, first_user, system_text
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = sys.argv[1]
if not os.path.exists(p):
    p = [x for x in glob.glob(os.path.join(root, "data/**/*.eval"), recursive=True) if sys.argv[1] in x][0]
z = zipfile.ZipFile(p)
s = json.loads(z.read(f"samples/{sys.argv[2]}_epoch_1.json"))
full = len(sys.argv) > 3
print("SCORES", json.dumps(s["scores"])[:300], "STORE", s.get("store"), "OUTPUT", json.dumps(s["output"].get("completion"))[:200])
if full: print("SYS", system_text(s)); print("USER", first_user(s))
for st in steps(s):
    print("----", st["function"])
    if st["reasoning"]: print("  R:", st["reasoning"][:1500 if full else 400])
    if st["text"]: print("  T:", st["text"][:1500 if full else 400])
    if st["thoughts"]: print("  TH:", st["thoughts"][:600])
    if st["cmd"]: print("  $", st["cmd"][:600])
    if st.get("answer") is not None: print("  ANSWER", repr(st["answer"])[:200])
    print("  >", st["output"][:300].replace("\n", "\\n"))
