import sys,json,copy
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt import Controller
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-first-wave-68-items-probe-01');out.mkdir(exist_ok=False);e=Emulator(ROM,deterministic=True,headless=True);raw=Path('arcade/runs/orlegend/bt/one-life-ch8-dragon-68-exit-practice-02/final.state').read_bytes();base=json.loads(Path('arcade/orlegend-bt-ch8-search-policy-14.json').read_text());rows=[]
for ident in [9,6,10,22]:
 s=copy.deepcopy(base);s['tree']['children'].insert(0,{'type':'sequence','children':[{'type':'condition','name':'item_ready','params':{'scenes':[1795],'choose':True,'ids':[ident],'min_hp':1,'dx':800,'dy':180}},{'type':'action','name':'select_item','params':{'ids':[ident],'radial_select':True,'timeout':45,'cooldown':99999}}]});e.restore(raw);initial=o=observation(e);ctrl=Controller(s);inputs=[];had=False
 for f in range(1200):
  k=ctrl.choose(o,f);e.step(k);inputs.append(k);o=observation(e);had=had or bool(o['enemies'])
  if o['hp']<=0 or o['lives']<2 or had and not o['enemies']:break
 row={'id':ident,'frames':len(inputs),'o':o,'clock':e.ram_view()[0xc06f],'events':ctrl.events};rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='events'}),flush=True)
 if o['hp']>0 and o['lives']==2:(out/f'item{ident}.state').write_bytes(e.save());(out/f'item{ident}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':f'first_wave_68_item{ident}','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
