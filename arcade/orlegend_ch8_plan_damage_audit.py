import sys,gzip,json
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
root=Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-18')
p=json.load(gzip.open(root/'checkpoints/depth-087.json.gz','rt'))
e=Emulator(ROM,deterministic=True,headless=True);e.restore((root/'initial.state').read_bytes());rows=[]
for i,m in enumerate(p['macros']):
    before=observation(e);clock=e.ram_view()[0xc06f]
    for k in m['inputs']:e.step(k)
    after=observation(e)
    if i==49:(root/'audit-before-macro051.state').write_bytes(e.save())
    if i>=39:
        row={'macro':i+1,'name':m['name'],'frames':len(m['inputs']),'clock':[clock,e.ram_view()[0xc06f]],'hp':[before['hp'],after['hp']],'boss':[before['enemies'][0]['hp'] if before['enemies'] else None,after['enemies'][0]['hp'] if after['enemies'] else None],'meter':[before['resources']['meter'],after['resources']['meter']],'pose':[after['player_state'],after['player_move']],'inventory_before':before['resources']['inventory'],'inventory_after':after['resources']['inventory']};rows.append(row)
(root/'damage-audit-depth087.json').write_text(json.dumps(rows,indent=2))
for r in rows:print(json.dumps({k:v for k,v in r.items() if not k.startswith('inventory')}))
assert after==p['after'];e.close()
