"""Native RAM-only exit-lane comparison after the last enemy disappears."""
import concurrent.futures
import json
from pathlib import Path
from emulator import Emulator
from kovsh import ROM,OUT,observe

def trial(job):
    lane,mode=job if isinstance(job,tuple) else (job,'axis')
    core=Path('arcade/cores/fbneo_pgm_statefix_libretro.dll')
    source=OUT/'bamboo-final-lane-checkpoint'
    out=(OUT/'bamboo-exit-lanes-016'/str(lane)) if mode=='axis' else (OUT/'bamboo-exit-mechanisms-017b'/f'{mode}-{lane}')
    out.mkdir(parents=True,exist_ok=False)
    e=Emulator(ROM,core=core,deterministic=True,headless=True);e.restore((source/'initial.state').read_bytes())
    initial=observe(e.ram_view());inputs=[];samples=[];transition=False;death=False
    for f in range(1600):
        before=observe(e.ram_view())
        if before['ground_y']>lane:keys=['left'] if before['x']>1900 else ['up']
        else:keys=['right'] if before['x']<2004 else []
        if mode!='axis':
            keys=(['right'] if before['x']<2004 else [])+(['up'] if before['ground_y']>lane else [])
            if mode=='jump_diagonal' and f<2:keys+=['jump']
            if mode=='dash_diagonal' and f<8:keys=[] if f<2 or 5<=f<8 else ['right']
            if mode=='cancel_diagonal' and f<2:keys=['attack','jump']
            if mode=='break_diagonal' and f%4<2:keys+=['attack']
        e.step(keys);inputs.append(keys);after=observe(e.ram_view())
        if f%20==19:samples.append(dict(frame=f+1,**after))
        transition=after['chapter']!=before['chapter'] or (before['x']-after['x']>600 and after['time_remaining']-before['time_remaining']>15)
        death=after['hp']==0 or after['lives']<initial['lives']
        if transition or death:break
    result=dict(lane=lane,mode=mode,frames=f+1,initial=initial,after=after,room_exit=transition,death=death,headless=True,video_bytes_allocated=e.video_bytes is not None)
    (out/'result.json').write_text(json.dumps(result,indent=2));(out/'samples.json').write_text(json.dumps(samples))
    (out/'inputs.jsonl').write_text(''.join(json.dumps(dict(frame=i+1,buttons=keys))+'\n' for i,keys in enumerate(inputs)))
    (out/'final.state').write_bytes(e.save());(out/'final.ram').write_bytes(e.ram());e.close();return result

if __name__=='__main__':
    import sys
    jobs=[(lane,mode) for lane in [162,174] for mode in ['diagonal','jump_diagonal','dash_diagonal','cancel_diagonal','break_diagonal']] if '--mechanisms' in sys.argv else [174,162,151,144]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,max_tasks_per_child=1) as pool:
        results=list(pool.map(trial,jobs))
    out=OUT/('bamboo-exit-mechanisms-017b' if '--mechanisms' in sys.argv else 'bamboo-exit-lanes-016')
    (out/'report.json').write_text(json.dumps(results,indent=2))
    for r in results:print(json.dumps(r),flush=True)
