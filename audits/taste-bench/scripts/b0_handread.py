"""B0: write a hand-reading sample to data/handread.txt (git-ignored; contains item text)."""
import random
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from b_common import ROOT, CELLS, load_items

items = load_items()
rng = random.Random(0)
out = []
for cell in CELLS:
    pool = [r for r in items if r["cell"] == cell]
    k = 12 if cell == "parallel_research" else 13
    for r in rng.sample(pool, k):
        out.append(f"===== {r['id']} {cell} task={r['task_id']} steps={r['prefix_steps']} answer={r['answer']}\n"
                   f"QUERY: {r['query'][:600]}\n--- PREFIX TAIL ---\n{r['prefix_text'][-1500:]}\n"
                   f"--- A ---\n{r['choices'][0]}\n--- B ---\n{r['choices'][1]}\n")
(ROOT / "data/handread.txt").write_text("\n".join(out))
print(len(out))
