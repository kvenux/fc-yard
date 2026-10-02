"""Finish the timed boss with ordinary consecutive inventory inputs."""
import sys,json
sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch5-chain-finish-practice-01');out.mkdir(exist_ok=False)
raw=Path('arcade/runs/orlegend/bt/one-life-ch5-active-parallel-beam-practice-01/checkpoints/depth-069.state').read_bytes()
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for period in [4,8,12]:
    e.restore(raw);initial=observation(e);inputs=[];events=[];alive=True
    for t in range(2500):
        before=observation(e);k=['d'] if before['enemies'] and t%period<2 else []
        e.step(k);inputs.append(k);o=observation(e)
        if o['resources']['inventory']!=before['resources']['inventory']:events.append({'frame':t+1,'resources':o['resources']})
        if o['hp']<=0 or o['lives']<2 or o['stage_byte']>=5:break
    row={'period':period,'frames':len(inputs),'after':o,'events':events,'clock':e.ram_view()[0xc06f]};rows.append(row)
    (out/f'{period}.state').write_bytes(e.save());(out/f'{period}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':f'chain_finish_d{period}','inputs':inputs}]}));print(json.dumps(row),flush=True)
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
