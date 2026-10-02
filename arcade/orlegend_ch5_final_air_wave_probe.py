import sys,json;sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch5-final-air-wave-practice-01');out.mkdir(exist_ok=False);raw=Path('arcade/runs/orlegend/bt/one-life-ch5-hidden-parallel-beam-practice-01/checkpoints/depth-063.state').read_bytes();e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for facing in ['left','right']:
 for delay in [6,12,18,24,30]:
  e.restore(raw);inputs=[];o=observation(e);moves={}
  for t in range(600):
   phase=t%80;k=[]
   if phase<4:k=[facing]
   elif phase<6:k=['jump']
   elif phase<6+delay:k=[]
   elif phase<8+delay:k=['down']
   elif phase<10+delay:k=['down',facing]
   elif phase<12+delay:k=[facing]
   elif phase<14+delay:k=['attack']
   e.step(k);inputs.append(k);o=observation(e);moves[(o['player_state'],o['player_move'],o['air_mask'])]=moves.get((o['player_state'],o['player_move'],o['air_mask']),0)+1
   if o['hp']==0 or o['lives']<2:break
  name=f'{facing}-{delay}';row={'name':name,'frames':len(inputs),'after':o,'moves':{str(k):v for k,v in moves.items()}};rows.append(row);(out/(name+'.state')).write_bytes(e.save());(out/(name+'-inputs.json')).write_text(json.dumps(inputs));print(name,o['hp'],o['x'],o['y'],o['enemies'],row['moves'],flush=True)
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
