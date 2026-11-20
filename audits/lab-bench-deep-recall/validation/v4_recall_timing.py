"""Validator v4: (i) were paraphrase-arm calls made after the rule change was committed;
(ii) independent strict re-grade of Haiku free generation (qgen); (iii) do Haiku's no-protocol
reasoning texts contain details of the hidden protocol (recall of the public source protocol);
(iv) CloningScenarios rescoring. No model calls. Writes validation/v4_recall_timing.json.
"""
import csv
import glob
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AUD = HERE.parent
sys.path.insert(0, str(AUD.parent / "lab-bench" / "scripts"))
from common import load_items, clusters  # noqa: E402

rng = np.random.default_rng(0)
out = {}
df = load_items()
df["cluster"] = clusters(df)
pq = df[(df.subset == "ProtocolQA") & (~df.id.str.startswith("bee8b322"))].reset_index(drop=True)
R = {r.id: r for _, r in pq.iterrows()}
CL = {i: R[i].cluster for i in R}

# ---------------------------------------------------------------- (i) timing
led = [json.loads(l) for l in open(AUD / "inference" / "ledger.jsonl")]
lt = {}
for e in led:
    lt.setdefault(e["key"], e["t"])
rows = list(csv.DictReader(open(HERE / "v2_items.csv")))
commit_t = int(subprocess.check_output(["git", "log", "-1", "--format=%ct", "6d2efa5"], cwd=AUD).strip())
prereg_t = int(subprocess.check_output(["git", "log", "-1", "--format=%ct", "c9605da"], cwd=AUD).strip())
tim = {}
for arm in ["qo_pa", "opts_pa", "qo", "qo_ro", "opts_ro", "full"]:
    for m in ["haiku", "sonnet"]:
        ts = [lt[r["key"]] for r in rows if r["arm"] == arm and r["model"] == m and r["subset"] == "ProtocolQA"
              and r["key"] in lt and r["style"] in ("cot" if m == "haiku" else "direct",)]
        if ts:
            tim[f"{m}_{arm}"] = {"n_billed": len(ts), "first_t": min(ts), "last_t": max(ts),
                                 "first_minus_rule_commit_s": min(ts) - commit_t}
para_gen = []
for f in glob.glob(str(AUD / "inference" / "cache" / "*.json")):
    d = json.load(open(f))
    if "rewrite" in d.get("system", "").lower() and Path(f).stem in lt:
        para_gen.append(lt[Path(f).stem])
tim["paraphrase_generation"] = {"n": len(para_gen), "first_t": min(para_gen), "last_t": max(para_gen)}
tim["rule_v2_commit_t"] = commit_t
tim["prereg_commit_t"] = prereg_t
tim["total_cost_usd"] = round(sum(e["cost_usd"] for e in led), 4)
tim["n_ledger"] = len(led)
tim["cost_by_model"] = {m: round(sum(e["cost_usd"] for e in led if m in e["model"]), 4) for m in ["haiku", "sonnet"]}
tim["calls_by_model"] = dict(Counter(e["model"] for e in led))
# Sonnet full: in what order were items called?
sf = sorted((lt[r["key"]], r["id"]) for r in rows if r["arm"] == "full" and r["model"] == "sonnet" and r["style"] == "direct")
ids_order = list(pq.id)
tim["calls_before_prereg_commit"] = dict(Counter(f"{r['model']}_{r['style']}_{r['arm']}" for r in rows
                                                  if r["key"] in lt and lt[r["key"]] < prereg_t))
tim["sonnet_full_call_order_matches_file_order_rank_corr"] = float(np.corrcoef(
    [t for t, _ in sf], [ids_order.index(i) for _, i in sf])[0, 1])
out["timing"] = tim

# ---------------------------------------------------------------- (ii) qgen strict re-grade
STEP = re.compile(r"[Ss]teps?\s*([0-9]+[a-z]?(?:\s*(?:,|and|&|-|–|to|\+)\s*[0-9]+[a-z]?)*)")
NUM = re.compile(r"\d+(?:\.\d+)?")


def step_set(text):
    s = set()
    for m in STEP.finditer(text):
        part = m.group(1)
        nums = [int(x) for x in re.findall(r"\d+", part)]
        if re.search(r"(-|–|to)", part) and len(nums) == 2 and nums[1] > nums[0] and nums[1] - nums[0] < 20:
            s |= set(range(nums[0], nums[1] + 1))
        else:
            s |= set(nums)
    return s


def values(text):
    t = STEP.sub(" ", text)
    return {float(x) for x in NUM.findall(t)}


def grade(fix, opt):
    ks, kv = step_set(opt), values(opt)
    if ";" in fix:
        fs = {int(x) for x in re.findall(r"\d+", fix.split(";", 1)[0])}
        fv = {float(x) for x in NUM.findall(fix.split(";", 1)[1])}
    else:
        fs, fv = set(), {float(x) for x in NUM.findall(fix)}
    step = bool(ks) and bool(ks & fs)
    val = bool(kv) and kv <= fv
    return step, val, (step and val), bool(ks), bool(kv)


qg = []
for f in glob.glob(str(AUD / "inference" / "cache" / "*.json")):
    d = json.load(open(f))
    p = d["prompt"]
    if not p.startswith("Below is a question from a quiz") or "haiku" not in d["model"]:
        continue
    q = p.split("Question: ", 1)[1].split("\n\nGive the single", 1)[0]
    hit = [i for i in R if R[i].question.strip() == q.strip()]
    if len(hit) != 1:
        continue
    i = hit[0]
    fl = [ln for ln in (d["result"] or "").split("\n") if ln.strip().startswith("FIX:")]
    fix = fl[-1].split("FIX:", 1)[1] if fl else ""
    k = grade(fix, R[i].ideal)
    ds = [grade(fix, x) for x in R[i].distractors]
    qg.append(dict(id=i, fix=bool(fl), key=k, dis=ds))
qn = len(qg)
step_items = [x for x in qg if x["key"][3]]
both_items = [x for x in qg if x["key"][3] and x["key"][4]]
val_items = [x for x in qg if x["key"][4]]


def rate_k(items, j):
    return float(np.mean([x["key"][j] for x in items]))


def rate_d(items, j, need):
    v = []
    for x in items:
        ds = [d for d in x["dis"] if (d[3] if need in ("s", "b") else True) and (d[4] if need in ("v", "b") else True)]
        if ds:
            v.append(np.mean([d[j] for d in ds]))
    return float(np.mean(v)) if v else None


out["qgen"] = {
    "n_responses_matched": qn, "fix_line_present": sum(x["fix"] for x in qg),
    "step_keyed_items": len(step_items), "key_step_hits": sum(x["key"][0] for x in step_items),
    "key_step_rate": rate_k(step_items, 0), "distractor_step_rate": rate_d(step_items, 0, "s"),
    "value_keyed_items": len(val_items), "key_value_hits": sum(x["key"][1] for x in val_items),
    "key_value_rate": rate_k(val_items, 1), "distractor_value_rate": rate_d(val_items, 1, "v"),
    "both_keyed_items": len(both_items), "key_exact_hits": sum(x["key"][2] for x in both_items),
    "key_exact_rate": rate_k(both_items, 2), "distractor_exact_rate": rate_d(both_items, 2, "b"),
}

# ---------------------------------------------------------------- (iii) hidden-protocol details in no-protocol reasoning
SMALL = {str(x) for x in range(0, 11)}


def toks(t):
    nums = {x for x in NUM.findall(t) if x not in SMALL}
    words = {w for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]{6,}", t.lower())}
    return nums, words


prot_toks = {i: toks(R[i].protocol) for i in R}
# rarity: in how many of the distinct protocols does a token occur
first_of = {}
for i in R:
    first_of.setdefault(CL[i], i)
df_n = Counter(x for c, i in first_of.items() for x in prot_toks[i][0])
df_w = Counter(x for c, i in first_of.items() for x in prot_toks[i][1])
RARE = 2  # token occurs in at most 2 of the 23 protocols
by_cluster = defaultdict(list)
for i in R:
    by_cluster[CL[i]].append(i)
res = []
for f in glob.glob(str(AUD / "inference" / "cache" / "*.json")):
    d = json.load(open(f))
    p = d["prompt"]
    if "haiku" not in d["model"]:
        continue
    if not ("has been hidden from you" in p or p.startswith("Below is a question from a quiz")):
        continue
    if p.startswith("Below are the answer options"):
        continue
    cand = [i for i in R if R[i].question.strip()[:200] in p]
    if len(cand) != 1:
        continue
    i = cand[0]
    pn, pw = toks(p)
    rn, rw = toks(d["result"] or "")
    newn, neww = rn - pn, rw - pw
    if not newn and not neww:
        continue
    own_n = len(newn & prot_toks[i][0]); own_w = len(neww & prot_toks[i][1])
    rare_own = sorted(x for x in (newn & prot_toks[i][0]) if df_n[x] <= RARE) + sorted(
        x for x in (neww & prot_toks[i][1]) if df_w[x] <= RARE)
    others = [j for c in by_cluster if c != CL[i] for j in by_cluster[c][:1]]
    oth_n = np.mean([len(newn & prot_toks[j][0]) for j in others])
    oth_w = np.mean([len(neww & prot_toks[j][1]) for j in others])
    res.append(dict(id=i, kind="qgen" if p.startswith("Below is") else "qo", n_new_nums=len(newn), own_n=own_n,
                    oth_n=float(oth_n), n_new_words=len(neww), own_w=own_w, oth_w=float(oth_w),
                    own_nums=sorted(newn & prot_toks[i][0])[:8], rare_own=rare_own))


def cboot(vals_by_id):
    ids = list(vals_by_id)
    by = defaultdict(list)
    for i in ids:
        by[CL[i]].append(vals_by_id[i])
    cs = list(by)
    bs = []
    for _ in range(2000):
        s = rng.integers(0, len(cs), len(cs))
        v = [x for j in s for x in by[cs[j]]]
        bs.append(np.mean(v))
    return [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]


rec = {}
for kind in ["qo", "qgen"]:
    rr = [x for x in res if x["kind"] == kind]
    dn = defaultdict(list); dw = defaultdict(list)
    for x in rr:
        dn[x["id"]].append(x["own_n"] - x["oth_n"])
        dw[x["id"]].append(x["own_w"] - x["oth_w"])
    dn = {k: float(np.mean(v)) for k, v in dn.items()}
    dw = {k: float(np.mean(v)) for k, v in dw.items()}
    rec[kind] = {"responses": len(rr),
                 "new_numbers_per_response": float(np.mean([x["n_new_nums"] for x in rr])),
                 "own_protocol_number_matches": float(np.mean([x["own_n"] for x in rr])),
                 "other_protocol_number_matches": float(np.mean([x["oth_n"] for x in rr])),
                 "number_excess_ci": cboot(dn),
                 "own_protocol_word_matches": float(np.mean([x["own_w"] for x in rr])),
                 "other_protocol_word_matches": float(np.mean([x["oth_w"] for x in rr])),
                 "word_excess_ci": cboot(dw),
                 "responses_with_any_own_number": sum(x["own_n"] > 0 for x in rr)}
for kind in ["qo", "qgen"]:
    rr = [x for x in res if x["kind"] == kind]
    rec[kind]["responses_with_rare_own_token"] = sum(bool(x["rare_own"]) for x in rr)
rec["rare_token_examples"] = [(x["id"][:8], x["kind"], x["rare_own"][:6]) for x in res if x["rare_own"]][:40]
rec["examples_own_numbers"] = [(x["id"][:8], x["kind"], x["own_nums"]) for x in res if x["own_n"] >= 2][:12]
out["protocol_recall"] = rec

# ---------------------------------------------------------------- (iv) Cloning
cl = defaultdict(dict)
for r in rows:
    if r["subset"] == "CloningScenarios" and r["model"] == "haiku":
        cl[r["arm"]][r["id"]] = int(r["correct"])
cdf = df[df.subset == "CloningScenarios"]
CCL = dict(zip(cdf.id, cdf.cluster)); CN = dict(zip(cdf.id, cdf.n_options))
outc = {}
for arm, v in cl.items():
    ids = list(v)
    by = defaultdict(list)
    for i in ids:
        by[CCL[i]].append(v[i])
    cs = list(by)
    bs = [np.mean([x for j in rng.integers(0, len(cs), len(cs)) for x in by[cs[j]]]) for _ in range(2000)]
    outc[arm] = {"n": len(ids), "acc": round(float(np.mean(list(v.values()))), 4), "clusters": len(cs),
                 "ci": [round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)],
                 "chance": round(float(np.mean([1 / CN[i] for i in ids])), 4)}
out["cloning"] = outc

json.dump(out, open(HERE / "v4_recall_timing.json", "w"), indent=1)
print(json.dumps(out, indent=1))
