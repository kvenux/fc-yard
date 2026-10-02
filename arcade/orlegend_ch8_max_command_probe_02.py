import sys,json,itertools
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation

out=Path('arcade/runs/orlegend/bt/one-life-ch8-max-command-probe-02');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True)
raw=Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-18/checkpoints/depth-050.state').read_bytes();rows=[]
for hold,menu,omit in itertools.product([1,2,3,4,6,8],[False,True],[False,True]):
    e.restore(raw);initial=o=observation(e);inputs=[];trace=[]
    def step(k):
        global o
        e.step(k);inputs.append(k);o=observation(e)
        signature=(o['hp'],o['player_state'],o['player_move'],o['resources']['meter'],o['resources']['menu_open'],tuple((v['hp'],v['state'],v['move']) for v in o['enemies']))
        if not trace or signature!=trace[-1]['signature']:trace.append({'frame':len(inputs),'signature':signature,'x':o['x'],'y':o['y'],'facing':o['player_facing']})
    for t in range(400):
        if o['player_state']==2 and not o['air_mask']:break
        step([])
    target=max(o['enemies'],key=lambda v:v['hp']);fwd='right' if target['x']>=o['x'] else 'left';back='left' if fwd=='right' else 'right'
    for t in range(12):
        if o['player_facing']==fwd:break
        step([fwd])
    for t in range(2):step([])
    recipe=([['c']]*2+[[]]*8) if menu else []
    dirs=[[back],[back,'down'],['down'],[fwd,'down']]+([] if omit else [[fwd]])+[[back],[fwd],['attack']]
    for k in dirs:recipe += [k]*hold
    for k in recipe:step(k)
    for t in range(240):
        if o['hp']<=0 or o['lives']<2:break
        step([])
    name=f'hold{hold}-menu{int(menu)}-omit{int(omit)}'
    boss=e.ram_view()[0x11a88]|(e.ram_view()[0x11a89]<<8)
    row={'name':name,'frames':len(inputs),'o':o,'boss_hp':boss,'damage':918-boss,'clock':e.ram_view()[0xc06f],'trace':trace};rows.append(row)
    print(json.dumps({k:v for k,v in row.items() if k!='trace'}),flush=True)
    if o['hp']>0 and o['lives']==2:
        (out/f'{name}.state').write_bytes(e.save())
        (out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':name,'inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
