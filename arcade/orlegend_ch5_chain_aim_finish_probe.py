"""Align ordinary item projectiles while finishing the timed final spider."""
import sys,json
sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch5-chain-finish-practice-02');out.mkdir(exist_ok=False)
raw=Path('arcade/runs/orlegend/bt/one-life-ch5-active-parallel-beam-practice-01/checkpoints/depth-069.state').read_bytes()
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for target_y in [120,125,132,0]:
    e.restore(raw);initial=observation(e);inputs=[];events=[]
    for t in range(2500):
        before=observation(e);targets=before['enemies'];k=['d'] if targets and t%4<2 else []
        ty=target_y or (max(targets,key=lambda v:v['hp'])['y'] if targets else before['y'])
        dy=ty-before['y']
        if abs(dy)>2:k.append('down' if dy>0 else 'up')
        e.step(k);inputs.append(k);o=observation(e)
        if o['resources']['inventory']!=before['resources']['inventory']:events.append({'frame':t+1,'resources':o['resources']})
        if o['hp']<=0 or o['lives']<2 or o['stage_byte']>=5:break
    row={'target_y':target_y,'frames':len(inputs),'after':o,'events':events,'clock':e.ram_view()[0xc06f]};rows.append(row)
    (out/f'{target_y}.state').write_bytes(e.save());(out/f'{target_y}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':f'chain_finish_aim_{target_y}','inputs':inputs}]}));print(json.dumps(row),flush=True)
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
