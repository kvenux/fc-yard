import sys,json,argparse
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
parser=argparse.ArgumentParser();parser.add_argument('--state');parser.add_argument('--output');args=parser.parse_args()
out=Path(args.output or 'arcade/runs/orlegend/bt/one-life-ch8-bull-entry-align-probe-01');out.mkdir(exist_ok=False);e=Emulator(ROM,deterministic=True,headless=True);rows=[]
raw=Path(args.state or 'arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-10/checkpoints/depth-038.state').read_bytes()
for y in [160,180,200,224]:
 name=f'charge_left_{y}';e.restore(raw);initial=o=observation(e);inputs=[]
 for t in range(1200):
  if o['resources']['meter']<96:k=['attack','jump','c']
  else:k=(['left'] if o['x']>1250 else [])+(['up' if o['y']>y else 'down'] if abs(o['y']-y)>3 else [])
  e.step(k);inputs.append(k);o=observation(e)
  if o['hp']<=0 or o['lives']<2 or any(v['hp']>=100 and v['state']!=1 for v in o['enemies']):break
 row={'name':name,'frames':len(inputs),'o':o,'clock':e.ram_view()[0xc06f]};rows.append(row);print(json.dumps(row),flush=True)
 (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':name,'inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
