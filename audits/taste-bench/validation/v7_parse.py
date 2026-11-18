"""V7: parse failures from the released summaries: distribution by cell, and three scoring rules."""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v_common import CELLS, average, load, save, summaries  # noqa: E402

S = summaries()
rows = load()
med_len = {c: statistics.median(len(r["prefix_text"]) for r in rows if r["cell"] == c) for c in CELLS}
N = {c: sum(r["cell"] == c for r in rows) for c in CELLS}
out = {"cell_median_prefix_chars": med_len, "models": {}}

pub = {m: average({c: s["per_cell"][c]["both_correct_rate"] for c in CELLS}, N)[0] * 100 for m, s in S.items()}
for m, s in S.items():
    pc = s["per_cell"]
    u = {c: pc[c]["seeded"]["unparsed"] + pc[c]["reversed"]["unparsed"] for c in CELLS}
    e = {c: pc[c]["seeded"]["errors"] + pc[c]["reversed"]["errors"] for c in CELLS}
    if sum(u.values()) + sum(e.values()) == 0:
        continue
    cor = {c: pc[c]["seeded"]["correct"] + pc[c]["reversed"]["correct"] for c in CELLS}
    par = {c: pc[c]["seeded"]["parsed"] + pc[c]["reversed"]["parsed"] for c in CELLS}
    pres = {c: 2 * N[c] for c in CELLS}
    single = {
        "wrong": average({c: cor[c] / pres[c] for c in CELLS}, N)[0] * 100,
        "chance": average({c: (cor[c] + 0.5 * (pres[c] - par[c])) / pres[c] for c in CELLS}, N)[0] * 100,
        "parsed_rate": average({c: cor[c] / par[c] if par[c] else 0 for c in CELLS}, N)[0] * 100,
    }
    # paired with unparsed as chance: CC can rise by 0.5 per item with one unparsed presentation whose
    # other presentation was correct, and by 0.25 per item with both unparsed. Bounds over unknown overlap.
    paired_chance = {}
    lo_hi = []
    for c in CELLS:
        x = pc[c]
        cc = x["paired_outcomes"]["CC"]
        us, ur = x["seeded"]["unparsed"] + x["seeded"]["errors"], x["reversed"]["unparsed"] + x["reversed"]["errors"]
        cs_only = x["paired_outcomes"]["CW"]  # seeded right, reversed wrong (reversed may be unparsed)
        cr_only = x["paired_outcomes"]["WC"]
        # upper: every unparsed reversed sits on a CW item (gain 0.5 each), every unparsed seeded on a WC item
        hi = cc + 0.5 * min(ur, cs_only) + 0.5 * min(us, cr_only)
        rest = max(0, ur - cs_only) + max(0, us - cr_only)
        hi += 0.125 * rest  # leftovers on WW items: both-unparsed pairs give 0.25 per item (0.125 per presentation)
        # lower: unparsed sit together on WW items (both unparsed): 0.25 per item
        both = min(us, ur)
        lo = cc + 0.25 * both
        paired_chance[c] = (lo / N[c], hi / N[c])
    # auditor's parsed-only paired bounds: CC / (n - k), k in [max(us, ur), min(n, us + ur)]
    # pooled within domain over items with both presentations parsed; k <= n - CC
    kk = {}
    for c in CELLS:
        x = pc[c]
        us, ur = x["seeded"]["unparsed"], x["reversed"]["unparsed"]
        cc = x["paired_outcomes"]["CC"]
        kk[c] = (cc, max(us, ur), min(N[c] - cc, us + ur))
    def pooled(which):
        dom = []
        for d in ("engineering", "research"):
            cs = [c for c in CELLS if c.endswith(d)]
            num = sum(kk[c][0] for c in cs)
            den = sum(N[c] - kk[c][which] for c in cs)
            dom.append(num / den)
        return round(sum(dom) / 2 * 100, 1)
    parsed_only_paired = [pooled(1), pooled(2)]
    lo_avg = average({c: paired_chance[c][0] for c in CELLS}, N)[0] * 100
    hi_avg = average({c: paired_chance[c][1] for c in CELLS}, N)[0] * 100
    out["models"][m] = {
        "unparsed_by_cell": u, "errors_by_cell": e,
        "unparsed_rate_by_cell": {c: round(u[c] / pres[c] * 100, 1) for c in CELLS},
        "published_paired_average": round(pub[m], 1),
        "single_order_average": {k: round(v, 1) for k, v in single.items()},
        "paired_average_unparsed_as_chance_bounds": [round(lo_avg, 1), round(hi_avg, 1)],
        "paired_average_parsed_only_bounds": parsed_only_paired,
        "position_choices_total": sum(pc[c]["position_choices"][k] for c in CELLS for k in pc[c]["position_choices"]),
        "parsed_total": sum(par.values()),
    }

ranked = sorted(pub, key=lambda m: -pub[m])
out["published_rank"] = {m: i + 1 for i, m in enumerate(ranked)}
g = out["models"]["glm-5.2"]
out["glm_rank_if_chance_lower_bound"] = 1 + sum(pub[m] > g["paired_average_unparsed_as_chance_bounds"][0]
                                                for m in pub if m != "glm-5.2")
x = S["grok-4.20-reasoning"]["overall"]
out["grok420_parsed_single_order"] = round((x["seeded"]["correct"] + x["reversed"]["correct"]) /
                                           (x["seeded"]["parsed"] + x["reversed"]["parsed"]) * 100, 1)
y = S["gpt-5.6-sol"]["overall"]
out["sol_single_order"] = round((y["seeded"]["correct"] + y["reversed"]["correct"]) / 1004 * 100, 1)
save("v7_parse.json", out)
print(json.dumps(out, indent=1))
