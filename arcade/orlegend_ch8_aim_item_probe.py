import sys,json,copy,itertools
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt import Controller
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-aim-item-probe-01');out.mkdir(exist_ok=False)
base=json.loads(Path('arcade/orlegend-bt-ch8-search-policy-17.json').read_text())
e=Emulator(ROM,deterministic=True,headless=True);raw=Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-18/checkpoints/depth-050.state').read_bytes();rows=[]
for ident,aim in itertools.product([6,9,10,19],[False,True]):
    e.restore(raw);initial=o=observation(e);inputs=[];s=copy.deepcopy(base)
    s['tree']={'type':'action','name':'aimed_item' if aim else 'select_item','params':{'ids':[ident],'radial_select':True,'timeout':90,'cooldown':99999,'min_hp':1,'aim_y':8,'prepare_timeout':240}}
    ctrl=Controller(s);ctrl.scene=1795;ctrl.boss_slots={0};consumed=None;start_count=next(v['count'] for v in o['resources']['inventory'] if v['id']==ident)
    for t in range(700):
        k=ctrl.choose(o,t) if consumed is None else [];e.step(k);inputs.append(k);o=observation(e)
        count=sum(v['count'] for v in o['resources']['inventory'] if v['id']==ident)
        if count<start_count and consumed is None:consumed=t+1
        if o['hp']<=0 or o['lives']<2 or (consumed is not None and t+1-consumed>=300):break
    boss=int.from_bytes(e.ram_view()[0x11a88:0x11a8a],'little');name=f'item{ident}-aim{int(aim)}'
    initial_boss=max(v['hp'] for v in initial['enemies'])
    row={'name':name,'frames':len(inputs),'consumed_at':consumed,'initial_boss_hp':initial_boss,'damage':initial_boss-boss,'o':o,'clock':e.ram_view()[0xc06f],'events':ctrl.events};rows.append(row);print(json.dumps(row),flush=True)
    if o['hp']>0 and o['lives']==2:
        (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':name,'inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
