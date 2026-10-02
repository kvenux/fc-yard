"""Probe item drops from the fourth-chapter shell with ordinary inputs."""
import json
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt import Controller
from orlegend_bt_train import observation
from orlegend_beam import keys
out=Path('arcade/runs/orlegend/bt/one-life-ch4-shell-practice-01');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);raw=Path('arcade/runs/orlegend/bt/one-life-ch4-boss-dps-practice-03/initial.state').read_bytes();rows=[]
spec=json.loads(Path('arcade/orlegend-bt-ch4-search-policy.json').read_text())
try:
 for item in [None,8,19]:
  for offset in [-20,0,20]:
   for distance in [25,50]:
    e.restore(raw);o=observation(e);memory={};ctrl=Controller(spec);inputs=[];events=[];used=item is None
    for t in range(720):
     if not used:
      result=ctrl.select_item({'o':o,'frame':t},memory,{'ids':[item],'radial_select':True,'timeout':45,'cooldown':180});k=result.buttons
      if not any(v['id']==item for v in o['resources']['inventory']) or t>=160:used=True
     else:
      dx=1858-o['x'];dy=206+offset-o['y'];k=[]
      if abs(dx)>distance:k.append('right' if dx>0 else 'left')
      elif o['player_facing']!='right':k.append('right')
      if abs(dy)>4:k.append('down' if dy>0 else 'up')
      if t%4<2:k.append('attack')
     before=o;e.step(k);inputs.append(k);o=observation(e)
     if o['resources']['inventory']!=before['resources']['inventory']:events.append({'frame':t,'resources':o['resources'],'position':[o['x'],o['y']]})
     if o['hp']<=0 or o['lives']<2:break
    name=f'{item}-{offset}-{distance}';row={'name':name,'frames':len(inputs),'after':o,'events':events};rows.append(row);print(json.dumps(row),flush=True)
    (out/(name+'.state')).write_bytes(e.save());(out/(name+'-inputs.json')).write_text(json.dumps(inputs));(out/'result.json').write_text(json.dumps(rows,indent=2))
finally:e.close()
