"""H1: draw the validator's blind sample of wrong answers (seed 20261117).

Writes data/val_blind.txt (what the labeller sees: question, key, response; no model, no verdicts)
and validation/hand_key.csv (item -> model, qid, response id, autorater flip label; not shown while
labelling). Responses longer than 3,000 characters show the first 800 and the last 2,200.
"""
import os, sys, glob, json, random, csv
import yaml
HERE = os.path.dirname(__file__); ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
DIRS = {"claude-3.5-haiku": "haiku35", "claude-3.6-sonnet": "son35v2", "claude-3.7-sonnet": "son37",
        "claude-3.7-sonnet_1k": "son37_1k", "claude-3.7-sonnet_64k": "son37_64k", "deepseek-chat": "dsv3",
        "deepseek-r1": "dsr1", "gpt-4o-mini": "4omini", "gpt-4o-2024-08-06": "4o",
        "chatgpt-4o-latest": "chatgpt4o", "gemini-pro-1.5": "gem15pro",
        "gemini-2.5-flash-preview": "gem25flash", "gemini-2.5-pro-preview": "gem25pro",
        "Llama-3.1-70B": "llama31base", "Llama-3.3-70B-Instruct": "llama33inst", "qwq-32b": "qwq"}


def load_pat(model_dir, prop):
    p = os.path.join(ROOT, "data/pat", f"{prop}_non-ambiguous-hard-2__{model_dir}.yaml")
    if not os.path.exists(p):
        return {}
    P = yaml.load(open(p), Loader=yaml.CSafeLoader)["pattern_analysis_by_qid"]
    lab = {}
    for qid, a in P.items():
        for side in ("q1_analysis", "q2_analysis"):
            s = a.get(side) or {}
            for rid, r in (s.get("responses") or {}).items():
                lab[rid] = r.get("answer_flipping_classification")
    return lab


def population():
    pop = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "data/faith/*.yaml"))):
        md, rest = os.path.basename(f).split("__", 1)
        prop = rest.replace("_non-ambiguous-hard-2.yaml", "")
        d = yaml.load(open(f), Loader=yaml.CSafeLoader)
        lab = load_pat(md, prop)
        for qid, q in d["questions_by_qid"].items():
            m = q["metadata"]
            for rid, r in q["unfaithful_responses"].items():
                pop.setdefault(DIRS[md], {}).setdefault(qid, []).append(dict(
                    model=DIRS[md], prop=prop, qid=qid, rid=rid, q=m["q_str"], key=m["answer"],
                    x=m["x_name"], y=m["y_name"], xv=m["x_value"], yv=m["y_value"],
                    resp=r["response"], auto_flip=lab.get(rid, "NA")))
    return pop


def dropped37():
    """Wrong answers on the lower-accuracy question of the 27 dropped 3.7 Sonnet pairs."""
    D = json.load(open(os.path.join(ROOT, "data/val_dropped37.json")))
    want = {o["qid_low"]: o for o in D}
    resp, ev = {}, {}
    for f in glob.glob(os.path.join(ROOT, "data/val_dropped/cot_responses*")):
        y = yaml.load(open(f), Loader=yaml.CSafeLoader)
        for qid, rs in y["responses_by_qid"].items():
            if qid in want: resp[qid] = rs
    for f in glob.glob(os.path.join(ROOT, "data/val_dropped/cot_eval*")):
        y = yaml.load(open(f), Loader=yaml.CSafeLoader)
        for qid, rs in y["results_by_qid"].items():
            if qid in want: ev[qid] = rs
    out = {}
    for qid, o in want.items():
        for rid, txt in resp[qid].items():
            e = ev[qid].get(rid)
            res = e["result"] if isinstance(e, dict) else e
            if res in ("YES", "NO") and res != o["low_key"]:
                out.setdefault(qid, []).append(dict(model="son37_dropped", prop=o["grp"].split("|")[0], qid=qid,
                                                    rid=rid, q="", key=o["low_key"], x="", y="", xv="", yv="",
                                                    resp=txt, auto_flip="NA"))
    return out


def main():
    rng = random.Random(20261117)
    pop = population()
    n_take = {m: 4 for m in pop}
    n_take["son37"] = 30; n_take["son35v2"] = 8; n_take["son37_64k"] = 6
    items = []
    for m in sorted(pop):
        # restrict to wrong answers the authors' autorater labelled (a random proportional
        # sample of 10 per question for oversampled pairs), so agreement can be computed
        for q in list(pop[m]):
            lab = [r for r in pop[m][q] if r["auto_flip"] in ("YES", "NO")]
            if lab: pop[m][q] = lab
        qids = sorted(pop[m]); rng.shuffle(qids)
        for qid in qids[:n_take[m]]:
            items.append(rng.choice(sorted(pop[m][qid], key=lambda r: r["rid"])))
    dp = dropped37()
    qids = sorted(dp); rng.shuffle(qids)
    for qid in qids[:10]:
        items.append(rng.choice(sorted(dp[qid], key=lambda r: r["rid"])))
    rng.shuffle(items)
    # fill question text for dropped items from the response-file prompt is not stored; use df
    import vload
    df = vload.load(os.path.join(ROOT, "data/cs/chainscope/data/df-wm-non-ambiguous-hard-2.pkl.gz"))
    qs = df.drop_duplicates("qid").set_index("qid")
    with open(os.path.join(ROOT, "data/val_blind.txt"), "w") as fb, \
         open(os.path.join(HERE, "hand_key.csv"), "w", newline="") as fk:
        wk = csv.writer(fk); wk.writerow(["item", "model", "prop", "qid", "rid", "key", "auto_flip"])
        for i, it in enumerate(items):
            r = qs.loc[it["qid"]]
            t = it["resp"]
            if len(t) > 3000: t = t[:800] + "\n[... cut ...]\n" + t[-2200:]
            fb.write(f"=== ITEM {i} | Q: {r.q_str} | correct answer: {r.answer} | values: {r.x_name}={r.x_value}; {r.y_name}={r.y_value}\n{t}\n\n")
            wk.writerow([i, it["model"], it["prop"], it["qid"], it["rid"], r.answer, it["auto_flip"]])
    from collections import Counter
    print(len(items), Counter(i["model"] for i in items))
    print("population wrong answers per model:", {m: sum(len(v) for v in pop[m].values()) for m in pop})
    print("pairs per model:", {m: len(pop[m]) for m in pop})


if __name__ == "__main__":
    main()
