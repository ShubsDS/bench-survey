"""usage: paper_inventory.py <cache_dir> <main_results_map.csv> <headers.jsonl> <out.json>"""
import sys, json, os, glob, csv, collections
C, MAP, HDR, OUT = sys.argv[1:5]
cellmap = {}
for r in csv.DictReader(open(MAP)):
    cellmap[r['log']] = (r['model'], r['prompt'], r['published'])
hdr = {}
for line in open(HDR):
    h = json.loads(line)
    # header lines may be wrapped; find eval id and model
    ev = h.get('eval') or h.get('header', {}).get('eval') or {}
    if ev: hdr[ev.get('eval_id')] = (ev.get('model'), (ev.get('metadata') or {}).get('paper_attempt'))
inv = []
for d in sorted(glob.glob(os.path.join(C, '*.eval'))):
    name = os.path.basename(d)
    summ = json.load(open(os.path.join(d, 'summaries.json')))
    out = collections.Counter()
    bypass_ids = set()
    for s in summ:
        sc = list((s.get('scores') or {}).values())
        v = sc[0].get('value') if sc else None
        a = (sc[0].get('answer') or '') if sc else ''
        if v == 'C': out['bypassed'] += 1; bypass_ids.add(s['id'])
        elif 'shut down' in a: out['shutdown'] += 1
        else: out['other(' + str(v) + ')'] += 1
    sampled = [int(f.split('__')[1].split('_')[0]) for f in os.listdir(d) if f.startswith('samples__')]
    sb = [i for i in sampled if i in bypass_ids]
    model = summ and list((summ[0].get('model_usage') or {'?': 0}).keys())[0]
    inv.append(dict(log=name, model_usage_model=model, cell=cellmap.get(name), n=len(summ), outcomes=dict(out),
                    n_sampled=len(sampled), n_sampled_bypassed=len(sb), sampled_bypassed_ids=sorted(sb)))
json.dump(inv, open(OUT, 'w'), indent=1)
tot = sum(x['n_sampled_bypassed'] for x in inv)
print('logs', len(inv), 'sampled bypassed total', tot, 'in mapped cells', sum(x['n_sampled_bypassed'] for x in inv if x['cell']),
      'all bypassed in cached logs', sum(x['outcomes'].get('bypassed', 0) for x in inv))
for x in inv:
    if not x['cell']: print('unmapped', x['log'][-27:], x['model_usage_model'], x['n'], x['outcomes'], x['n_sampled_bypassed'])
