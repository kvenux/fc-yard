import sys,json
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM,action
from orlegend_bt_train import observation
from orlegend_beam_parallel import damage_increment
out=Path('arcade/runs/orlegend/bt/one-life-ch8-combo-cancel-probe-01');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);raw=Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-21/checkpoints/depth-066.state').read_bytes();rows=[]
for name,period in [('base',4),('simultaneous',4),('simultaneous',8),('sequential',6),('sequential',8),('sequential',12)]:
    e.restore(raw);initial=o=observation(e);inputs=[];damage=0;empty_at=None;cycle=0
    for t in range(900):
        k=action(o,t,{'distance':32,'align':8,'jump':0,'rush':0,'period':4,'reserve_meter':True})
        if name!='base' and o['enemies']:
            v=min(o['enemies'],key=lambda v:abs(v['x']-o['x'])+3*abs(v['y']-o['y']));dx=v['x']-o['x'];dy=v['y']-o['y']
            if abs(dx)<=40 and abs(dy)<=8:
                age=cycle%period
                if name=='simultaneous':k=(['attack'] if cycle<period else ['attack','c']) if age<2 else []
                else:k=['c'] if age<2 and cycle>=period else ['attack'] if age<4 else []
                cycle+=1
            elif o['resources']['menu_open']:k=['attack'] if t%4<2 else []
        e.step(k);inputs.append(k);now=observation(e);hit,_=damage_increment(o,now,set(),e.ram_view());damage+=hit;o=now
        if not o['enemies'] and empty_at is None:empty_at=t+1
        if o['hp']<=0 or o['lives']<2 or any(v['hp']>=100 for v in o['enemies']):break
    ident=f'{name}-{period}';row={'name':ident,'frames':len(inputs),'damage':damage,'first_empty_at':empty_at,'o':o,'clock':e.ram_view()[0xc06f]};rows.append(row);print(json.dumps(row),flush=True)
    if o['hp']>0 and o['lives']==2:
        (out/f'{ident}.state').write_bytes(e.save());(out/f'{ident}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':ident,'inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
