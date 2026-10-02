import sys,json
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-loot-prefix-reuse-probe-01');out.mkdir(exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);e.restore(Path('arcade/runs/orlegend/bt/one-life-ch7-post-boss-loot-probe-01/loot_all.state').read_bytes());initial=o=observation(e)
plan=json.loads(Path('arcade/runs/orlegend/bt/one-life-ch8-first-bull-prefix-candidate-01.json').read_text());inputs=[];trace=[]
for m in plan['macros']:
    for k in m['inputs']:
        e.step(k);inputs.append(k);o=observation(e)
        if o['hp']<=0 or o['lives']<2:break
    trace.append({'macro':m['name'],'frames':len(inputs),'o':o})
    if o['hp']<=0 or o['lives']<2:break
row={'frames':len(inputs),'o':o,'trace':trace};(out/'result.json').write_text(json.dumps(row,indent=2));print(json.dumps({k:v for k,v in row.items() if k!='trace'}))
if o['hp']>0 and o['lives']==2:
    (out/'final.state').write_bytes(e.save());(out/'plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'loot_prefix_reuse','inputs':inputs}]}))
e.close()
