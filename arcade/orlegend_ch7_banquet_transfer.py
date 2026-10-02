"""Replay existing ordinary-input banquet candidates from the richer entry."""
import sys,json,gzip
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch7-banquet-transfer-practice-01');out.mkdir(exist_ok=False)
root=Path('arcade/runs/orlegend/bt/one-life-ch7-tail-stock-practice-02/320-200.state').read_bytes();e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for depth in [10,12,14,16,18,20,22,24]:
 p=Path(f'arcade/runs/orlegend/bt/one-life-ch7-parallel-beam-practice-04/checkpoints/depth-{depth:03d}.json.gz')
 if not p.exists():continue
 plan=json.loads(gzip.decompress(p.read_bytes()));e.restore(root);initial=o=observation(e);inputs=[]
 for m in plan['macros']:
  for k in m['inputs']:
   e.step(k);inputs.append(k);o=observation(e)
   if o['hp']<=0 or o['lives']<2:break
  if o['hp']<=0 or o['lives']<2:break
 name=f'{depth:03d}';row={'name':name,'frames':len(inputs),'after':o,'source':str(p)};rows.append(row);print(json.dumps(row),flush=True)
 (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'banquet_transferred_normal_inputs','inputs':inputs}],'source':str(p)}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
