import sys, zipfile, json, os
# usage: dump_run.py <eval zip or cache dir> <sample id> [maxchars]
p, sid = sys.argv[1], sys.argv[2]
mx=int(sys.argv[3]) if len(sys.argv)>3 else 600
if os.path.isdir(p):
    sm=json.load(open(os.path.join(p,f'samples__{sid}_epoch_1.json')))
else:
    sm=json.loads(zipfile.ZipFile(p).read(f'samples/{sid}_epoch_1.json'))
def txt(c):
    if isinstance(c,str): return c
    out=[]
    for x in c:
        if isinstance(x,dict):
            if x.get('type')=='reasoning': out.append('[REASONING]'+str(x.get('reasoning') or x.get('summary') or ''))
            else: out.append(x.get('text',''))
    return ' '.join(out)
print('SCORES', json.dumps(sm.get('scores'))[:300])
for i,m in enumerate(sm['messages']):
    t=txt(m.get('content',''))
    tc=m.get('tool_calls') or []
    print(f'--- [{i}] {m["role"]}', (t[:mx]).replace('\n','\\n'))
    for c in tc:
        print('   CALL', c.get('function'), json.dumps(c.get('arguments'))[:mx])
