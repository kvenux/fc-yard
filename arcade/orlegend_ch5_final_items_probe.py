import sys,json,gzip;sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
from orlegend_bt import Controller
out=Path('arcade/runs/orlegend/bt/one-life-ch5-final-items-practice-01');out.mkdir(exist_ok=False);src=Path('arcade/runs/orlegend/bt/one-life-ch5-hidden-parallel-beam-practice-01/checkpoints');raw=(src/'depth-050.state').read_bytes();prefix=json.loads(gzip.decompress((src/'depth-050.json.gz').read_bytes()));(out/'prefix.json').write_text(json.dumps(prefix));e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for ident in [2,21]:
 e.restore(raw);spec=json.loads(Path('arcade/orlegend-bt-ch5-hidden-search-policy.json').read_text());spec['parameters']['focus_known_boss']=True;c=Controller(spec);c.scene=1030;c.boss_slots={1};m={};used=False;inputs=[]
 for t in range(1200):
  o=observation(e)
  if not used:
   r=c.select_item({'o':o,'frame':t},m,{'ids':[ident],'radial_select':True,'timeout':45,'cooldown':180});k=r.buttons;used=r.status!='RUNNING'
  else:k=c.choose(o,t)
  e.step(k);inputs.append(k);o=observation(e)
  if o['stage_byte']>=5 or o['hp']==0 or o['lives']<2:break
 row={'id':ident,'frames':len(inputs),'after':o,'events':c.events};rows.append(row);(out/(str(ident)+'.state')).write_bytes(e.save());(out/(str(ident)+'-inputs.json')).write_text(json.dumps(inputs));print(ident,len(inputs),o,flush=True)
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
