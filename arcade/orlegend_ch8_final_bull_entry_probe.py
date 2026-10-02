import sys,json
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
from orlegend_bt import Controller,load
out=Path('arcade/runs/orlegend/bt/one-life-ch8-final-bull-entry-probe-01');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=False)
for name,ty in [('nav180',180),('nav200',200),('nav240',240),('policy',None)]:
 e.restore(Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-05/checkpoints/depth-052.state').read_bytes());initial=o=observation(e);inputs=[];trace=[];ctrl=Controller(load('arcade/orlegend-bt-ch8-search-policy-03.json'))
 for t in range(1500):
  k=ctrl.choose(o,t) if ty is None else (['down' if o['y']<ty else 'up'] if abs(o['y']-ty)>3 else ['left'])
  e.step(k);inputs.append(k);o=observation(e)
  if t%100==99:trace.append({'frame':t+1,'o':o,'clock':e.ram_view()[0xc06f]})
  if o['hp']<=0 or o['lives']<2 or o['stage_raw']!=1795 or any(v['state']!=1 for v in o['enemies']):break
 e.picture().save(out/f'{name}.png');(out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':name,'inputs':inputs}]}));(out/f'{name}-trace.json').write_text(json.dumps(trace));print(json.dumps({'name':name,'frames':len(inputs),'o':o,'clock':e.ram_view()[0xc06f]}),flush=True)
e.close()

