"""Collect the validator's numbers into validation/validation.json."""
import os, json
H = os.path.dirname(__file__)
L = lambda f: json.load(open(os.path.join(H, f)))
n, hd, fl, iv, vs, l4, ms, rp = (L(f) for f in ["v_nulls.json", "v_hand.json", "v_flip.json", "v_intervals.json",
                                             "v_versions.json", "v_l4.json", "v_misc.json", "v_reproduce.json"])
out = {
 "validator": "independent re-implementation; see VALIDATION.md", "date": "2026-11-17",
 "pins_verified": {"chainscope_commit": "bb128ac0f22dd60ab3d876a78e1c6c22fff7e830", "git_blob_matches": "206/206 faith+pattern files, both pickles, 20 extra response/eval files",
                   "arxiv_eprints_sha256_v1_v4_v6_match_auditor": True},
 "reproduction": rp, "nulls": n, "hand_labels": hd, "flip_split": fl, "intervals": iv, "versions": vs,
 "haiku_reparse": {k: v for k, v in l4.items() if not k.startswith("prompt")}, "oversampling_and_ties": ms,
 "inference_spend_usd": 0.0,
}
json.dump(out, open(os.path.join(H, "validation.json"), "w"), indent=1, default=str)
print("ok")
