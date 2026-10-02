"""Identical cold inputs: compare game RAM and serialized state with/without AV."""
import argparse, hashlib, json, subprocess, sys, time
from pathlib import Path
from emulator import Emulator
from orlegend import ROM, OUT, observe

def worker(mode, frames, out):
    rows=[json.loads(x)['buttons'] for x in (OUT/'full-policy-cold-05/inputs.jsonl').read_text().splitlines()[:frames]]
    e=Emulator(ROM, deterministic=True, headless=mode!='render')
    if mode=='noav':e.av_enable=0
    checks=[];started=time.perf_counter()
    try:
        for i,keys in enumerate(rows):
            e.step(keys)
            if (i+1)%1000==0:
                checks.append({'frame':i+1,'ram':hashlib.sha256(e.ram_view()).hexdigest(),'observation':observe(e.ram_view())})
        seconds=time.perf_counter()-started
        result={'mode':mode,'frames':len(rows),'seconds':seconds,'fps':len(rows)/seconds,'realtime_multiplier':len(rows)/seconds/e.fps,'video_callbacks':e.video_callbacks,'pixels_copied':e.video_bytes is not None,'checks':checks,'fingerprint':e.fingerprint()}
        out.write_text(json.dumps(result,indent=2))
    finally:e.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['render','headless','noav']);p.add_argument('--frames',type=int,default=24000);p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output)
    if a.mode:worker(a.mode,a.frames,out)
    else:
        out.mkdir(parents=True,exist_ok=False);results=[]
        for mode in ['render','headless','noav']:
            path=out/(mode+'.json')
            subprocess.run([sys.executable,__file__,'--mode',mode,'--frames',str(a.frames),'--output',str(path)],check=True)
            results.append(json.loads(path.read_text()))
        reference_checks=results[0]['checks'];reference_state=results[0]['fingerprint']['state']
        for r in results:
            r['ram_checkpoints_equal_render']=r['checks']==reference_checks;r['serialized_state_equal_render']=r['fingerprint']['state']==reference_state;r.pop('checks')
        (out/'summary.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
