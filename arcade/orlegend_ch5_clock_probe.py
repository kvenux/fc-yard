import sys,json;sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
from orlegend_beam import keys
out=Path('arcade/runs/orlegend/bt/one-life-ch5-clock-practice-01');out.mkdir(exist_ok=False);raw=Path('arcade/runs/orlegend/bt/one-life-ch5-parallel-beam-practice-01/checkpoints/depth-090.state').read_bytes();e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for mode in ['loot','push','push_attack']:
 for target_y in [120,136,150,163]:
  e.restore(raw);o=observation(e);initial=o;inputs=[];events=[]
  for t in range(600):
   if mode=='loot':k=keys('loot',o,t)
   elif t<80:k=['left']
   elif t<200:k=['up' if o['y']>target_y else 'down'] if abs(o['y']-target_y)>3 else []
   else:k=['right']+(['up' if o['y']>target_y else 'down'] if abs(o['y']-target_y)>3 else [])
   if mode=='push_attack' and t%4<2:k.append('attack')
   old=o;e.step(k);inputs.append(k);o=observation(e)
   if old['resources']['inventory']!=o['resources']['inventory']:events.append({'frame':t,'resources':o['resources']})
   if o['hp']==0 or o['lives']<2:break
  name=f'{mode}-{target_y}';row={'name':name,'after':o,'events':events};rows.append(row);(out/(name+'.state')).write_bytes(e.save());(out/(name+'-inputs.json')).write_text(json.dumps(inputs));print(name,o['hp'],o['x'],o['y'],o['enemies'],o['resources'],events,flush=True)
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
