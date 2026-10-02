"""Pick the nearby real lightning sword before the automatic room transition."""
import sys,json
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-bull-pickup-practice-01');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for name in ['stay','left','right']:
 e.restore(Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-02/checkpoints/depth-072.state').read_bytes());initial=o=observation(e);inputs=[];events=[]
 for t in range(180):
  k=[name] if name!='stay' and t<2 else ['attack'] if t%4<2 else []
  e.step(k);inputs.append(k);now=observation(e)
  if now['resources']['inventory']!=o['resources']['inventory']:events.append({'frame':t+1,'o':now})
  o=now
  if o['hp']<=0 or o['lives']<2 or o['stage_raw']!=1792 or any(v['id']==22 for v in o['resources']['inventory']):break
 row={'name':name,'frames':len(inputs),'after':o,'events':events};rows.append(row);print(json.dumps(row),flush=True)
 (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'bull_lightning_sword_pickup','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
