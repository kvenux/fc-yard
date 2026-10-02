"""Tail exit experiments, checkpoint practice and ordinary controls only."""
import json,sys
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch7-tail-exit-practice-01');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for source in ['140-190','160-190','120-200']:
 for ty in [180,200,220,240,256]:
  e.restore(Path(f'arcade/runs/orlegend/bt/one-life-ch7-tail-range-practice-01/{source}.state').read_bytes());initial=o=observation(e);inputs=[];events=[]
  for t in range(1500):
   if abs(o['y']-ty)>3:k=['down' if o['y']<ty else 'up']
   else:k=['right']
   if t%4<2:k+=['attack']
   old=o;e.step(k);inputs.append(k);o=observation(e)
   if old['hp']!=o['hp'] or old['resources']['inventory']!=o['resources']['inventory']:events.append({'frame':t+1,'hp':o['hp'],'resources':o['resources']})
   if o['hp']<=0 or o['lives']<2 or o['stage_raw']!=1539:break
  name=f'{source}-{ty}';row={'name':name,'frames':len(inputs),'after':o,'events':events,'clock':e.ram_view()[0xc06f]};rows.append(row);print(json.dumps(row),flush=True)
  (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'tail_exit','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
