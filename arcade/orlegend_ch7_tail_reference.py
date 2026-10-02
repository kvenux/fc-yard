"""Read-only replay the historical successful room to calibrate navigation."""
import sys,json
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
root=Path('arcade/runs/orlegend/bt/full-v4-screen-01/64-16');out=Path('arcade/runs/orlegend/bt/one-life-ch7-tail-reference-01');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);e.restore((root/'entry-0276441-0603.state').read_bytes());rows=[]
for i,line in enumerate((root/'inputs.jsonl').open()):
 if i<276441:continue
 if i>=282199:break
 k=json.loads(line)['buttons'];e.step(k)
 if (i-276441)%100==0 or observation(e)['stage_raw']!=1539:
  o=observation(e);row={'frame':i+1,'buttons':k,'o':o};rows.append(row);print(json.dumps(row),flush=True)
  (out/f"frame-{i+1}.state").write_bytes(e.save())
  if o['stage_raw']!=1539:break
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
