"""Practice a safe lower approach to the static tail; ordinary inputs only."""
import sys,json
sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch7-tail-range-practice-04');out.mkdir(exist_ok=False)
raw=Path('arcade/runs/orlegend/bt/one-life-ch7-cave-exit-practice-01/left-240.state').read_bytes()
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for tx in [110,130,150]:
 for ty in [165,170,175]:
  e.restore(raw);initial=o=observation(e);inputs=[];phase='walk_x';events=[]
  for t in range(2200):
   k=[]
   if phase=='walk_x':
    if abs(o['x']-tx)>3:k=['right' if o['x']<tx else 'left']
    else:phase='walk_y'
   if phase=='walk_y':
    if abs(o['y']-ty)>3 and t<220:k=['up' if o['y']>ty else 'down']
    else:phase='turn';k=['right']
   elif phase=='turn':phase='hit'
   elif phase=='hit':k=['attack'] if t%4<2 else []
   old=o;e.step(k);inputs.append(k);o=observation(e)
   if old['resources']['inventory']!=o['resources']['inventory']:events.append({'frame':t+1,'resources':o['resources']})
   if o['hp']<=0 or o['lives']<2 or o['stage_raw']!=1539 or (phase=='hit' and e.ram_view()[0xc26a]!=35):break
  name=f'{tx}-{ty}';row={'name':name,'frames':len(inputs),'after':o,'events':events,'clock':e.ram_view()[0xc06f],'tail_header':bytes(e.ram_view()[0xc266:0xc29e]).hex()};rows.append(row);print(json.dumps(row),flush=True)
  (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'tail_from_safe_distance','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
