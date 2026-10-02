"""Collect legitimate tail drops after clearing the hazard."""
import sys,json
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch7-tail-pickup-practice-01');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for ty in [190,195,200,210,230]:
 e.restore(Path('arcade/runs/orlegend/bt/one-life-ch7-tail-range-practice-03/130-170.state').read_bytes());initial=o=observation(e);inputs=[];events=[];points=[(30,200,120),(140,190,120),(323,ty,120),(610,200,0)];idx=age=0
 for t in range(1500):
  tx,y,hold=points[idx];k=[]
  if abs(o['y']-y)>3:k=['down' if o['y']<y else 'up']
  elif abs(o['x']-tx)>3:k=['right' if o['x']<tx else 'left']
  else:
   k=['attack'] if age%4<2 else [];age+=1
   if age>=hold:idx+=1;age=0
   if idx>=len(points):k=['right'];idx=len(points)-1
  e.step(k);inputs.append(k);now=observation(e)
  if o['resources']['inventory']!=now['resources']['inventory']:events.append({'frame':t+1,'o':now})
  o=now
  if o['hp']<=0 or o['lives']<2 or o['stage_raw']!=1539:break
 name=str(ty);row={'name':name,'frames':len(inputs),'after':o,'events':events,'clock':e.ram_view()[0xc06f]};rows.append(row);print(json.dumps(row),flush=True)
 (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'tail_pickup_exit','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
