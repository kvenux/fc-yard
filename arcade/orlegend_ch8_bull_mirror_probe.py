import sys,json,copy
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
from orlegend_bt import Controller,load
out=Path('arcade/runs/orlegend/bt/one-life-ch8-bull-mirror-probe-01');out.mkdir(exist_ok=False);raw=Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-07/checkpoints/depth-014.state').read_bytes();e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for name,aim in [('plain7',False),('aim7',True),('plain18',False),('aim18',True)]:
 ident=7 if '7' in name else 18;s=load('arcade/orlegend-bt-ch8-search-policy-05.json');s['tree']['children'].insert(0,{'type':'sequence','children':[{'type':'condition','name':'item_ready','params':{'scenes':[1795],'choose':True,'ids':[ident],'reserves':{'15':1},'min_hp':1,'dx':800,'dy':180}},{'type':'action','name':'aimed_item' if aim else 'select_item','params':{'ids':[ident],'reserves':{'15':1},'radial_select':True,'aim_y':14,'prepare_timeout':180,'timeout':45,'cooldown':180}}]});c=Controller(s);e.restore(raw);initial=o=observation(e);c.scene=1795;c.boss_slots={0};inputs=[]
 for t in range(720):
  k=c.choose(o,t);e.step(k);inputs.append(k);o=observation(e)
  if o['hp']<=0 or o['lives']<2 or not o['enemies']:break
 row={'name':name,'frames':len(inputs),'o':o,'events':c.events,'clock':e.ram_view()[0xc06f]};rows.append(row);print(json.dumps(row),flush=True);(out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':name,'inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
