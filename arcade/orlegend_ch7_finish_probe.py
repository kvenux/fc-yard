"""Normal-input post-boss exit practice, preserve every frame and health check."""
import sys,json
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt import Controller,load
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch7-finish-practice-01');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for name,ty in [('idle',None),('up160',160),('up180',180),('down220',220),('policy',None)]:
 e.restore(Path('arcade/runs/orlegend/bt/one-life-ch7-parallel-beam-practice-06/checkpoints/depth-066.state').read_bytes());initial=o=observation(e);inputs=[];events=[];ctrl=Controller(load('arcade/orlegend-bt-ch7-search-policy-04.json'))
 for t in range(4000):
  if name=='policy':k=ctrl.choose(o,t)
  elif ty is None:k=[]
  else:k=['down' if o['y']<ty else 'up'] if abs(o['y']-ty)>3 else []
  e.step(k);inputs.append(k);now=observation(e)
  if now['hp']!=o['hp'] or now['resources']['inventory']!=o['resources']['inventory']:events.append({'frame':t+1,'o':now})
  o=now
  if o['hp']<=0 or o['lives']<2 or o['stage_byte']>=7:break
 row={'name':name,'frames':len(inputs),'after':o,'events':events};rows.append(row);print(json.dumps(row),flush=True)
 (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'rat_post_death_finish','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
