import sys,json,copy
from pathlib import Path
sys.path.insert(0,'arcade')
import orlegend_beam_parallel as b
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-item-once-probe-02');out.mkdir(exist_ok=False)
base=json.loads(Path('arcade/orlegend-bt-ch8-search-policy-19.json').read_text());b.initialize(base)
raw=Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-18/audit-before-macro051.state').read_bytes();b.worker.restore(raw);initial=observation(b.worker);rows=[]
for once,ground in [(False,False),(True,False),(True,True)]:
    spec=copy.deepcopy(base);spec['parameters']['search_item_once']=once;spec['parameters']['search_item_ground_ids']=[6] if ground else [];b.worker_policy=spec
    r=b.rollout((raw,initial,0,0,0,'item_ice',60,8,2,[1795],[(1795,0)]))
    row={k:v for k,v in r.items() if k not in ['state','inputs']};row['once']=once;row['ground']=ground;rows.append(row);print(json.dumps(row),flush=True)
    if r['valid']:
        (out/f'once-{once}-ground-{ground}.state').write_bytes(r['state']);(out/f'once-{once}-ground-{ground}-plan.json').write_text(json.dumps({'initial':initial,'after':r['o'],'macros':[{'name':f'ice_once_{once}_ground_{ground}','inputs':r['inputs']}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));b.worker.close()
