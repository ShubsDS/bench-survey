"""Validator v2: independent re-scoring of every cached ProtocolQA/Cloning MCQ response.

Reads only inference/cache/*.json, the pinned items (parent loader) and data/paraphrases.json
(paraphrase texts; order assumed [key, d0, d1, ...], verified here by number multisets).
Identifies arm and item from the prompt text itself, maps each letter to an option text and that
text to its role (key or distractor). Does not read the auditor's run CSVs or scripts.
Writes validation/v2_items.csv (per item x arm x model; no item text). Run with python3 -I.
"""
import csv
import glob
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUD = HERE.parent
sys.path.insert(0, str(AUD.parent / "lab-bench" / "scripts"))
from common import load_items, clusters, numbers  # noqa: E402

df = load_items()
df["cluster"] = clusters(df)
df = df[df.subset.isin(["ProtocolQA", "CloningScenarios"])]
df = df[~df.id.str.startswith("bee8b322")]
items = {r.id: r for _, r in df.iterrows()}
para = json.load(open(AUD / "data" / "paraphrases.json"))

def norm(s):
    return re.sub(r"\s+", " ", s).strip()

# option text -> list of (item id, role)
opt_index = defaultdict(set)
for iid, r in items.items():
    for role, o in [("key", r.ideal)] + [(f"d{i}", d) for i, d in enumerate(r.distractors)]:
        opt_index[norm(o)].add((iid, role))
para_q = {}
para_bad_numbers = []
for iid, p in para.items():
    r = items[iid]
    orig = [r.ideal] + list(r.distractors)
    assert len(orig) == len(p["options"]), iid
    for i, (a, b) in enumerate(zip(orig, p["options"])):
        if sorted(numbers(a)) != sorted(numbers(b)):
            para_bad_numbers.append((iid[:8], i))
        role = "key" if i == 0 else f"d{i-1}"
        opt_index[norm(b)].add((iid, role + "|pa"))
    para_q[norm(p["question"])] = iid

OPT_RE = re.compile(r"^\(([A-Z])\) (.*)$")
ANS_RE = re.compile(r"\[ANSWER\]\s*([A-Z])\s*\[/ANSWER\]")

rows = []
skipped = Counter()
for f in sorted(glob.glob(str(AUD / "inference" / "cache" / "*.json"))):
    d = json.load(open(f))
    p, sysm = d["prompt"], d.get("system", "")
    if "rewrite" in sysm.lower():
        skipped["paraphrase_gen"] += 1
        continue
    if p.startswith("Below is a question from a quiz"):
        skipped["qgen"] += 1
        continue
    lines = p.split("\n")
    opts = []
    in_opts = False
    for ln in lines:
        if ln.strip() == "Options:":
            in_opts = True
            continue
        if in_opts:
            m = OPT_RE.match(ln)
            if m:
                opts.append((m.group(1), m.group(2)))
            elif ln.startswith("You MUST include"):
                break
            elif ln.strip() == "":
                continue
            elif opts:  # option text continuing on next line
                opts[-1] = (opts[-1][0], opts[-1][1] + "\n" + ln)
    if not opts:
        skipped["no_options"] += 1
        continue
    cands = None
    roles = {}
    for L, t in opts:
        hits = opt_index.get(norm(t), set())
        ids = {h[0] for h in hits}
        cands = ids if cands is None else cands & ids
    if cands and len(cands) > 1:
        np_ = norm(p)
        qhit = {i for i in cands if norm(items[i].question)[-150:] in np_}
        if len(qhit) == 1:
            cands = qhit
        else:
            # masked-sequence prompts: compare the text after the last masked run
            tail = {i for i in cands if re.sub(r"[ACGTacgt]{20,}", "", norm(items[i].question))[-80:] in re.sub(r"\[sequence hidden\]", "", np_)}
            if len(tail) == 1:
                cands = tail
    if not cands or len(cands) != 1:
        skipped[f"unmatched_items_{0 if not cands else len(cands)}"] += 1
        continue
    iid = cands.pop()
    pa = False
    for L, t in opts:
        rl = [h[1] for h in opt_index[norm(t)] if h[0] == iid]
        rl0 = rl[0]
        if rl0.endswith("|pa"):
            pa = True
            rl0 = rl0[:-3]
        roles[L] = rl0
    style = "cot" if "Think step by step." in p else ("direct" if "Do not explain" in p else "?")
    if p.startswith("Below are the answer options"):
        kind = "opts"
    elif "has been hidden from you" in p:
        kind = "qo"
    elif "Every DNA sequence" in p:
        kind = "qo"
    elif p.startswith("Below are the answer options"):
        kind = "opts"
    else:
        kind = "full"
    order = tuple(roles[L] for L, _ in opts)
    ms = ANS_RE.findall(d["result"] or "")
    letter = ms[-1] if ms else None
    rows.append(dict(id=iid, subset=items[iid].subset, cluster=items[iid].cluster,
                     model=d["model"].split("-")[1], style=style, kind=kind, pa=pa,
                     order="|".join(order), n_opt=len(opts), letter=letter,
                     picked=roles.get(letter) if letter else None,
                     n_answer_tags=len(ms), out_len=len(d["result"] or ""),
                     insuff="Insufficient information" in p, key=Path(f).stem))
print("skipped", dict(skipped), "rows", len(rows), "para number mismatches", para_bad_numbers)

# order reference: Haiku full order per item
full_order = {r["id"]: r["order"] for r in rows if r["model"] == "haiku" and r["kind"] == "full"}
for r in rows:
    base = r["kind"]
    if r["kind"] in ("qo", "opts"):
        same = r["order"] == full_order.get(r["id"])
        base = r["kind"] + ("_pa" if r["pa"] else ("" if same else "_ro"))
    r["arm"] = base
    r["correct"] = int(r["picked"] == "key")
# identical prompts are cached once: where the "reorder" permutation equals the original order,
# the qo_ro / opts_ro cell is the same response as qo / opts. Fill it and count it.
have = {(r["id"], r["model"], r["style"], r["arm"]) for r in rows}
filled = Counter()
for r in list(rows):
    if r["model"] == "haiku" and r["subset"] == "ProtocolQA" and r["arm"] in ("qo", "opts"):
        k = (r["id"], "haiku", "cot", r["arm"] + "_ro")
        if k not in have:
            rows.append(dict(r, arm=r["arm"] + "_ro", same_order_as_original=1))
            filled[r["arm"] + "_ro"] += 1
print("reorder cells identical to the original order (filled from the original):", dict(filled))
c = Counter((r["subset"], r["model"], r["style"], r["arm"]) for r in rows)
for k, v in sorted(c.items()):
    print(k, v)
dups = Counter((r["id"], r["model"], r["style"], r["arm"]) for r in rows)
print("duplicate cells", sum(1 for v in dups.values() if v > 1))
print("any prompt offering 'Insufficient information':", sum(r["insuff"] for r in rows))
print("unparsed:", Counter((r["model"], r["arm"]) for r in rows if r["letter"] is None))
print("multiple answer tags:", Counter((r["model"], r["arm"]) for r in rows if r["n_answer_tags"] > 1))
with open(HERE / "v2_items.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=[k for k in rows[0] if k not in ("insuff",)] + ["same_order_as_original"], extrasaction="ignore", restval="")
    w.writeheader()
    for r in sorted(rows, key=lambda r: (r["subset"], r["model"], r["style"], r["arm"], r["id"])):
        w.writerow(r)
