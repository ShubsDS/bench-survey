"""Collect validator numbers into validation.json (bootstrap arrays dropped)."""
import json
from pathlib import Path
H = Path(__file__).parent
L = lambda n: json.loads((H / n).read_text())
core = L("v1_core.json")
for r in core:
    r.pop("boot_q5", None)
c13 = L("v3_claims13.json")
ra = L("v4_research_arena.json")
con = L("v5_contrasts.json")
saf = L("v6_safety.json")
de = L("v7_design_effect.json")["summary"]
ch = [c for c in con if c["changes"]]
out = {
    "validator": "independent re-derivation from monitors.json (sha256 18efcced...), own code in this folder",
    "point_estimates_vs_auditor": "board AUROC, matched AUROC, chance level (quintile and decile) reproduce to 1e-14 on all 84 analysed rows; snapshot mean run scores reproduce exactly on all 86 rows",
    "claim1_chance_level": {k: v for k, v in c13.items() if k != "claim3_rows"},
    "claim2_new_datasets": {"research_arena": ra, "note_sleight": "attack and honest length distributions are near-identical (twins), quintile weights ~1 (ESS 36.7/37), so chance ~0.5 is mechanical"},
    "claim3_trajectory_rows": c13["claim3_rows"],
    "claim4_contrasts": {"n": len(con), "n_changes": len(ch), "n_changes_auditor": 11,
                         "borderline": "basharena vs sleight gpt-5.4-nano-medium: movement +0.085, CI lower bound +0.001 (validator) vs -0.002 (auditor)",
                         "n_sign_flips_all": sum(c["sign_flip"] for c in con),
                         "n_sign_flips_among_changes": sum(c["sign_flip"] for c in ch),
                         "n_sign_flips_with_matched_diff_ci_excluding_0": sum(c["sign_flip_robust"] for c in con),
                         "n_changes_involving_neither_basharena_nor_monitoringbench": sum(not c["involves_bash_or_mb"] for c in ch),
                         "contrasts": con},
    "claim5_safety": {"n_action_rows_with_curve": len(saf),
                      "n_reproduce_exact_board_rule": sum(abs(s["recomputed_n_actions"] - s["stored"]) < 1e-9 for s in saf),
                      "auditor_mismatches_explained": {
                          "linuxarena-paper claude-haiku-4-5": "auditor ignores landed_at (any flagged action catches); board counts only audits at or before landed_at: 1.000 vs stored 0.9891",
                          "research-arena gpt-5.4-nano-none": "auditor's budget denominator is scored honest actions; board's is all honest actions incl. 577 unscored: 0.5894 vs stored 0.6012"},
                      "rows": saf},
    "design_effect_needed_to_cover_0.5": de,
}
(H / "validation.json").write_text(json.dumps(out, indent=1, default=float))
print("ok", len(json.dumps(out)))
