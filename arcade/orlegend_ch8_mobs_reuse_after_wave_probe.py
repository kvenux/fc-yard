import sys,json,gzip
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-mobs-reuse-after-wave-probe-01');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);raw=Path('arcade/runs/orlegend/bt/one-life-ch8-first-wave-68-items-probe-01/item22.state').read_bytes()
plans=[json.load(gzip.open(f'arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-{pool:02}/checkpoints/depth-{depth:03}.json.gz','rt')) for pool,depth in [(9,31),(10,38)]]
rows=[]
for tx in [48,300,450,650]:
    e.restore(raw);initial=o=observation(e);inputs=[]
    for t in range(400):
        if abs(o['x']-tx)<=4 and abs(o['y']-212)<=3:break
        k=[]
        if abs(o['x']-tx)>4:k.append('right' if o['x']<tx else 'left')
        if abs(o['y']-212)>3:k.append('down' if o['y']<212 else 'up')
        e.step(k);inputs.append(k);o=observation(e)
    aligned=len(inputs)
    for plan in plans:
        for m in plan['macros']:
            for k in m['inputs']:
                e.step(k);inputs.append(k);o=observation(e)
                if o['hp']<=0 or o['lives']<2:break
            if o['hp']<=0 or o['lives']<2:break
        if o['hp']<=0 or o['lives']<2:break
    row={'target_x':tx,'aligned_frames':aligned,'frames':len(inputs),'o':o,'clock':e.ram_view()[0xc06f]};rows.append(row);print(json.dumps(row),flush=True)
    if o['hp']>0 and o['lives']==2:
        (out/f'x{tx}.state').write_bytes(e.save());(out/f'x{tx}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':f'mobs_reuse_x{tx}','inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
