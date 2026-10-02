import sys,json,copy
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
from orlegend_bt import load
import orlegend_beam_parallel as b
out=Path('arcade/runs/orlegend/bt/one-life-ch8-dragon-finish-probe-01');out.mkdir(exist_ok=False)
spec=load('arcade/orlegend-bt-ch8-search-policy-03.json');b.initialize(spec);e=b.worker;raw=Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-04/checkpoints/depth-075.state').read_bytes();e.restore(raw);o=observation(e);rows=[]
for name in ['policy','boss_policy','boss_combat','finish_8','finish_19','finish_10','charge']:
 r=b.rollout((raw,o,0,0,0,name,150,8,2,[1793],[(1793,0)]));row={k:v for k,v in r.items() if k not in ('state','inputs')};row['name']=name;rows.append(row)
 if r['valid']:(out/f'{name}.state').write_bytes(r['state']);(out/f'{name}-plan.json').write_text(json.dumps({'initial':o,'after':r['o'],'macros':[{'name':name,'inputs':r['inputs']}]}))
 print(json.dumps(row),flush=True)
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()

