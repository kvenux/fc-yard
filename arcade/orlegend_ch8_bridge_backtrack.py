"""Test safe upper-route backtracking to the remaining lower-floor enemy."""
import sys,json
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM,action
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-bridge-backtrack-practice-01');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for tx in [830,850,880]:
 e.restore(Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-03/checkpoints/depth-036.state').read_bytes());initial=o=observation(e);inputs=[];trace=[]
 for t in range(1000):
  if t<20:k=['up'] if o['y']>125 else []
  elif t<130:k=['left'] if o['x']>tx else []
  elif t<180:k=['down'] if o['y']<210 else []
  elif o['enemies']:k=action(o,t,{'distance':32,'align':10,'period':4,'jump':0,'rush':0})
  else:k=['up'] if o['y']>125 else ['right']
  e.step(k);inputs.append(k);o=observation(e)
  if t%100==99:trace.append({'frame':t+1,'o':o})
  if o['hp']<=0 or o['lives']<2 or (not o['enemies'] and o['x']>1200):break
 name=str(tx);row={'name':name,'frames':len(inputs),'after':o,'trace':trace};rows.append(row);print(json.dumps(row),flush=True)
 (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'bridge_last_mob_backtrack','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
