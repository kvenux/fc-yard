"""Normal jump-attack calibration for the hanging spiders in chapter five."""
import gzip,json
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch5-ceiling-practice-01');out.mkdir(exist_ok=False)
raw=Path('arcade/runs/orlegend/bt/one-life-ch5-finish-parallel-beam-practice-01/checkpoints/depth-048.state').read_bytes();e=Emulator(ROM,deterministic=True,headless=True);rows=[]
try:
 for y in [110,120,140,160]:
  for period in [24,32,48]:
   e.restore(raw);o=observation(e);inputs=[]
   for t in range(720):
    k=['right'];phase=t%period
    if abs(o['y']-y)>4:k.append('up' if o['y']>y else 'down')
    if phase<2:k=[v for v in k if v!='down']+['jump']
    elif 6<=phase<8 or 12<=phase<14:k.append('attack')
    e.step(k);inputs.append(k);o=observation(e)
    if o['lives']<2 or o['hp']==0:break
   name=f'{y}-{period}';row={'name':name,'frames':len(inputs),'after':o};rows.append(row);(out/(name+'.state')).write_bytes(e.save());(out/(name+'-inputs.json')).write_text(json.dumps(inputs));print(json.dumps(row),flush=True)
 (out/'result.json').write_text(json.dumps(rows,indent=2))
finally:e.close()
