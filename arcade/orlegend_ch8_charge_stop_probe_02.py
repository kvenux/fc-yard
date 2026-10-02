import sys,json,copy
from pathlib import Path
sys.path.insert(0,'arcade')
import orlegend_beam_parallel as b
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-charge-stop-probe-02');out.mkdir(exist_ok=False);base=json.loads(Path('arcade/orlegend-bt-ch8-search-policy-12.json').read_text());b.initialize(base);rows=[]
for root in ['arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-10/checkpoints/depth-038.state','arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-14/checkpoints/depth-074.state']:
 raw=Path(root).read_bytes();b.worker.restore(raw);o=observation(b.worker)
 for flag in [False,True]:
  b.worker_policy=copy.deepcopy(base);b.worker_policy['parameters']['search_charge_stop_at_full']=flag
  r=b.rollout((raw,o,0,0,0,'charge',120,8,2,[1795],[(1795,0)]));row={k:v for k,v in r.items() if k not in ['state','inputs']};row.update(root=root,stop_at_full=flag);rows.append(row);print(json.dumps(row),flush=True)
(out/'result.json').write_text(json.dumps(rows,indent=2));b.worker.close()
