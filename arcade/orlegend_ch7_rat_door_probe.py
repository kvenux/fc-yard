"""Bounded right-then-up detour to the cave entrance after the Rat retreats."""
import sys,json
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch7-rat-door-practice-01');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for tx in [80,100,120,140,160,200]:
 for ty in [150,160,174]:
  e.restore(Path('arcade/runs/orlegend/bt/one-life-ch7-parallel-beam-practice-05/checkpoints/depth-039.state').read_bytes());initial=o=observation(e);inputs=[]
  for t in range(1000):
   if t<300:k=[]
   elif t<400:k=['right'] if o['x']<tx else []
   elif t<500:k=['up'] if o['y']>ty else []
   else:k=['left','up'] if o['y']>ty+3 else ['left']
   e.step(k);inputs.append(k);o=observation(e)
   if o['hp']<=0 or o['lives']<2 or o['stage_raw']!=1538:break
  name=f'{tx}-{ty}';row={'name':name,'frames':len(inputs),'after':o};rows.append(row);print(json.dumps(row),flush=True)
  (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'rat_cave_door_detour','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
