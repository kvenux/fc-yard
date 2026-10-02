import sys,json,copy
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt import Controller
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-bull-62-freeze-probe-01');out.mkdir(exist_ok=False);e=Emulator(ROM,deterministic=True,headless=True);raw=Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-17/checkpoints/depth-061.state').read_bytes();base=json.loads(Path('arcade/orlegend-bt-ch8-search-policy-14.json').read_text());rows=[]
for name in ['freeze_max','freeze_fast_max','freeze_melee','freeze_close_melee']:
 s=copy.deepcopy(base)
 for branch in s['tree']['children']:
  c=branch.get('children',[])
  if c and c[0].get('name')=='super_ready':
   c[0]['params']['ground_only']=False
   if name=='freeze_fast_max':c[1]['params'].update(turn_hold=2,turn_release=2,menu_wait=2)
 if 'melee' in name:s['tree']['children'].insert(0,{'type':'action','name':'combat','params':{'distance':12 if 'close' in name else 32,'align':8,'period':4,'jump':0,'rush':0}})
 s['tree']['children'].insert(0,{'type':'sequence','children':[{'type':'condition','name':'item_ready','params':{'scenes':[1795],'choose':True,'ids':[18],'min_hp':1,'dx':1000,'dy':180}},{'type':'action','name':'select_item','params':{'ids':[18],'radial_select':True,'timeout':45,'cooldown':99999}}]})
 e.restore(raw);initial=o=observation(e);ctrl=Controller(s);ctrl.scene=1795;ctrl.boss_slots={0};inputs=[];cleared=None
 for t in range(1800):
  k=ctrl.choose(o,t) if o['enemies'] else [];e.step(k);inputs.append(k);o=observation(e)
  if not o['enemies'] and cleared is None:cleared=t+1
  if o['hp']<=0 or o['lives']<2 or o['stage_byte']>=8:break
 row={'name':name,'frames':len(inputs),'o':o,'clock':e.ram_view()[0xc06f],'cleared_at':cleared,'events':ctrl.events};rows.append(row);print(json.dumps(row),flush=True)
 if o['hp']>0 and o['lives']==2:(out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':f'bull62_{name}','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
