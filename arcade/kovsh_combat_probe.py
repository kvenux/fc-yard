"""Fixed mechanism comparison at identical native checkpoints, no pixels."""
import argparse
import concurrent.futures
import json
from pathlib import Path
import time
from emulator import Emulator
from kovsh import ROM, observe, evaluate_candidate
from kovsh_combat import MODES

def trial(job):
    source,out,frame,mode=job
    m=json.loads((source/'manifest.json').read_text());c=dict(m['config'],horizon=360,commit=360)
    state=(source/f'frame-{frame:06d}.state').read_bytes()
    choice=dict(c,tactic='pressure',special=None) if mode=='baseline_pressure' else dict(combat_rule=mode)
    e=Emulator(ROM,core=Path(m['core_path']),deterministic=True,headless=True)
    e.restore(state);before=observe(e.ram_view());start=time.perf_counter()
    try:
        value,seq=evaluate_candidate(e,state,before,frame,c,choice)
        after=observe(e.ram_view())
        r=dict(checkpoint=frame,mode=mode,frames=e.frame,seconds=time.perf_counter()-start,before=before,after=after,value=value,
               score_gain=after['score']-before['score'],hp_loss=before['hp']-after['hp'],headless=True)
        (out/f'{frame}-{mode}.json').write_text(json.dumps(r,indent=2));return r
    finally:e.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(exist_ok=False,parents=True);start=time.perf_counter()
    jobs=[(a.source,a.output,f,mode) for f in (600,1200,1800,2400,3600,6000) for mode in ('baseline_pressure',)+MODES]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,max_tasks_per_child=1) as pool:results=list(pool.map(trial,jobs))
    report=dict(seconds=time.perf_counter()-start,native_frames=sum(r['frames'] for r in results),results=results)
    (a.output/'report.json').write_text(json.dumps(report,indent=2))
    for r in results:print(json.dumps({k:r[k] for k in ('checkpoint','mode','score_gain','hp_loss','value')}),flush=True)
