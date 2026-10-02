"""Stop on a real Frisbee drop and approach from below; ordinary controls."""
import json,sys
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch7-tail-frisbee-practice-01');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);e.restore(Path('arcade/runs/orlegend/bt/one-life-ch7-cave-exit-practice-01/left-240.state').read_bytes());initial=o=observation(e);inputs=[];phase=0;drop=None
for t in range(1700):
 if phase==0:
  if abs(o['x']-130)>3:k=['right' if o['x']<130 else 'left']
  else:phase=1;k=[]
 elif phase==1:
  if abs(o['y']-165)>3 and t<220:k=['up']
  else:phase=2;k=['right']
 else:k=['attack'] if t%4<2 else []
 e.step(k);inputs.append(k);o=observation(e);r=e.ram_view()
 for i in range(80):
  b=0xc266+152*i
  if r[b+1]==2 and r[b+4]==28 and r[b+127]==10:
   drop=[int.from_bytes(r[b+20:b+22],'little'),int.from_bytes(r[b+22:b+24],'little')];break
 if drop or o['hp']<=0:break
(out/'drop.state').write_bytes(e.save());(out/'drop-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'tail_three_hits_drop','inputs':inputs}]}));print(json.dumps({'frames':len(inputs),'drop':drop,'after':o}),flush=True)
raw=e.save();rows=[]
if drop:
 for ty in [210,215,220,225,230]:
  e.restore(raw);initial=o=observation(e);inputs=[];events=[]
  for t in range(600):
   if t<50:k=['down'] if o['y']<ty else []
   elif t<160:k=['right'] if o['x']<drop[0]-10 else []
   elif t<320:k=['attack'] if t%4<2 else []
   elif t<360:k=['down'] if o['y']<237 else []
   else:k=['left'] if o['x']>33 else []
   e.step(k);inputs.append(k);now=observation(e)
   if now['resources']['inventory']!=o['resources']['inventory']:events.append({'frame':t+1,'o':now})
   o=now
   if o['hp']<=0 or o['lives']<2:break
  name=str(ty);row={'name':name,'after':o,'events':events};rows.append(row);print(json.dumps(row),flush=True)
  (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'tail_frisbee_pickup','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
