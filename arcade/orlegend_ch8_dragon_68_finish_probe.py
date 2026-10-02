import sys,json
from pathlib import Path
sys.path.insert(0,'arcade')
import orlegend_beam_parallel as b
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-dragon-68-finish-probe-01');out.mkdir(exist_ok=False);base=json.loads(Path('arcade/orlegend-bt-ch8-search-policy-03.json').read_text());b.initialize(base);raw=Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-04/checkpoints/depth-054.state').read_bytes();b.worker.restore(raw);o=observation(b.worker);rows=[]
for name in ['item_10','item_19','item_22','item_8','item_18','item_6','policy']:
 b.worker_policy=base;r=b.rollout((raw,o,0,0,0,name,150,8,2,[1793],[(1793,0)]));row={k:v for k,v in r.items() if k not in ['state','inputs']};row['name']=name;rows.append(row);print(json.dumps(row),flush=True)
 if r['valid']:(out/f'{name}.state').write_bytes(r['state']);(out/f'{name}-plan.json').write_text(json.dumps({'initial':o,'after':r['o'],'macros':[{'name':name,'inputs':r['inputs']}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));b.worker.close()
