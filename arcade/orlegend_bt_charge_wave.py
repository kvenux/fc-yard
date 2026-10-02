"""Cold ordinary-input trials: charge and spend on mobs, or reserve for boss."""
import concurrent.futures,copy,itertools,json,time
from pathlib import Path
from orlegend_bt_sweep import execute

root=Path('arcade/runs/orlegend/bt/one-life-charge-wave2-01')
root.mkdir(exist_ok=False)
base=json.loads(Path('arcade/runs/orlegend/bt/one-life-telegraph2-01/dx160-dy40-hold30-focus0.json').read_text())
jobs=[];started=time.perf_counter()
for boss,safe,dx,dy in itertools.product([False,True],[60,120],[140,240],[24,60]):
    spec=copy.deepcopy(base);spec['parameters']['scenes']['257'].update(reserve_meter=True,jump=0,rush=0)
    charge={'type':'sequence','children':[
        {'type':'condition','name':'charge_ready','params':{'scenes':[257],'min_x':700,'min_y':380,'safe_dx':safe,'safe_dy':24,'require_boss':boss}},
        {'type':'action','name':'charge_meter','params':{'abort_on_threat':True,'safe_dx':safe,'safe_dy':24,'max_hold':80,'cooldown':15,'timeout':600}}]}
    super_branch={'type':'sequence','children':[
        {'type':'condition','name':'super_ready','params':{'scenes':[257],'min_hp':80 if boss else 1,'dx':dx,'dy':dy,'ground_only':True}},
        {'type':'action','name':'super_command','params':{'boss_focus':boss,'hold':2,'fast_prepare':True,'cooldown':30}}]}
    children=spec['tree']['children'];idx=next(i for i,n in enumerate(children) if n.get('children',[{}])[0].get('name')=='route')
    children.insert(idx,charge);children.insert(0,super_branch)
    name=f'boss{int(boss)}-safe{safe}-dx{dx}-dy{dy}';path=root/(name+'.json');path.write_text(json.dumps(spec));jobs.append((path,root/name,2,90000))
rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    for future in concurrent.futures.as_completed([pool.submit(execute,j) for j in jobs]):
        row=future.result();rows.append(row)
        (root/'summary.json').write_text(json.dumps({'mode':'charge-wave2','wall':time.perf_counter()-started,'completed':len(rows),'total':len(jobs),'results':rows},indent=2))
        print(json.dumps(row),flush=True)
