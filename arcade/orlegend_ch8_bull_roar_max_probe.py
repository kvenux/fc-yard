import sys,json,copy
from pathlib import Path
sys.path.insert(0,'arcade')
import orlegend_beam_parallel as b
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-bull-roar-max-probe-01');out.mkdir(exist_ok=False);base=json.loads(Path('arcade/orlegend-bt-ch8-search-policy-11.json').read_text());b.initialize(base);raw=Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-15/checkpoints/depth-046.state').read_bytes();b.worker.restore(raw);o=observation(b.worker);rows=[]
for name,states,charge in [('base',[1],False),('roar',[1,3],False),('roar_attack',[1,3,6],False),('roar_charge',[1,3],True)]:
 s=copy.deepcopy(base)
 for branch in s['tree']['children']:
  c=branch.get('children',[])
  if c and c[0].get('name')=='super_ready':c[0]['params']['exclude_enemy_states']=states;c[1]['params']['exclude_enemy_states']=states
  if charge and c and c[0].get('name')=='charge_ready':c[0]['params']['ignore_enemy_states']=[7,8];c[1]['params']['ignore_enemy_states']=[7,8]
 b.worker_policy=s;r=b.rollout((raw,o,0,0,0,'policy',225,8,2,[1795],[(1795,0)]));row={k:v for k,v in r.items() if k not in ['state','inputs']};row['name']=name;rows.append(row);print(json.dumps(row),flush=True)
 if r['valid']:(out/f'{name}.state').write_bytes(r['state']);(out/f'{name}-plan.json').write_text(json.dumps({'initial':o,'after':r['o'],'macros':[{'name':name,'inputs':r['inputs']}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));b.worker.close()
