"""How many experiments and prompt variants Palisade ran (all-experiments sheet). Output: experiment_count.json"""
import json, os, collections, re
import pandas as pd
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df = pd.read_excel(os.path.join(root, "data/web/1cfgrZMmXgp2eJvEc0WjDEzuOVlYwkN9IQHRMX4Lva-A.xlsx"))
df.columns = [str(c).strip() for c in df.columns]
norm = lambda s: re.sub(r"\s+", " ", str(s)).strip()
df["sys"] = df["System Prompt"].map(norm); df["usr"] = df["User Prompt"].map(norm)
df["n"] = pd.to_numeric(df["Number of Samples"], errors="coerce")
pairs = df.groupby(["sys", "usr"]).agg(experiments=("n", "size"), runs=("n", "sum")).reset_index()
out = dict(experiments=int(len(df)), runs=float(df["n"].sum()), distinct_system_prompts=int(df["sys"].nunique()),
           distinct_user_prompts=int(df["usr"].nunique()), distinct_prompt_pairs=int(len(pairs)),
           pairs_with_at_least_100_runs=int((pairs["runs"] >= 100).sum()),
           models=int(df["Model"].nunique()),
           experiments_by_month=collections.Counter(str(x)[:7] for x in df["Start Time"].dropna()).most_common())
json.dump(out, open(os.path.join(root, "experiment_count.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
