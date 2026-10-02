import sys,json,collections
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
from orlegend_bt import Controller,load
out=Path('arcade/runs/orlegend/bt/one-life-ch8-emergency-finish-probe-02');out.mkdir(exist_ok=False);e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for name,interval,items,filtering in [('ab16',16,False,False),('ab48',48,False,False),('ab96',96,False,False),('items_ab16',16,True,False),('items_ab48',48,True,True)]:
 e.restore(Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-12/checkpoints/depth-052.state').read_bytes());initial=o=observation(e);inputs=[];events=[];moves=collections.Counter();s=load('arcade/orlegend-bt-ch8-search-policy-10.json');s['tree']={'type':'sequence','children':[{'type':'condition','name':'item_ready','params':{'scenes':[1795],'ids':[19,8],'choose':True,'reserves':{'15':1},'min_hp':1,'dx':800,'dy':180}},{'type':'action','name':'select_item','params':{'ids':[19,8],'reserves':{'15':1},'radial_select':True,'timeout':45,'cooldown':0}}]};s['tree']={'type':'selector','children':[s['tree'],{'type':'action','name':'combat'}]};c=Controller(s)
 for t in range(1150):
  ready=items and any(v['id'] in [8,19] and v['count']>0 for v in o['resources']['inventory']) and (not filtering or any(v['state'] in [2,3,8] for v in o['enemies']))
  if ready:k=c.choose(o,t)
  else:k=['attack','jump'] if t%interval<2 else []
  before=o;e.step(k);inputs.append(k);o=observation(e);moves[(o['player_state'],o['player_move'])]+=1
  if before['hp']!=o['hp'] or before['enemies']!=o['enemies'] and t%10==0:events.append({'frame':t+1,'o':o,'k':k})
  if o['hp']<=0 or o['lives']<2 or not o['enemies'] or o['stage_byte']>=8:break
 row={'name':name,'frames':len(inputs),'o':o,'clock':e.ram_view()[0xc06f],'moves':{str(k):v for k,v in moves.items()},'events':events};rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='events'}),flush=True);(out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':name,'inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()

