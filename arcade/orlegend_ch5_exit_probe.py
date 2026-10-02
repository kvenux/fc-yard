"""Check ordinary pickup/exit inputs around the defeated spider's body."""
import sys,json
sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch5-exit-practice-01');out.mkdir(exist_ok=False)
raw=Path('arcade/runs/orlegend/bt/one-life-ch5-full-area-parallel-beam-practice-01/checkpoints/depth-127.state').read_bytes()
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for target in ['corpse','tree',(1672,124),(1783,130),(1940,205),(1988,120)]:
    e.restore(raw);initial=observation(e);inputs=[];events=[]
    for t in range(1500):
        o=observation(e);r=e.ram_view()
        if target=='corpse':tx=int.from_bytes(r[0x11a40:0x11a42],'little',signed=True);ty=int.from_bytes(r[0x11a42:0x11a44],'little',signed=True)
        elif target=='tree':tx,ty=o['tree']
        else:tx,ty=target
        k=[]
        if abs(tx-o['x'])>4:k.append('right' if tx>o['x'] else 'left')
        if abs(ty-o['y'])>4:k.append('down' if ty>o['y'] else 'up')
        if t%4<2:k.append('attack')
        e.step(k);inputs.append(k);o=observation(e)
        if t%100==99:events.append({'frame':t+1,'clock':r[0xc06f],'o':o,'boss_state':r[0x11a73]})
        if o['hp']<=0 or o['lives']<2 or o['stage_byte']>=5:break
    name=str(target).replace(' ','');row={'target':target,'frames':len(inputs),'after':o,'events':events};rows.append(row)
    (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':f'clear_exit_{name}','inputs':inputs}]}));print(json.dumps(row),flush=True)
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
