import sys,json
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-max-cancel-probe-01');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);raw=Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-18/checkpoints/depth-087.state').read_bytes();rows=[]
for name,k in [('neutral',[]),('attack',['attack']),('ab',['attack','jump']),('abc',['attack','jump','c']),('rush',['down','jump']),('right',['right']),('left',['left']),('up',['up']),('down',['down']),('item',['d']),('menu',['c']),('jump',['jump'])]:
    e.restore(raw);initial=o=observation(e);inputs=[]
    for t in range(600):
        keys=k if t%4<2 else [];e.step(keys);inputs.append(keys);o=observation(e)
        if o['hp']<=0 or o['lives']<2 or o['player_state']!=6:break
    boss=int.from_bytes(e.ram_view()[0x11a88:0x11a8a],'little')
    row={'name':name,'frames_to_exit':len(inputs),'boss_hp':boss,'hp':o['hp'],'pose':[o['player_state'],o['player_move']],'meter':o['resources']['meter'],'clock':e.ram_view()[0xc06f]};rows.append(row);print(json.dumps(row),flush=True)
    if o['hp']>0 and o['lives']==2:
        (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':name,'inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
