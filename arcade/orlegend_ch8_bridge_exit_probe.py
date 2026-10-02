"""Route from the cleared bridge wave to the fire dragon; normal inputs only."""
import sys,json,copy
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt import Controller,load
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-bridge-exit-practice-02');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);rows=[];spec=load('arcade/orlegend-bt-ch8-search-policy-03.json')
for name,ty in [('policy',None),('jump124',124),('jump140',140),('jump155',155),('clear_bomb',None)]:
 e.restore(Path('arcade/runs/orlegend/bt/one-life-ch8-bridge-backtrack-practice-01/880.state').read_bytes());initial=o=observation(e);inputs=[];events=[];trace=[];ctrl=Controller(spec);discard=Controller({'parameters':spec['parameters'],'tree':{'type':'action','name':'select_item','params':{'ids':[4],'reserves':{'15':1},'radial_select':True,'timeout':90,'cooldown':0}}})
 for t in range(2400):
  if name=='clear_bomb' and any(v['id']==4 and v['count']>0 for v in o['resources']['inventory']):k=discard.choose(o,t)
  elif ty is None or o['enemies']:k=ctrl.choose(o,t)
  else:
   k=['right']+(['up' if o['y']>ty else 'down'] if abs(o['y']-ty)>3 else [])
   if t%30<2:k=[v for v in k if v!='down']+['jump']
  e.step(k);inputs.append(k);now=observation(e)
  if now['hp']!=o['hp'] or now['resources']['inventory']!=o['resources']['inventory']:events.append({'frame':t+1,'o':now})
  o=now
  if t%200==199:trace.append({'frame':t+1,'o':o})
  if o['hp']<=0 or o['lives']<2 or any(v['hp']>=100 for v in o['enemies']):break
 row={'name':name,'frames':len(inputs),'after':o,'events':events,'trace':trace,'clock':e.ram_view()[0xc06f]};rows.append(row);print(json.dumps(row),flush=True)
 (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'bridge_dragon_approach','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
