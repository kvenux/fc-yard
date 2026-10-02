import sys,json,gzip,copy,concurrent.futures,time
from pathlib import Path
sys.path.insert(0,'arcade')
import orlegend_beam_parallel as b
from orlegend_bt import Controller
from orlegend_bt_train import observation
ROOT='arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-12/checkpoints/depth-003.state'
PLAN='arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-13/checkpoints/depth-047.json.gz'
OUT=Path('arcade/runs/orlegend/bt/one-life-ch8-bull-retiming-practice-01')
def candidate(job):
 name,inputs=job;b.worker.restore(Path(ROOT).read_bytes());initial=o=observation(b.worker);record=[];ctrl=Controller(b.worker_policy)
 for t in range(len(inputs)+1000):
  k=inputs[t] if t<len(inputs) else ctrl.choose(o,t)
  b.worker.step(k);record.append(k);o=observation(b.worker)
  if o['hp']<=0 or o['lives']<2:return {'name':name,'valid':False,'frames':len(record)}
  if o['stage_byte']>=8:break
 return {'name':name,'valid':True,'frames':len(record),'o':o,'clock':b.worker.ram_view()[0xc06f],'goal':o['stage_byte']>=8,'state':b.worker.save(),'plan':{'initial':initial,'after':o,'macros':[{'name':name,'inputs':record}]}}
def main():
 OUT.mkdir(exist_ok=False);spec=json.loads(Path('arcade/orlegend-bt-ch8-search-policy-11.json').read_text());p=json.loads(gzip.decompress(Path(PLAN).read_bytes()));macros=p['macros'];jobs=[]
 for i,m in enumerate(macros):
  if len(m['inputs'])>120 or m['name'].startswith('item') or m['name']=='policy':continue
  for cut in [30,60]:
   if cut>len(m['inputs']):continue
   seq=[k for j,v in enumerate(macros) for k in (v['inputs'][cut:] if j==i else v['inputs'])];jobs.append((f'cut-{i:02}-{cut}',seq))
 # Multiple independent short waits can also be removed together.
 candidates=[i for i,m in enumerate(macros) if m['name']=='combat' and len(m['inputs'])==60]
 for offset in range(4):
  skip=set(candidates[offset::4]);jobs.append((f'cut-combat-quarter-{offset}',[k for j,v in enumerate(macros) if j not in skip for k in v['inputs']]))
 (OUT/'manifest.json').write_text(json.dumps({'scope':'checkpoint retiming practice; not a cold clear','root':ROOT,'source_plan':PLAN,'jobs':len(jobs)},indent=2));rows=[];started=time.perf_counter()
 with concurrent.futures.ProcessPoolExecutor(max_workers=2,initializer=b.initialize,initargs=(spec,)) as pool:
  for r in pool.map(candidate,jobs,chunksize=1):
   row={k:v for k,v in r.items() if k not in ['state','plan']};rows.append(row);print(json.dumps(row),flush=True)
   if r['valid']:
    (OUT/f"{r['name']}.state").write_bytes(r['state']);(OUT/f"{r['name']}-plan.json").write_text(json.dumps(r['plan']))
   (OUT/'result.json').write_text(json.dumps({'wall':time.perf_counter()-started,'rows':rows},indent=2))
if __name__=='__main__':main()
