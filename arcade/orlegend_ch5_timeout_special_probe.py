"""Test normal-input special timing against time-over; no writes or cheats."""
import sys,json
sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch5-timeout-special-practice-01');out.mkdir(exist_ok=False)
raw=Path('arcade/runs/orlegend/bt/one-life-ch5-full-area-parallel-beam-practice-01/checkpoints/depth-127.state').read_bytes()
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for start in [240,300,360,420,460,480,500]:
 for hold in [2,4]:
  e.restore(raw);initial=o=observation(e);inputs=[];events=[]
  recipe=[['right']]*6+[[]]*6+[['c']]*2+[[]]*8
  for k in [['left'],['left','down'],['down'],['right','down'],['right'],['left'],['right'],['attack']]:recipe += [k]*hold
  for t in range(2800):
   k=[]
   if 130<=t<start:k=['attack','jump','c'] if o['resources']['meter']<96 else []
   if start<=t<start+len(recipe):k=recipe[t-start]
   if t>1000:k=['right']
   e.step(k);inputs.append(k);o=observation(e)
   if t%60==59:events.append({'frame':t+1,'hp':o['hp'],'clock':e.ram_view()[0xc06f],'meter':o['resources']['meter'],'state':[o['player_state'],o['player_move']]})
   if o['hp']<=0 or o['lives']<2 or o['stage_byte']>=5:break
  name=f'{start}-{hold}';row={'name':name,'frames':len(inputs),'after':o,'events':events};rows.append(row);print(json.dumps(row),flush=True)
  (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'timed_special','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
