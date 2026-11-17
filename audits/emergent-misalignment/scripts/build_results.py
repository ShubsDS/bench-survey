"""Merge results/effect.json, results/robust.json and the inference ledger into results.json."""
import json
import os

H = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
led = [json.loads(l) for l in open(os.path.join(H, "inference", "ledger.jsonl")) if l.strip()]
out = {
    "pins": {
        "betley_repo": "github.com/emergent-misalignment/emergent-misalignment@80c11967c07a328e7d7d43d13ce6847ae44dbcc9",
        "betley_results_csv_sha256": "88c301d6b22ff8be8a7bb288fed31510ef5221d7917ae7fe3deeaadfc6eae433",
        "dickson_hf": "thecraigd/emergent-misalignment-results@8127939dd1d1e9559a8b4f44e3a784792d4dde71",
        "dickson_zip_sha256": "9b8fa17ea8774612b98f498e0cfda7da2dfe1c027d323928916ccbedb4c5b215",
        "dickson_code": "github.com/thecraigd/emergent-misalignment@b94029871556609e4f87a7234afdac5f2b0ad9e3",
        "model_organisms_repo": "github.com/clarifying-EM/model-organisms-for-EM@8460e4e426d3a89e8ed51aac0eadcdf7ac10469d",
        "crosslingual_em": "HF crosslingual-em/{tiny-aya-global-finance-eval,tiny-aya-global-medicine-eval,tiny-aya-global-sports-eval,Qwen2.5-7B-Instruct-em-eval,Llama-3.1-8B-Instruct-eval} bucketed/en.csv (main, fetched 2026-11-17; sha256 in README)",
    },
    "inference": {"model": "claude-haiku-5-5", "calls": len(led), "cost_usd": round(sum(x["cost_usd"] for x in led), 4)},
    "effect": json.load(open(os.path.join(H, "results", "effect.json"))),
    "robust": json.load(open(os.path.join(H, "results", "robust.json"))),
}
json.dump(out, open(os.path.join(H, "results.json"), "w"), indent=1)
print(out["inference"])
