import sys,json,copy
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
from orlegend_bt import load
import orlegend_beam_parallel as b
out=Path('arcade/runs/orlegend/bt/one-life-ch8-bull-defense-probe-01');out.mkdir(exist_ok=False)
spec=load('arcade/orlegend-bt-ch8-search-policy-03.json');b.initialize(spec);e=b.worker;raw=Path('arcade/runs/orlegend/bt/one-life-ch8-bull-threat-calibration-02/prehit-160.state').read_bytes();e.restore(raw);o=observation(e);rows=[]
for name in ['up','down','left+jump','right+jump','policy','boss_policy','item_18','item_19','item_9','item_7']:
 r=b.rollout((raw,o,0,0,0,name,90,8,2,[1795],[(1795,0)]));row={k:v for k,v in r.items() if k not in ('state','inputs')};row['name']=name;rows.append(row)
 if r['valid']:(out/f'{name}.state').write_bytes(r['state']);(out/f'{name}-plan.json').write_text(json.dumps({'initial':o,'after':r['o'],'macros':[{'name':name,'inputs':r['inputs']}]}))
 print(json.dumps(row),flush=True)
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()

