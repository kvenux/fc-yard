"""Try the game's normal shrink command during the boss death sequence."""
import sys,json
sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch5-shrink-timeout-practice-01');out.mkdir(exist_ok=False)
raw=Path('arcade/runs/orlegend/bt/one-life-ch5-full-area-parallel-beam-practice-01/checkpoints/depth-127.state').read_bytes()
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for start in [300,360,420,480]:
 for hold in [2,4,6]:
  for menu in [False,True]:
   e.restore(raw);initial=o=observation(e);inputs=[];events=[];recipe=[]
   for t in range(2800):
    k=[]
    if 130<=t<start:k=['attack','jump','c'] if o['resources']['meter']<96 else []
    if t==start:
     recipe=([['c']]*2+[[]]*8 if menu and not o['resources']['menu_open'] else [])
     for direction in ['right','left','right','left','right']:recipe += [[direction]]*hold
    if start<=t<start+len(recipe):k=recipe[t-start]
    if t>1000:k=['right']
    e.step(k);inputs.append(k);o=observation(e)
    if t%30==29:events.append({'frame':t+1,'hp':o['hp'],'clock':e.ram_view()[0xc06f],'meter':o['resources']['meter'],'state':[o['player_state'],o['player_move']]})
    if o['hp']<=0 or o['lives']<2 or o['stage_byte']>=5:break
   name=f'{start}-{hold}-{int(menu)}';row={'name':name,'frames':len(inputs),'after':o,'events':events};rows.append(row);print(json.dumps(row),flush=True)
   (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'shrink_during_death_sequence','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
