"""Real-input exit comparison from a newer, earlier-cleared checkpoint."""
import concurrent.futures
import json
from pathlib import Path
from emulator import Emulator
from kovsh import ROM,OUT,observe

SOURCE=OUT/'one-life-bamboo-tempo-021'
OUTPUT=OUT/'bamboo-exit-recheck-024'
CORE=Path('arcade/cores/fbneo_pgm_statefix_libretro.dll')

def trial(mode):
    e=Emulator(ROM,core=CORE,deterministic=True,headless=True)
    e.restore((OUTPUT/'initial.state').read_bytes());initial=observe(e.ram_view());trace=[];samples=[]
    try:
        for f in range(1000):
            o=observe(e.ram_view());gy=o['ground_y'];keys=['right']
            if mode=='diagonal_down_174' and gy<174:keys+=['down']
            if mode=='diagonal_down_200' and gy<200:keys+=['down']
            if mode=='diagonal_up_144' and gy>144:keys+=['up']
            if mode=='down_then_right_200' and gy<200:keys=['down']
            if mode=='left_detour_174':
                keys=['left'] if o['x']>1850 and gy<174 else ['down'] if gy<174 else ['right']
            e.step(keys);after=observe(e.ram_view());trace.append(keys)
            if f%30==29:samples.append(dict(frame=f+1,**after))
            transition=after['chapter']!=initial['chapter'] or (o['x']-after['x']>600 and after['time_remaining']-o['time_remaining']>15)
            if transition or after['hp']==0 or after['lives']<initial['lives']:break
        r=dict(mode=mode,frames=f+1,room_exit=transition,before=initial,after=after,samples=samples)
        p=OUTPUT/mode;p.mkdir();(p/'result.json').write_text(json.dumps(r,indent=2));(p/'inputs.jsonl').write_text(''.join(json.dumps(dict(frame=i+1,buttons=k))+'\n' for i,k in enumerate(trace)))
        (p/'final.state').write_bytes(e.save());return r
    finally:e.close()

if __name__=='__main__':
    OUTPUT.mkdir(exist_ok=False)
    e=Emulator(ROM,core=CORE,deterministic=True,headless=True);e.restore((SOURCE/'frame-006000.state').read_bytes())
    inputs=[json.loads(x)['buttons'] for x in (SOURCE/'inputs.jsonl').read_text().splitlines()]
    for k in inputs[6000:6496]:e.step(k)
    (OUTPUT/'initial.state').write_bytes(e.save());(OUTPUT/'initial.ram').write_bytes(e.ram());e.close()
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,max_tasks_per_child=1) as pool:results=list(pool.map(trial,['right_continuous','diagonal_down_174','diagonal_down_200','diagonal_up_144','down_then_right_200','left_detour_174']))
    (OUTPUT/'report.json').write_text(json.dumps(results,indent=2))
    for r in results:print(json.dumps({k:r[k] for k in ('mode','frames','room_exit','after')}),flush=True)
