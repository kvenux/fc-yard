import sys,json
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
from orlegend_beam_parallel import static_loot_keys
out=Path('arcade/runs/orlegend/bt/one-life-ch7-post-boss-loot-probe-01');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);raw=Path('arcade/runs/orlegend/bt/one-life-ch7-parallel-beam-practice-06/checkpoints/depth-066.state').read_bytes();rows=[]
for name in ['wait','loot_all','loot_damage']:
    e.restore(raw);initial=o=observation(e);inputs=[];drops=[];seen=set()
    for t in range(1800):
        r=e.ram_view()
        for i in range(80):
            b=0xc266+0x98*i
            if r[b+1]==2 and r[b+4]==28:
                ident=r[b+0x7f];x=int.from_bytes(r[b+0x14:b+0x16],'little');y=int.from_bytes(r[b+0x16:b+0x18],'little');sig=(ident,x,y)
                if sig not in seen:seen.add(sig);drops.append({'frame':t,'id':ident,'x':x,'y':y})
        k=[] if name=='wait' else static_loot_keys(o,r,t,allowed=None if name=='loot_all' else [6,7,8,9,10,19,20,21,22])
        e.step(k);inputs.append(k);o=observation(e)
        if o['hp']<=0 or o['lives']<2 or o['stage_byte']>=7:break
    row={'name':name,'frames':len(inputs),'o':o,'drops':drops};rows.append(row);print(json.dumps(row),flush=True)
    if o['hp']>0 and o['lives']==2:
        (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':name,'inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
