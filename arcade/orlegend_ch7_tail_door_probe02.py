"""Test both cave exit edges after safe retreat; no RAM mutations."""
import json,sys
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch7-tail-door-practice-02');out.mkdir(exist_ok=False)
roots={'hit':Path('arcade/runs/orlegend/bt/one-life-ch7-tail-range-practice-03/130-170.state')}
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for source,root in roots.items():
 for side in ['left','right']:
  for ty in [120,140,160,180,200,220,240,256]:
   e.restore(root.read_bytes());initial=o=observation(e);inputs=[];phase=0
   for t in range(1000):
    if phase==0:
     if abs(o['y']-240)>3:k=['down' if o['y']<240 else 'up']
     else:phase=1;k=[side]
    elif phase==1:
     if (side=='left' and o['x']>34) or (side=='right' and o['x']<609):k=[side]
     else:phase=2;k=[]
    else:
     k=['down' if o['y']<ty else 'up'] if abs(o['y']-ty)>3 else [side]
    e.step(k);inputs.append(k);o=observation(e)
    if o['hp']<=0 or o['lives']<2 or o['stage_raw']!=1539:break
   name=f'{source}-{side}-{ty}';row={'name':name,'frames':len(inputs),'after':o,'clock':e.ram_view()[0xc06f]};rows.append(row);print(json.dumps(row),flush=True)
   (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'tail_door','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
