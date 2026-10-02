import sys,json
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-bull-intro-charge-probe-01');out.mkdir(exist_ok=False);e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for name in ['hold','pulse2','pulse4']:
 e.restore(Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-10/checkpoints/depth-038.state').read_bytes());initial=o=observation(e);inputs=[];trace=[]
 for t in range(520):
  k=['attack','jump','c'] if o['resources']['meter']<96 and (name=='hold' or t%(4 if name=='pulse2' else 8)<(2 if name=='pulse2' else 4)) else []
  e.step(k);inputs.append(k);o=observation(e)
  if t%20==19:trace.append({'frame':t+1,'o':o})
  if o['hp']<=0 or o['lives']<2 or any(v['hp']>=100 and v['state']!=1 for v in o['enemies']):break
 row={'name':name,'frames':len(inputs),'o':o,'clock':e.ram_view()[0xc06f],'trace':trace};rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='trace'}),flush=True);(out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':name,'inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
