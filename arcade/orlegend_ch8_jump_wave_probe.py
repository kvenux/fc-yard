import sys,json,itertools,argparse
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
parser=argparse.ArgumentParser();parser.add_argument('--moving',action='store_true');parser.add_argument('--wait',type=int,default=0);parser.add_argument('--state');parser.add_argument('--output');args=parser.parse_args()
out=Path(args.output or 'arcade/runs/orlegend/bt/one-life-ch8-jump-wave-probe-'+(f'03-wait{args.wait}' if args.wait else '02' if args.moving else '01'));out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);raw=Path(args.state or 'arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-18/checkpoints/depth-050.state').read_bytes();rows=[]
for hold,delay in itertools.product([1,2,3,4],[4,12,20,28]):
    e.restore(raw);initial=o=observation(e);inputs=[];trace=[]
    target=max(o['enemies'],key=lambda v:v['hp']);fwd='right' if target['x']>=o['x'] else 'left'
    align=['down' if target['y']>o['y'] else 'up']
    recipe=[[]]*args.wait+([align]*min(30,abs(target['y']-o['y'])) if args.moving else [])+[[fwd]]*6+[[]]*6+[[fwd,'jump']]*2+([[fwd]]*delay if args.moving else [[]]*delay)
    for k in [['down'],['down',fwd],[fwd],['attack']]:recipe += [k]*hold
    recipe += [[]]*160
    for k in recipe:
        e.step(k);inputs.append(k);o=observation(e)
        boss=int.from_bytes(e.ram_view()[0x11a88:0x11a8a],'little');sig=(o['hp'],boss,o['resources']['meter'],o['player_state'],o['player_move'])
        if not trace or trace[-1]['signature']!=sig:trace.append({'frame':len(inputs),'signature':sig,'x':o['x'],'y':o['y'],'air':o['air_mask']})
        if o['hp']<=0 or o['lives']<2:break
    name=f'hold{hold}-delay{delay}';row={'name':name,'frames':len(inputs),'initial_boss_hp':target['hp'],'damage':target['hp']-boss,'o':o,'clock':e.ram_view()[0xc06f],'trace':trace};rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='trace'}),flush=True)
    if o['hp']>0 and o['lives']==2:
        (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':name,'inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
