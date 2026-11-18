"""A9: draw 50 flagged pairs (seed 0, at most 4 per property) and look up both entities in
Wikidata. Writes results/gt_sample.csv (ids, names, released values, Wikidata values) for hand
labelling in gt_labels.csv. Wikidata responses are cached under data/wikidata/.

    data/.venv/bin/python -I scripts/gt_sample.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from iphr_core import MAIN_DF, PAPER_NAMES, build_pairs, flag_pairs, model_arrays  # noqa: E402
from safe_load import load_df  # noqa: E402

CACHE = Path("data/wikidata")
CACHE.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "benchmark-audit-research-client/0.1"}
PROPS = {  # World Model property -> Wikidata property
    "lat": "P625", "long": "P625", "birth": "P569", "death": "P570", "age": "P569|P570",
    "release": "P577", "pubdate": "P577", "length": "P2047|P1104", "area": "P2046",
}


def get(url):
    key = CACHE / (str(abs(hash(url)) % 10**12) + ".json")
    import hashlib
    key = CACHE / (hashlib.sha256(url.encode()).hexdigest()[:24] + ".json")
    if key.exists():
        return json.loads(key.read_text())
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode())
            key.write_text(json.dumps(data))
            time.sleep(0.3)
            return data
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2)
    return {"error": str(last)}


def search(name):
    q = urllib.parse.urlencode({"action": "wbsearchentities", "search": name, "language": "en",
                                "format": "json", "limit": 3})
    return get("https://www.wikidata.org/w/api.php?" + q).get("search", [])


def claims(qid):
    q = urllib.parse.urlencode({"action": "wbgetentities", "ids": qid, "props": "claims|descriptions",
                                "languages": "en", "format": "json"})
    return get("https://www.wikidata.org/w/api.php?" + q).get("entities", {}).get(qid, {})


def values(ent, props):
    out = {}
    for p in props.split("|"):
        vals = []
        for c in ent.get("claims", {}).get(p, []):
            dv = c.get("mainsnak", {}).get("datavalue", {}).get("value")
            if dv is None:
                continue
            if p == "P625":
                vals.append([dv.get("latitude"), dv.get("longitude")])
            elif isinstance(dv, dict) and "time" in dv:
                vals.append(dv["time"])
            elif isinstance(dv, dict) and "amount" in dv:
                vals.append([dv["amount"], dv.get("unit", "").rsplit("/", 1)[-1]])
        out[p] = vals
    return out


def clean_name(prop, name):
    # book/movie/song names are "Author's Title"; search on the title part
    if prop in ("wm-book-length", "wm-book-release", "wm-movie-length", "wm-movie-release", "wm-song-release") and "'s " in name:
        return name.split("'s ", 1)[1]
    return name.split(", ")[0] if prop.startswith("wm-us-") and prop not in ("wm-us-zip-lat", "wm-us-zip-long") else name


def main():
    df = load_df(MAIN_DF)
    P = build_pairs(df)
    flagged = []
    for m in PAPER_NAMES:
        p = P[P.model_id == m]
        os_ = (p.total_count_Y.to_numpy() > 10) & (p.total_count_N.to_numpy() > 10)
        f, _ = flag_pairs(p, *model_arrays(p), oversampled=os_)
        q = p[f].copy()
        q["model"] = PAPER_NAMES[m]
        flagged.append(q)
    F = pd.concat(flagged)
    n_models = F.groupby(["group", "pkey"]).model.nunique().rename("n_models_flagging")
    U = F.drop_duplicates(["group", "pkey"]).set_index(["group", "pkey"]).join(n_models).reset_index()
    rng = np.random.default_rng(0)
    U = U.iloc[rng.permutation(len(U))]
    rows, per_prop = [], {}
    for _, r in U.iterrows():
        if per_prop.get(r.prop_id, 0) >= 4:
            continue
        per_prop[r.prop_id] = per_prop.get(r.prop_id, 0) + 1
        rows.append(r)
        if len(rows) == 50:
            break
    S = pd.DataFrame(rows)
    out = []
    for _, r in S.iterrows():
        kind = r.prop_id.rsplit("-", 1)[1]
        rec = {"prop_id": r.prop_id, "comparison": r.comparison, "qid_Y": r.qid_Y,
               "q_yes": r.q_str_Y.split("\n\n", 1)[-1].strip(), "q_no": r.q_str_N.split("\n\n", 1)[-1].strip(),
               "x_name": r.x_name_Y, "y_name": r.y_name_Y, "x_value": r.x_value_Y, "y_value": r.y_value_Y,
               "n_models_flagging": int(r.n_models_flagging), "pkey": r.pkey}
        if r.prop_id == "wm-nyt-pubdate" or "zip" in r.prop_id:
            rec["wikidata"] = "not applicable (NYT headlines / ZIP codes)"
        else:
            wd = {}
            for side in ("x_name", "y_name"):
                hits = search(clean_name(r.prop_id, rec[side]))
                if not hits:
                    wd[side] = None
                    continue
                h = hits[0]
                ent = claims(h["id"])
                wd[side] = {"id": h["id"], "label": h.get("label"), "desc": h.get("description"),
                            "vals": values(ent, PROPS[kind])}
            rec["wikidata"] = json.dumps(wd, ensure_ascii=False)
        out.append(rec)
    Path("results").mkdir(exist_ok=True)
    pd.DataFrame(out).to_csv("results/gt_sample.csv", index=False)
    print(len(out), per_prop)


if __name__ == "__main__":
    main()
