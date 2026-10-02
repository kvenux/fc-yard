"""Pick up the defeated spider's drops with normal movement."""
import sys,json
sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch5-drop-practice-01');out.mkdir(exist_ok=False)
raw=Path('arcade/runs/orlegend/bt/one-life-ch5-early-active-parallel-beam-practice-01/checkpoints/depth-019.state').read_bytes()
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for tx in [1600,1750,1835,1900,1950,2000]:
    for ty in [205,223,240]:
        e.restore(raw);o=observation(e);initial=o;inputs=[];events=[]
        for t in range(420):
            k=[]
            if abs(o['x']-tx)>4:k.append('right' if o['x']<tx else 'left')
            if abs(o['y']-ty)>4:k.append('down' if o['y']<ty else 'up')
            before=o;e.step(k);inputs.append(k);o=observation(e)
            if o['resources']['inventory']!=before['resources']['inventory']:
                events.append({'frame':t+1,'before':before['resources'],'after':o['resources']})
                if any(v['id'] in [8,21] for v in o['resources']['inventory']):break
            if o['hp']<=0 or o['lives']<2:break
        name=f'{tx}-{ty}';row={'name':name,'frames':len(inputs),'after':o,'events':events};rows.append(row)
        (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-inputs.json').write_text(json.dumps(inputs));print(json.dumps(row),flush=True)
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
