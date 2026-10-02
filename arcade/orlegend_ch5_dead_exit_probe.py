"""Diagnose exit after death animation. This root already loses a life: not acceptance."""
import sys,json
sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch5-dead-exit-diagnostic-01');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);e.restore(Path('arcade/runs/orlegend/bt/one-life-ch5-full-area-parallel-beam-practice-01/checkpoints/depth-127.state').read_bytes());e.step([],1100);raw=e.save();rows=[]
for tx,ty in [(1988,90),(1988,130),(1988,210),(1672,124),(1783,130),(1940,205),(1400,130)]:
 e.restore(raw);o=observation(e)
 for t in range(1800):
  k=[]
  if abs(o['x']-tx)>4:k.append('right' if o['x']<tx else 'left')
  if abs(o['y']-ty)>4:k.append('down' if o['y']<ty else 'up')
  if t%4<2:k.append('attack')
  e.step(k);o=observation(e)
  if o['stage_byte']>=5:break
 row={'target':[tx,ty],'frame':t+1,'after':o,'clock':e.ram_view()[0xc06f]};rows.append(row);print(json.dumps(row),flush=True)
 e.av_enable=3;e.headless=False;e.step([]);e.picture().save(out/f'{tx}-{ty}.png');e.av_enable=2;e.headless=True
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
