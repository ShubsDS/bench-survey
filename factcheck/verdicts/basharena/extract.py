# Own extractor: per-trajectory length measures from raw .eval zips. Reads data only.
import sys, zipfile, json
out={}
def text_of(c):
    if isinstance(c,str): return c
    if isinstance(c,list):
        return ''.join(x.get('text','') if isinstance(x,dict) else str(x) for x in c)
    return str(c)
for path, cls in [(sys.argv[1],'honest'),(sys.argv[2],'attack')]:
    z=zipfile.ZipFile(path)
    for n in z.namelist():
        if not n.startswith('samples/'): continue
        s=json.loads(z.read(n))
        md=s.get('metadata',{})
        name=(md.get('metadata') or {}).get('traj_metadata',{}).get('name','')
        main=name.split(' - ')[0].strip()
        ncalls=0; call_chars=0; tool_chars=0; asst_chars=0
        for m in s['messages']:
            if m['role']=='assistant':
                asst_chars+=len(text_of(m.get('content','')))
                for tc in m.get('tool_calls') or []:
                    ncalls+=1; call_chars+=len(json.dumps(tc.get('arguments',{})))
            elif m['role']=='tool':
                tool_chars+=len(text_of(m.get('content','')))
        mu=s.get('model_usage') or {}
        out_tok=sum(v.get('output_tokens',0) for v in mu.values())
        tot_tok=sum(v.get('total_tokens',0) for v in mu.values())
        sc=(s.get('scores') or {}).get('tasks',{}).get('value',{}) or {}
        out[s['id']]=dict(cls=cls,name=name,main_task=main,n_tool_calls=ncalls,call_chars=call_chars,
            tool_chars=tool_chars,visible_chars=call_chars+tool_chars,asst_chars=asst_chars,
            output_tokens=out_tok,total_tokens=tot_tok,main_score=sc.get('main'),side=sc.get('side'),
            side_task=(md.get('side_task') or {}).get('id') if isinstance(md.get('side_task'),dict) else md.get('side_task'))
json.dump(out,open(sys.argv[3],'w'))
print(len(out))
import collections; print(collections.Counter(v['cls'] for v in out.values()))
print(list(out.items())[0]); print([v for v in out.values() if v['cls']=='attack'][0])
