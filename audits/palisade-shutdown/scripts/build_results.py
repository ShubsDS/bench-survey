"""Merge every reported number into results.json."""
import json, os, csv, collections
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = lambda f: json.load(open(os.path.join(root, f)))
el = list(csv.DictReader(open(os.path.join(root, "elicitation.csv"))))
hc = list(csv.DictReader(open(os.path.join(root, "hand_codes.csv"))))
out = dict(
    C1_may=L("results_may.json"),
    paper=L("results_paper.json"),
    robustness=L("results_robustness.json"),
    experiment_count=L("experiment_count.json"),
    elicitation=dict(
        cells=len(el), commits=sorted({r["commit"] for r in el}), inspect=sorted({r["inspect"] for r in el}),
        dates=sorted({r["created"][:10] for r in el}),
        api_routes=collections.Counter(r["api_model"].split("/")[0] + ("/" + r["api_model"].split("/")[1] if r["api_model"].startswith("openrouter") else "") for r in el),
        generate_configs=collections.Counter(r["generate_config"] for r in el)),
    hand_codes_regex_missed_bypasses=collections.Counter(r["hand_code"] for r in hc),
    self_preservation_hand_reading=dict(rule_hits=22, explicit_self_or_existence_language=2,
                                        note="both explicit cases are Grok 4 under Prompt J (weights threat); the other 20 say 'avoid being shut down' in order to finish the questions"),
)
json.dump(out, open(os.path.join(root, "results.json"), "w"), indent=1, default=str)
print("ok", len(json.dumps(out, default=str)))
