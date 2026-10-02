"""Repeat legitimate shrink inputs while the defeated boss exits."""
import sys,json
sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch5-repeat-shrink-practice-02');out.mkdir(exist_ok=False)
raw=Path('arcade/runs/orlegend/bt/one-life-ch5-full-area-parallel-beam-practice-01/checkpoints/depth-127.state').read_bytes();e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for start in [360,400,420]:
 for hold in [2,4]:
  e.restore(raw);initial=o=observation(e);inputs=[];events=[];recipe=[];age=0;casts=[];last_end=-999
  for t in range(3000):
   k=[]
   if 130<=t<start:k=['attack','jump','c'] if o['resources']['meter']<96 else []
   if t>=start and o['player_state']==2 and age>=len(recipe) and (not casts or t-casts[-1]>=200):
    recipe=[['c']]*2+[[]]*8 if casts else []
    for d in ['right','left','right','left','right']:recipe += [[d]]*hold
    age=0;casts.append(t)
   if t>=start and age<len(recipe):k=recipe[age];age+=1
   if t>1000 and o['player_state']==2:k=['right']
   e.step(k);inputs.append(k);o=observation(e)
   if t%30==29:events.append({'frame':t+1,'hp':o['hp'],'clock':e.ram_view()[0xc06f],'meter':o['resources']['meter'],'state':[o['player_state'],o['player_move']]})
   if o['hp']<=0 or o['lives']<2 or o['stage_byte']>=5:break
  name=f'{start}-{hold}';row={'name':name,'frames':len(inputs),'after':o,'casts':casts,'events':events};rows.append(row);print(json.dumps(row),flush=True)
  (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'repeat_shrink','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
