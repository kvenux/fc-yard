import sys,json,copy
from pathlib import Path
sys.path.insert(0,'arcade')
import orlegend_beam_parallel as b
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-super-cadence-probe-01');out.mkdir(exist_ok=False)
base=json.loads(Path('arcade/orlegend-bt-ch8-search-policy-12.json').read_text());b.initialize(base)
raw=Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-12/checkpoints/depth-003.state').read_bytes();b.worker.restore(raw);initial=observation(b.worker);rows=[]
for name,hold,cool,dx in [('base',2,30,150),('fast',1,0,150),('fast_near',1,0,0),('normal_near',2,0,0),('hold3_near',3,0,0)]:
 s=copy.deepcopy(base)
 for branch in s['tree']['children']:
  c=branch.get('children',[])
  if c and c[0].get('name')=='super_ready':c[1]['params'].update(hold=hold,cooldown=cool)
  if c and c[0].get('name')=='charge_ready':c[0]['params']['safe_dx']=dx
 b.worker_policy=s;r=b.rollout((raw,initial,0,0,0,'policy',450,8,2,[1795],[(1795,0)]));row={k:v for k,v in r.items() if k not in ['state','inputs']};row['name']=name;rows.append(row);print(json.dumps(row),flush=True)
 if r['valid']:
  (out/f'{name}.state').write_bytes(r['state']);(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':r['o'],'macros':[{'name':name,'inputs':r['inputs']}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));b.worker.close()
