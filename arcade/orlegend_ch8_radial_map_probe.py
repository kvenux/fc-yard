import sys,json,argparse
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM,sha
from orlegend_bt_train import observation
parser=argparse.ArgumentParser();parser.add_argument('--state');parser.add_argument('--output');args=parser.parse_args()
out=Path(args.output or 'arcade/runs/orlegend/bt/one-life-ch8-radial-map-probe-01');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);source=Path(args.state or 'arcade/runs/orlegend/bt/one-life-ch8-loot-mobs-reuse-practice-07/final.state');e.restore(source.read_bytes());o=observation(e);wait=[]
for t in range(900):
    if o['player_state']==2 and not o['air_mask'] and o['player_move']<=4:break
    e.step([]);wait.append([]);o=observation(e)
raw=e.save();initial=o;rows=[]
for direction in [['up'],['left'],['down'],['right'],['up','left'],['down','left'],['down','right'],['up','right']]:
    e.restore(raw);inputs=[['c']]*2+[[]]*10+[direction]*2+[[]]*8
    for k in inputs:e.step(k)
    o=observation(e);rows.append({'direction':direction,'selected':o['resources']['selected'],'menu_open':o['resources']['menu_open'],'hp':o['hp'],'inventory':o['resources']['inventory']})
    print(json.dumps(rows[-1]),flush=True)
assert all(r['menu_open'] and r['hp']==initial['hp'] for r in rows)
assert sorted(set(r['selected'] for r in rows))==list(range(len(initial['resources']['inventory'])))
mapping={}
for r in sorted(rows,key=lambda r:len(r['direction'])):mapping.setdefault(str(r['selected']),r['direction'])
(out/'result.json').write_text(json.dumps({'scope':'ordinary inputs, read-only native menu feedback','source':str(source),'state_sha256':sha(source),'initial':initial,'wait_frames':len(wait),'directions':rows,'map':mapping},indent=2));print(mapping);e.close()
