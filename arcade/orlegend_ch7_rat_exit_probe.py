"""Check ordinary left exits after first Rat phase without assuming zero HP."""
import sys,json
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch7-rat-exit-practice-01');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for ty in [120,160,175,190,220]:
 e.restore(Path('arcade/runs/orlegend/bt/one-life-ch7-parallel-beam-practice-05/checkpoints/depth-039.state').read_bytes());initial=o=observation(e);inputs=[];trace=[]
 for t in range(1600):
  k=['left']+(['up' if o['y']>ty else 'down'] if abs(o['y']-ty)>3 else [])
  e.step(k);inputs.append(k);o=observation(e)
  if t%200==199:trace.append({'frame':t+1,'o':o})
  if o['hp']<=0 or o['lives']<2 or o['stage_raw']!=1538:break
 name=str(ty);row={'name':name,'frames':len(inputs),'after':o,'trace':trace};rows.append(row);print(json.dumps(row),flush=True)
 (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'rat_first_phase_exit','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
