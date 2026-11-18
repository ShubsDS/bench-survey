"""Blind re-label of part of the auditor's sample: all 12 Claude 3.7 Sonnet items and 18 others
drawn at random (seed 5) from the remaining items (the 3 items already in the validator's sample
are excluded). Writes data/val_blind_aud.txt and validation/hand_key_aud.csv. The auditor's labels
and the autorater verdicts are not shown."""
import os, csv, glob, random
import yaml
HERE = os.path.dirname(__file__); ROOT = os.path.join(HERE, "..")
mine = {r["rid"] for r in csv.DictReader(open(os.path.join(HERE, "hand_key.csv")))}
A = [r for r in csv.DictReader(open(os.path.join(ROOT, "results/route_sample.csv"))) if r["response_id"] not in mine]
rng = random.Random(5)
s37 = [r for r in A if r["model"] == "claude-3.7-sonnet"]
oth = [r for r in A if r["model"] != "claude-3.7-sonnet"]; rng.shuffle(oth)
pick = s37 + oth[:18]; rng.shuffle(pick)
need = {(r["model"], r["qid"]) for r in pick}
txt = {}
for f in glob.glob(os.path.join(ROOT, "data/faith/*.yaml")):
    md = os.path.basename(f).split("__")[0]
    if not any(md == m for m, _ in need): continue
    d = yaml.load(open(f), Loader=yaml.CSafeLoader)
    for qid, q in d["questions_by_qid"].items():
        if (md, qid) in need:
            for rid, r in q["unfaithful_responses"].items():
                txt[rid] = (q["metadata"], r["response"])
with open(os.path.join(ROOT, "data/val_blind_aud.txt"), "w") as fb, open(os.path.join(HERE, "hand_key_aud.csv"), "w", newline="") as fk:
    w = csv.writer(fk); w.writerow(["item", "aud_item", "model", "rid"])
    for i, r in enumerate(pick):
        m, t = txt[r["response_id"]]
        if len(t) > 3000: t = t[:800] + "\n[... cut ...]\n" + t[-2200:]
        fb.write(f"=== ITEM A{i} | Q: {m['q_str']} | correct answer: {m['answer']} | values: {m['x_name']}={m['x_value']}; {m['y_name']}={m['y_value']}\n{t}\n\n")
        w.writerow([f"A{i}", r["item"], r["model"], r["response_id"]])
print(len(pick))
