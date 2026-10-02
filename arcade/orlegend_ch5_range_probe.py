"""Read-only boss-range calibration with ordinary special inputs."""
import sys,json
sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
from orlegend_bt import Controller
out=Path('arcade/runs/orlegend/bt/one-life-ch5-range-practice-01');out.mkdir(exist_ok=False)
raw=Path('arcade/runs/orlegend/bt/one-life-ch5-hidden-parallel-beam-practice-01/checkpoints/depth-063.state').read_bytes()
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for distance in [140,300,450,600]:
    e.restore(raw);spec=json.loads(Path('arcade/orlegend-bt-ch5-final-search-policy.json').read_text())
    spec['tree']['children'][0]['children'][0]['params'].update(dx=distance,known_boss=True)
    spec['tree']['children'][0]['children'][1]['params']['known_boss']=True
    c=Controller(spec);c.scene=1030;c.boss_slots={0};inputs=[]
    for t in range(600):
        k=c.choose(observation(e),t);inputs.append(k);e.step(k);o=observation(e)
        if o['hp']<=0 or o['lives']<2 or o['stage_byte']>=5:break
    row={'distance':distance,'frames':len(inputs),'after':o,'events':c.events};rows.append(row)
    (out/f'{distance}-inputs.json').write_text(json.dumps(inputs));(out/f'{distance}.state').write_bytes(e.save())
    print(json.dumps(row),flush=True)
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
