import sys,json
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM,action
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-bull-24-finisher-probe-01');out.mkdir(exist_ok=False);e=Emulator(ROM,deterministic=True,headless=True);raw=Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-17/checkpoints/depth-073.state').read_bytes();rows=[]
for name in ['ab4','ab8','ab12','ab16','attack','attack1','rush','adaptive_ab']:
 e.restore(raw);initial=o=observation(e);inputs=[];health=[]
 for t in range(1800):
  if not o['enemies']:k=[]
  elif name=='attack':k=action(o,t,{'distance':32,'align':10,'period':4,'jump':0,'rush':0})
  elif name=='attack1':k=['attack'] if t%2==0 else []
  elif name=='rush':
   from orlegend_beam import keys
   k=keys('rush',o,t)
  elif name=='adaptive_ab':k=['attack','jump'] if o['player_state']==2 and o['hp']>8 and t%4<2 else []
  else:
   period=int(name[2:]);k=['attack','jump'] if t%period<2 and o['hp']>8 else []
  before=o;e.step(k);inputs.append(k);o=observation(e)
  if before['hp']!=o['hp']:health.append({'frame':t+1,'from':before['hp'],'to':o['hp'],'boss':o['enemies']})
  if o['hp']<=0 or o['lives']<2 or o['stage_byte']>=8:break
 row={'name':name,'frames':len(inputs),'o':o,'clock':e.ram_view()[0xc06f],'health':health};rows.append(row);print(json.dumps(row),flush=True)
 if o['hp']>0 and o['lives']==2:(out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':f'bull24_{name}','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
