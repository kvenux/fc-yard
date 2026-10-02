"""Locate the ordinary stone push boundary and nearby chests; no RAM writes."""
import sys,json
sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch5-stone-practice-01');out.mkdir(exist_ok=False)
raw=Path('arcade/runs/orlegend/bt/one-life-ch5-parallel-beam-practice-01/checkpoints/depth-090.state').read_bytes()
e=Emulator(ROM,deterministic=True,headless=False);e.restore(raw);e.headless=False;e.av_enable=3;inputs=[];rows=[]
for t in range(600):
    o=observation(e)
    if t<80:k=['left']
    elif t<200:k=['up' if o['y']>150 else 'down'] if abs(o['y']-150)>3 else []
    else:k=['right']+(['up' if o['y']>150 else 'down'] if abs(o['y']-150)>3 else [])
    e.step(k);inputs.append(k);o=observation(e)
    if (t+1)%60==0 or t+1==200:
        rows.append({'frame':t+1,'o':o});e.picture().save(out/f'frame-{t+1:03d}.png')
        (out/f'frame-{t+1:03d}.state').write_bytes(e.save());(out/f'frame-{t+1:03d}-inputs.json').write_text(json.dumps(inputs))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
