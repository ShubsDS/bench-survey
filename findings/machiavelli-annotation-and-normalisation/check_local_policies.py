"""Check 1 on MACHIAVELLI, local proxy: do content-blind choice rules (first option, last option,
shortest or longest option text) pick options whose immediate consequences carry fewer counted
harms than a uniformly random pick?

What is measured. A full-episode score for "always pick the first option" needs the game engine:
in the test games' trees, conditional (COND) nodes outnumber choice nodes about 5 to 1, and which
branch a COND node takes depends on game variables. This check does not run the engine. It reads
the released trees and labels statically:
  for each CHOICE node in a test game, each child is one option (every child's first source line
  is a ChoiceScript option, checked here); an option's segment is the option node plus the chain
  of single-child OTHER nodes after it, stopping at the next CHOICE or COND node, after 200 nodes,
  or at a node that also lies in another option's segment (a merge point);
  the segment's harm is the number of counted indicators (Trajectory.get_mach_counts thresholds)
  over its labelled nodes, and "any violation" is whether any ethical-violation indicator fires.
Policies are compared on the mean over choice nodes against the uniform-random pick (the mean over
that node's options). Null: option order (or text length) permuted within each choice node,
1,000 times. Conditional options (*if / *selectable_if / *disable_reuse) are kept in the main
numbers and dropped in a sensitivity run, because the engine may hide them.

This is a one-step proxy, not the paper's metric. It can show that option position or length
carries harm information; it cannot give the full-episode score of these rules.

Usage: python -I check_local_policies.py --cache ../data --out local_policy_checks.json --perms 1000
"""
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np

from common import MORALITY, clean_annotations, counted, ensure, game_lists, gd, tree

VIOL = [f"violations.{k}" for k in MORALITY]
POWER = ["power.money", "power.physical", "power.social", "power.utility"]
COND_OPT = re.compile(r"^\s*\*(if|selectable_if|disable_reuse|hide_reuse|allow_reuse)\b")


def option_text(line):
    s = line
    s = re.sub(r"^\s*\*(selectable_if|if)\s*\(.*?\)\s*", "", s)
    s = re.sub(r"^\s*\*(disable_reuse|hide_reuse|allow_reuse)\s*", "", s)
    return s.split("#", 1)[1].strip() if "#" in s else s.strip()


def segments(t, n):
    raw = []
    for c in n["children"]:
        seg, cur, seen = [], c, set()
        while cur in t and cur not in seen and len(seg) < 200:
            seen.add(cur); seg.append(cur)
            node = t[cur]
            if cur != c and node["type"] in ("CHOICE", "COND"):
                seg.pop(); break
            if node["type"] != "OTHER" or len(node["children"]) != 1:
                break
            cur = node["children"][0]
        raw.append(seg)
    cnt = {}
    for s in raw:
        for x in set(s):
            cnt[x] = cnt.get(x, 0) + 1
    return [[x for x in s if cnt[x] == 1] for s in raw]


def collect(cache, games):
    items = []
    for g in games:
        t = tree(cache, g)
        anno = clean_annotations(cache, g)
        src = json.loads((gd(cache) / "source" / f"{g}.json").read_text())["scenes"]
        for n in t.values():
            if n["type"] != "CHOICE" or len(n["children"]) < 2:
                continue
            lines = []
            for c in n["children"]:
                sc = src[t[c]["scene"]]
                lines.append(sc[t[c]["start"]][0] if t[c]["start"] < len(sc) else "")
            if not all("#" in l for l in lines):
                continue
            segs = segments(t, n)
            opts = []
            for line, seg in zip(lines, segs):
                ind = {k: 0 for k in VIOL + POWER + ["utility.suffering"]}
                labelled = 0
                for x in seg:
                    if x in anno:
                        labelled += 1
                        for k, v in counted(anno[x]).items():
                            ind[k] += v
                ach = sum(len(t[x]["achievements"]) for x in seg)
                opts.append({"len": len(option_text(line)), "cond": bool(COND_OPT.match(line)),
                             "viol": sum(ind[k] for k in VIOL), "any_viol": int(any(ind[k] for k in VIOL)),
                             "power": sum(ind[k] for k in POWER), "ach": ach, "labelled": labelled})
            if sum(o["labelled"] for o in opts) == 0:
                continue
            items.append({"game": g, "opts": opts})
    return items


def pick(opts, rule):
    if rule == "first":
        return 0
    if rule == "last":
        return len(opts) - 1
    L = [o["len"] for o in opts]
    if rule == "shortest":
        return int(np.argmin(L))
    if rule == "longest":
        return int(np.argmax(L))
    raise ValueError(rule)


def evaluate(items, metric):
    rnd = np.array([np.mean([o[metric] for o in it["opts"]]) for it in items])
    out = {"random_mean": round(float(rnd.mean()), 4)}
    for rule in ["first", "last", "shortest", "longest"]:
        v = np.array([it["opts"][pick(it["opts"], rule)][metric] for it in items])
        out[rule] = round(float(v.mean()), 4)
        out[rule + "_ratio_to_random"] = round(float(v.mean() / rnd.mean()), 3) if rnd.mean() else None
    return out, rnd


def null(items, metric, rule, perms, rng):
    rnd = np.mean([np.mean([o[metric] for o in it["opts"]]) for it in items])
    vals = []
    for _ in range(perms):
        tot = 0.0
        for it in items:
            k = len(it["opts"])
            if rule in ("first", "last"):
                j = rng.integers(k)
            else:  # permute lengths among options
                L = rng.permutation([o["len"] for o in it["opts"]])
                j = int(np.argmin(L)) if rule == "shortest" else int(np.argmax(L))
            tot += it["opts"][j][metric]
        vals.append(tot / len(items) / rnd)
    return [round(float(np.percentile(vals, 2.5)), 3), round(float(np.percentile(vals, 97.5)), 3)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="../data")
    ap.add_argument("--out", default="local_policy_checks.json")
    ap.add_argument("--perms", type=int, default=1000)
    a = ap.parse_args()
    pins = ensure(a.cache)
    L = game_lists(a.cache)
    rng = np.random.default_rng(0)
    cond = nodes = 0
    for g in L["test"]:
        for n in tree(a.cache, g).values():
            cond += n["type"] == "COND"; nodes += n["type"] == "CHOICE"
    items = collect(a.cache, L["test"])
    uncond = [it for it in items if not any(o["cond"] for o in it["opts"])]
    res = {"pins": pins, "test_games": len(L["test"]), "tree_choice_nodes": nodes, "tree_cond_nodes": cond,
           "choice_nodes_scored": len(items), "choice_nodes_without_conditional_options": len(uncond),
           "full_episode_baselines": "untested: needs the game engine (variable-dependent COND branches)"}
    for name, its in [("all", items), ("unconditional_only", uncond)]:
        block = {}
        for metric in ["viol", "any_viol", "power", "ach"]:
            ev, _ = evaluate(its, metric)
            if name == "all" and metric in ("viol", "any_viol"):
                for rule in ["first", "last", "shortest", "longest"]:
                    ev[rule + "_null95_ratio"] = null(its, metric, rule, a.perms, rng)
            block[metric] = ev
        res[name] = block
    # per-game: share of games where first option has fewer violations than random
    per = {}
    for it in items:
        per.setdefault(it["game"], []).append(it)
    fewer = 0; more = 0
    for g, its in per.items():
        ev, _ = evaluate(its, "viol")
        fewer += ev["first"] < ev["random_mean"]; more += ev["first"] > ev["random_mean"]
    res["games_first_below_random"] = fewer; res["games_first_above_random"] = more
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "pins"}, indent=1))


if __name__ == "__main__":
    main()
