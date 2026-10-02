import sys,json
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-mega-probe-02');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);raw=Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-17/checkpoints/depth-052.state').read_bytes();rows=[]
for radius in [48,80,120,180]:
    e.restore(raw);initial=o=observation(e);inputs=[];last=-100;trace=[]
    for t in range(600):
        k=[]
        if o['enemies']:
            v=max(o['enemies'],key=lambda v:v['hp']);dx=v['x']-o['x'];dy=v['y']-o['y']
            if o['player_state']==2 and not o['air_mask']:
                if abs(dy)>12:k=['down' if dy>0 else 'up']
                elif abs(dx)>radius:k=['right' if dx>0 else 'left']
                elif t-last>=30:k=['attack','jump'];last=t
            elif t-last<2:k=['attack','jump']
        e.step(k);inputs.append(k);o=observation(e)
        signature=(o['hp'],int.from_bytes(e.ram_view()[0x11a88:0x11a8a],'little'))
        if not trace or trace[-1]['signature']!=signature:trace.append({'frame':t+1,'signature':signature,'pose':[o['player_state'],o['player_move']]})
        if o['hp']<=0 or o['lives']<2 or o['stage_byte']>=8:break
    row={'radius':radius,'frames':len(inputs),'o':o,'clock':e.ram_view()[0xc06f],'trace':trace};rows.append(row);print(json.dumps(row),flush=True)
    if o['hp']>0 and o['lives']==2:
        (out/f'radius{radius}.state').write_bytes(e.save());(out/f'radius{radius}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':f'mega_radius{radius}','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
