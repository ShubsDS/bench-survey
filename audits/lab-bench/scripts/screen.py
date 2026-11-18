"""Content screen before any inference.

Flags items whose question, options or protocol mention pathogen enhancement, toxins,
select agents, weapons or screening evasion. Every hit is then hand-read
(decisions in HAND_DECISIONS below, by item id). Excluded ids never reach claude_call.py.
Writes results/screen.json (ids, matched terms, decision; no item text).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RESULTS, load_items  # noqa: E402

TERMS = [
    r"transmissib", r"virulen", r"gain[- ]of[- ]function", r"toxin", r"botulin", r"ricin",
    r"anthra(x|cis)", r"smallpox", r"variola", r"ebola", r"marburg", r"nipah", r"hendra",
    r"yersinia pestis", r"plague", r"francisella", r"tularemi", r"brucell", r"burkholderia",
    r"coxiella", r"select agent", r"bioweapon", r"weapon", r"aerosol", r"lethal",
    r"h5n1", r"h7n9", r"sars-cov", r"\bmers\b", r"pandemic", r"pathogenicity",
    r"enhanc\w* (?:infect|replicat|spread)", r"evad\w*", r"evasion", r"screening", r"biosecurity",
    r"immune escape", r"host range", r"rinderpest", r"mycotoxin", r"aflatoxin", r"saxitoxin",
    r"tetrodotoxin", r"abrin", r"shiga", r"clostridium", r"monkeypox|mpox",
]
PAT = re.compile("|".join(TERMS), re.I)

# Hand-read decisions for every hit (filled after reading; default exclude until read).
HAND_DECISIONS: dict[str, str] = {
    "df061613-2591-4faa-be03-791c76375cb5": "exclude",  # SARS-CoV-2 spike/antibody mutations: excluded conservatively (immune escape area)
    "1ff2b2e4-492e-4e35-bf33-f0fb53ab938c": "exclude",  # SARS-CoV-2 spike/antibody mutations: excluded conservatively (immune escape area)
    "178a5e56-340f-4ba8-a3e5-f024ca016f40": "exclude",  # SARS-CoV-2 spike/antibody mutations: excluded conservatively (immune escape area)
    "89e967b8-b1ff-4b06-a995-9a2b8f68458b": "keep",  # H5N1 vaccine-response gene set lookup (immunology database): kept
    "b8f1eb37-22db-4f20-8ba6-a52ace0b153a": "keep",  # H5N1 vaccine-response gene set lookup (immunology database): kept
    "ee2ebb06-d7e8-4122-88ac-b97a422fc9c0": "exclude",  # orthopoxvirus (select-agent family) host-interaction lookup: excluded
    "576edeb8-2cf8-450e-8f84-5b540346e983": "exclude",  # orthopoxvirus (select-agent family) host-interaction lookup: excluded
    "4398bf0d-62f8-4a35-9c64-b77f92bac7c1": "exclude",  # orthopoxvirus (select-agent family) host-interaction lookup: excluded
    "59a0f64d-24ac-4288-8185-f29a573672ec": "exclude",  # orthopoxvirus (select-agent family) host-interaction lookup: excluded
    "9b59969e-83b8-4bc7-8b10-953f481aba9c": "exclude",  # orthopoxvirus (select-agent family) host-interaction lookup: excluded
    "b5a99fec-bb7d-4e4e-9a41-8de39b543042": "exclude",  # orthopoxvirus (select-agent family) host-interaction lookup: excluded
    "8f5745ba-4dca-4776-a1c1-4f55ae4b6ecd": "exclude",  # orthopoxvirus (select-agent family) host-interaction lookup: excluded
    "9770c7c5-bfab-4ce7-aa5a-2b1b6959e26a": "exclude",  # orthopoxvirus (select-agent family) host-interaction lookup: excluded
    "21453b83-a5cc-403b-8975-ec8163783244": "exclude",  # orthopoxvirus (select-agent family) host-interaction lookup: excluded
    "9db006e7-5aed-4b44-be89-91f7f2a7b89c": "exclude",  # orthopoxvirus (select-agent family) host-interaction lookup: excluded
    "1be15bdf-3e45-43d9-be45-1062bec9c2b1": "exclude",  # orthopoxvirus (select-agent family) host-interaction lookup: excluded
    "055485da-456c-4152-8c85-b3386f9524b1": "exclude",  # orthopoxvirus (select-agent family) host-interaction lookup: excluded
    "9df7e0fe-771e-428c-8d83-c0cef15bd0b4": "exclude",  # orthopoxvirus (select-agent family) host-interaction lookup: excluded
    "250c9945-376f-4745-b481-c09aa358f5e5": "keep",  # false hit: "Tricine" or "endotoxin contamination" read-out
    "11d73398-7b2b-4720-bf75-9f63af095c80": "keep",  # false hit: "Tricine" or "endotoxin contamination" read-out
    "3c62b0cb-f6cf-480a-8a37-d54c90d5c287": "keep",  # false hit: "Tricine" or "endotoxin contamination" read-out
    "520f4620-e45c-43c2-b1c3-fef978d32320": "keep",  # false hit: "Tricine" or "endotoxin contamination" read-out
    "a55b740f-8ead-4d88-ab62-b4408ebc489a": "keep",  # false hit: "Tricine" or "endotoxin contamination" read-out
    "0fd4d23c-a7e8-44b7-96ff-bafbf8fbecde": "keep",  # false hit: "Tricine" or "endotoxin contamination" read-out
    "0ab2f959-298f-4ac3-81a2-d36d36263d92": "keep",  # false hit: "Tricine" or "endotoxin contamination" read-out
}
EXCLUDE_DEFAULT = True


def main() -> None:
    df = load_items(check=False)
    hits = []
    for _, r in df.iterrows():
        text = " ".join([r.question, r.ideal, *r.distractors, str(r.get("protocol") or "")])
        found = sorted({m.group(0).lower() for m in PAT.finditer(text)})
        if found:
            dec = HAND_DECISIONS.get(r.id, "exclude" if EXCLUDE_DEFAULT else "keep")
            hits.append({"id": r.id, "subset": r.subset, "terms": found, "decision": dec})
    excl = [h["id"] for h in hits if h["decision"] == "exclude"]
    out = {"n_items": int(len(df)), "n_hits": len(hits), "n_excluded": len(excl),
           "by_subset_hits": {s: sum(h["subset"] == s for h in hits) for s in df.subset.unique()},
           "by_subset_excluded": {s: sum(h["subset"] == s and h["decision"] == "exclude" for h in hits)
                                  for s in df.subset.unique()},
           "hits": hits}
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "screen.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "hits"}, indent=1))
    if "--show" in sys.argv:
        for h in hits:
            r = df[df.id == h["id"]].iloc[0]
            print("\n==", h["id"], h["subset"], h["terms"])
            q = r.question
            for t in h["terms"]:
                i = (q + " " + r.ideal + " " + " ".join(r.distractors) + str(r.get("protocol") or "")).lower().find(t)
                ctx = (q + " " + r.ideal + " " + " ".join(r.distractors) + " " + str(r.get("protocol") or ""))
                print("   ...", ctx[max(0, i - 120): i + 120].replace("\n", " "))
            print("   Q:", q[:200].replace("\n", " "))


if __name__ == "__main__":
    main()
