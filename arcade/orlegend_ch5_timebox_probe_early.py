"""Try normal chest routes after a bounded stone push; watch only the clock."""
import sys,json
sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch5-timebox-practice-02');out.mkdir(exist_ok=False)
raw=Path('arcade/runs/orlegend/bt/one-life-ch5-stone-practice-01/frame-240.state').read_bytes()
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for direction in ['right','left']:
    for y in [100,120,150,180,210,240]:
        e.restore(raw);inputs=[];events=[];start=e.ram_view()[0xc06f];old_time=start;recovered=False
        for t in range(900):
            o=observation(e);dy=y-o['y'];k=[]
            if abs(dy)>3:k=['down' if dy>0 else 'up']
            elif t<140:k=[]
            else:k=[direction]+(['attack'] if t%4<2 else [])
            e.step(k);inputs.append(k);o=observation(e);now_time=e.ram_view()[0xc06f]
            if now_time>old_time+5:
                events.append({'frame':t+1,'before':old_time,'after':now_time,'scene':o['stage_raw'],'o':o})
                if o['stage_raw']==1028:recovered=True;break
            old_time=now_time
            if o['hp']<=0 or o['lives']<2 or o['stage_raw']!=1028:break
        name=f'{direction}-{y}';row={'name':name,'initial_clock':start,'clock':now_time,'recovered':recovered,'frames':len(inputs),'after':o,'events':events};rows.append(row)
        (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-inputs.json').write_text(json.dumps(inputs));print(json.dumps(row),flush=True)
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
