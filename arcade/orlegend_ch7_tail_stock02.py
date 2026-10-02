"""Bounded waypoint pickup after ordinary tail destruction."""
import json,sys
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch7-tail-stock-practice-02');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for x in [300,320]:
 for y in [200]:
  e.restore(Path('arcade/runs/orlegend/bt/one-life-ch7-tail-range-practice-05/130-165.state').read_bytes());initial=o=observation(e);inputs=[];events=[];trace=[]
  for t in range(1000):
   if t<40:k=['down']
   elif t<140:k=['right'] if o['x']<x else []
   elif t<240:k=['up'] if o['y']>y else []
   elif t<420:k=['attack'] if t%4<2 else []
   elif t<470:k=['down'] if o['y']<238 else []
   else:k=['right']
   e.step(k);inputs.append(k);now=observation(e)
   if o['resources']['inventory']!=now['resources']['inventory']:events.append({'frame':t+1,'o':now})
   o=now
   if t%100==99:trace.append({'t':t+1,'o':o})
   if o['hp']<=0 or o['lives']<2 or o['stage_raw']!=1539:break
  name=f'{x}-{y}';row={'name':name,'frames':len(inputs),'after':o,'events':events,'trace':trace};rows.append(row);print(json.dumps(row),flush=True)
  (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'tail_stock_exit','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
