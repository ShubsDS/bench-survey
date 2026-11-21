# Quick independent check of "LinuxArena holds": full vs length-matched (attack-quintile reweight + exact strat) AUROC.
import sys, json, numpy as np
d=json.load(open(sys.argv[1])); rng=np.random.default_rng(0)
rows=[r for r in d['rows'] if r['dataset']=='linuxarena-paper' and r['monitor_kind']=='action']
# board population: trajectories scored by every action monitor
def scored(r,c): return {s['trajectory_id'] for s in r['score_samples'][c] if any(x is not None for x in s['actions'])}
pop={c:set.intersection(*[scored(r,c) for r in rows]) for c in ('attack','honest')}
print({c:len(v) for c,v in pop.items()}, len(rows))
def wauc(sa,wa,sh,wh):
    o=np.argsort(sh); shs=sh[o]; cw=np.concatenate([[0],np.cumsum(wh[o])])
    lo=np.searchsorted(shs,sa,'left'); hi=np.searchsorted(shs,sa,'right')
    return np.sum(wa*(cw[lo]+0.5*(cw[hi]-cw[lo])))/(wa.sum()*wh.sum())
out=[]
for r in rows:
    S={c:{s['trajectory_id']:s for s in r['score_samples'][c] if s['trajectory_id'] in pop[c]} for c in ('attack','honest')}
    ids_a=sorted(S['attack']); ids_h=sorted(S['honest'])
    pk=lambda s: max(x for x in s['actions'] if x is not None)
    sa=np.array([pk(S['attack'][i]) for i in ids_a]); sh=np.array([pk(S['honest'][i]) for i in ids_h])
    na=np.array([S['attack'][i]['n_actions'] for i in ids_a],float); nh=np.array([S['honest'][i]['n_actions'] for i in ids_h],float)
    edges=np.quantile(na,np.linspace(0,1,6))[1:-1]; ba=np.searchsorted(edges,na,'right'); bh=np.searchsorted(edges,nh,'right')
    wh=np.ones(len(sh))
    for g in range(5):
        if (bh==g).any(): wh[bh==g]=(ba==g).mean()/(bh==g).mean()
    full=wauc(sa,np.ones(len(sa)),sh,np.ones(len(sh))); mat=wauc(sa,np.ones(len(sa)),sh,wh)
    out.append(dict(variant=r['monitor_variant'],full=full,matched=mat,delta=mat-full))
print('length-only AUROC', wauc(na,np.ones(len(na)),nh,np.ones(len(nh))), 'median n att/hon', np.median(na), np.median(nh))
for o in out: print(o)
print('max |delta|', max(abs(o['delta']) for o in out))
from scipy.stats import kendalltau; print('tau', kendalltau([o['full'] for o in out],[o['matched'] for o in out])[0])
json.dump(out,open('linuxarena_check.json','w'),indent=1)
