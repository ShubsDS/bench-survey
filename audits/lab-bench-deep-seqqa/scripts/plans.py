"""Item samples and batches in priority order (prereg.md). Seed 0. Writes plans/b*.json.

Per cue subtask, the items that passed every build check (build_check.json) are put in a fixed
random order (numpy default_rng(0) permutation of the sorted ids, one draw per subtask, in the
order of build.CUE); GC-percent draws only from items that also have an I arm. Samples are
prefixes of that order, so the Sonnet sample is contained in the Haiku sample. Non-cue subtasks
use the same scheme over all 40 items.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AUD = HERE.parent
sys.path.insert(0, str(HERE))
from build import CUE, NONCUE  # noqa: E402

N_SONNET = {"Prop-seq-gcpercent-v1": 6, "ORF-seq-AAseq-v1": 6, "PCR-seq-enzprimers-v1": 6,
            "PCR-gene-enzprimers-v1": 10, "PCR-gene-gibshindprimers-v1": 10,
            "PCR-gene-gibssmaprimers-v1": 10}
N_PILOT = 2
N_HAIKU = 15
N_HAIKU_O = 8      # Haiku O and N on cue subtasks
N_SONNET_N = 3     # Sonnet N on cue subtasks
N_NONCUE_HAIKU = 6  # Haiku O and N per non-cue subtask
N_NONCUE_SONNET = 2  # Sonnet O per non-cue subtask (lowest priority)


def orders():
    arms = json.loads((AUD / "data" / "arms.json").read_text())
    rng = np.random.default_rng(0)
    out = {}
    for fam in CUE:
        ids = sorted(i for i, a in arms.items() if a["family"] == fam and "D" in a
                     and (not fam.startswith("Prop") or "I" in a))
        out[fam] = [ids[j] for j in rng.permutation(len(ids))]
    for fam in NONCUE:
        ids = sorted(i for i, a in arms.items() if a["family"] == fam)
        out[fam] = [ids[j] for j in rng.permutation(len(ids))]
    return out, arms


def cue_arms(fam):
    return ["K", "D", "I"] if fam.startswith("Prop") else ["K", "D"]  # GC: K is O


def main():
    od, arms = orders()
    P = AUD / "plans"
    P.mkdir(exist_ok=True)
    b = {}
    b["b1_sonnet_pilot"] = [{"id": i, "arm": a, "model": "sonnet"}
                            for f in CUE for i in od[f][:N_PILOT] for a in cue_arms(f)]
    b["b2_sonnet_main"] = [{"id": i, "arm": a, "model": "sonnet"}
                           for f in CUE for i in od[f][N_PILOT:N_SONNET[f]] for a in cue_arms(f)]
    b["b3_sonnet_N"] = [{"id": i, "arm": "N", "model": "sonnet"} for f in CUE for i in od[f][:N_SONNET_N]]
    b["b4_haiku_cue"] = [{"id": i, "arm": a, "model": "haiku"}
                         for f in CUE for i in od[f][:N_HAIKU] for a in cue_arms(f)]
    b["b5_haiku_O_N"] = ([{"id": i, "arm": a, "model": "haiku"} for f in CUE if not f.startswith("Prop")
                          for i in od[f][:N_HAIKU_O] for a in ["O"]]
                         + [{"id": i, "arm": "N", "model": "haiku"} for f in CUE for i in od[f][:N_HAIKU_O]]
                         + [{"id": i, "arm": a, "model": "haiku"} for f in NONCUE
                            for i in od[f][:N_NONCUE_HAIKU] for a in ["O", "N"]])
    b["b6_sonnet_noncue_O"] = [{"id": i, "arm": "O", "model": "sonnet"} for f in NONCUE
                               for i in od[f][:N_NONCUE_SONNET]]
    for k, v in b.items():
        (P / f"{k}.json").write_text(json.dumps(v, indent=0))
        print(k, len(v))
    (P / "orders.json").write_text(json.dumps(od, indent=0))


if __name__ == "__main__":
    main()
