"""Check whether ordinary idle input lets the zero-HP boss finish its death sequence."""
import sys,json
sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch5-clear-wait-practice-01');out.mkdir(exist_ok=False)
raw=Path('arcade/runs/orlegend/bt/one-life-ch5-full-area-parallel-beam-practice-01/checkpoints/depth-127.state').read_bytes()
e=Emulator(ROM,deterministic=True,headless=True);e.restore(raw);initial=observation(e);inputs=[];rows=[]
for t in range(1600):
    e.step([]);inputs.append([]);o=observation(e);r=e.ram_view()
    if t%60==59:rows.append({'frame':t+1,'clock':r[0xc06f],'hp':o['hp'],'stage':o['stage_raw'],'hero':[o['player_state'],o['player_move']],'boss':[r[0x11a31],r[0x11a73],r[0x11a72],int.from_bytes(r[0x11a88:0x11a8a],'little')]})
    if o['hp']<=0 or o['lives']<2 or o['stage_byte']>=5:break
plan={'initial':initial,'after':o,'macros':[{'name':'wait_for_boss_death','inputs':inputs}]}
(out/'plan.json').write_text(json.dumps(plan,indent=2));(out/'final.state').write_bytes(e.save());(out/'result.json').write_text(json.dumps({'frames':len(inputs),'after':o,'rows':rows},indent=2));print(json.dumps({'frames':len(inputs),'after':o,'rows':rows}));e.close()
