"""Practice ordinary attacks at visible secret-room jars; no RAM writes."""
import sys,json
sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch5-secret-pickup-practice-01');out.mkdir(exist_ok=False)
raw=Path('arcade/runs/orlegend/bt/one-life-ch5-clock-practice-01/push-150.state').read_bytes()
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for tx in [20,250,320,460]:
 for ty in [125,150,170]:
  e.restore(raw);initial=o=observation(e);inputs=[];events=[]
  for t in range(540):
   k=[]
   if abs(o['x']-tx)>10:k.append('right' if o['x']<tx else 'left')
   if abs(o['y']-ty)>5:k.append('down' if o['y']<ty else 'up')
   if t%4<2:k.append('attack')
   before=o;e.step(k);inputs.append(k);o=observation(e)
   if o['resources']['inventory']!=before['resources']['inventory']:events.append({'frame':t+1,'resources':o['resources']})
   if o['hp']<=0 or o['lives']<2:break
  name=f'{tx}-{ty}';row={'name':name,'after':o,'events':events};rows.append(row)
  (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'secret_jars','inputs':inputs}]}));print(json.dumps(row),flush=True)
  e.av_enable=3;e.headless=False;e.step([]);e.picture().save(out/f'{name}.png');e.av_enable=2;e.headless=True
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
