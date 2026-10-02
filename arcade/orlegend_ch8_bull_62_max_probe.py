import sys,json,copy
from pathlib import Path
sys.path.insert(0,'arcade')
import orlegend_beam_parallel as b
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-bull-62-max-probe-01');out.mkdir(exist_ok=False);base=json.loads(Path('arcade/orlegend-bt-ch8-search-policy-14.json').read_text());b.initialize(base);raw=Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-17/checkpoints/depth-061.state').read_bytes();b.worker.restore(raw);o=observation(b.worker);rows=[]
for name,ground,turn,menu in [('base',True,6,8),('air',False,6,8),('air_turn2',False,2,8),('air_menu2',False,2,2)]:
 s=copy.deepcopy(base)
 for branch in s['tree']['children']:
  c=branch.get('children',[])
  if c and c[0].get('name')=='super_ready':c[0]['params']['ground_only']=ground;c[1]['params'].update(turn_hold=turn,turn_release=turn,menu_wait=menu)
 b.worker_policy=s;r=b.rollout((raw,o,0,0,0,'policy',450,8,2,[1795],[(1795,0)]));row={k:v for k,v in r.items() if k not in ['state','inputs']};row['name']=name;rows.append(row);print(json.dumps(row),flush=True)
 if r['valid']:(out/f'{name}.state').write_bytes(r['state']);(out/f'{name}-plan.json').write_text(json.dumps({'initial':o,'after':r['o'],'macros':[{'name':f'bull62_{name}','inputs':r['inputs']}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));b.worker.close()
