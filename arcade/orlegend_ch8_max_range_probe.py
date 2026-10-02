import sys,json,copy
from pathlib import Path
sys.path.insert(0,'arcade')
import orlegend_beam_parallel as b
from orlegend_bt_train import observation

out=Path('arcade/runs/orlegend/bt/one-life-ch8-max-range-probe-01');out.mkdir(exist_ok=False)
base=json.loads(Path('arcade/orlegend-bt-ch8-search-policy-16.json').read_text())
b.initialize(base)
raw=Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-18/checkpoints/depth-045.state').read_bytes()
b.worker.restore(raw);initial=observation(b.worker);rows=[]
for dx,dy,menu in [(450,60,8),(200,20,8),(120,12,8),(80,12,8),(200,20,2),(120,12,2),(80,12,2)]:
    spec=copy.deepcopy(base)
    for branch in spec['tree']['children']:
        c=branch.get('children',[])
        if c and c[0].get('name')=='super_ready':
            c[0]['params'].update(dx=dx,dy=dy)
            c[1]['params'].update(menu_wait=menu)
    b.worker_policy=spec
    r=b.rollout((raw,initial,0,0,0,'boss_policy',600,8,2,[1795],[(1795,0)]))
    name=f'dx{dx}-dy{dy}-menu{menu}'
    row={k:v for k,v in r.items() if k not in ['state','inputs']};row['name']=name;rows.append(row)
    print(json.dumps(row),flush=True)
    if r['valid']:
        (out/f'{name}.state').write_bytes(r['state'])
        (out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':r['o'],'macros':[{'name':name,'inputs':r['inputs']}]}))
        (out/f'{name}-policy.json').write_text(json.dumps(spec,indent=2))
(out/'result.json').write_text(json.dumps(rows,indent=2));b.worker.close()
