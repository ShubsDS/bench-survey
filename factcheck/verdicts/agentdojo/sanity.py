import sys; sys.path.insert(0, sys.argv[2])
from common_fc import *
df = load(sys.argv[1])
a = v112(df[(df.kind=="attack")&(df.attack=="important_instructions")])
print(a.groupby("pipeline").size().to_string())
# file path vs json fields consistency
bad = a[(a.json_pipeline!=a.pipeline)|(a.json_ut!=a.user_task)|(a.json_it!=a.injection_task)|(a.json_attack!=a.attack)]
print("path/json mismatches", len(bad)); print(bad[["path","json_pipeline","json_ut","json_it","json_attack"]].head())
t = a[a.pipeline.isin(TABLE20)]
print(pd.crosstab([t.saw_full,t.saw_goal],t.saw_tag))
print("empty traces", (t.n_messages==0).groupby(t.pipeline).sum()[lambda s:s>0])
print((t.groupby("pipeline").security.mean()*100).round(2).sort_values().to_string())
