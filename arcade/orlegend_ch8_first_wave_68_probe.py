import sys,json
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM,action
from orlegend_bt import Controller
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-first-wave-68-probe-01');out.mkdir(exist_ok=False);e=Emulator(ROM,deterministic=True,headless=True);raw=Path('arcade/runs/orlegend/bt/one-life-ch8-dragon-68-exit-practice-02/final.state').read_bytes();rows=[]
for name,dist,align,jump in [('policy',32,10,0),('close',32,10,0),('wide',56,14,0),('jump',32,10,30)]:
 e.restore(raw);initial=o=observation(e);ctrl=Controller(json.loads(Path('arcade/orlegend-bt-ch8-search-policy-14.json').read_text()));inputs=[];had=False
 for f in range(1000):
  k=ctrl.choose(o,f) if name=='policy' else action(o,f,{'distance':dist,'align':align,'jump':jump,'rush':0,'period':4}) if o['enemies'] else []
  e.step(k);inputs.append(k);o=observation(e);had=had or bool(o['enemies'])
  if o['hp']<=0 or o['lives']<2 or had and not o['enemies']:break
 row={'name':name,'frames':len(inputs),'o':o,'clock':e.ram_view()[0xc06f]};rows.append(row);print(json.dumps(row),flush=True)
 if o['hp']>0 and o['lives']==2:(out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':f'first_wave_68_{name}','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
