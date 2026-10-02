"""Compare fixed native walking routes at an empty-room RAM checkpoint."""
import argparse
import concurrent.futures
import json
from pathlib import Path
from emulator import Emulator
from kovsh import ROM,observe

def trial(job):
    source,out,frame,mode=job
    m=json.loads((source/'manifest.json').read_text());e=Emulator(ROM,core=Path(m['core_path']),deterministic=True,headless=True)
    checkpoint=source/f'frame-{frame:06d}.state' if frame else source/'initial.state'
    e.restore(checkpoint.read_bytes());before=observe(e.ram_view());trace=[];samples=[]
    try:
        for f in range(1600):
            o=observe(e.ram_view());gy=o['ground_y'];keys=['right']
            if mode=='left':keys=['left']
            if mode=='left_up':keys=['left','up']
            if mode=='left_down':keys=['left','down']
            if mode=='return_830_220':keys=(['left'] if o['x']>830 else [])+(['up'] if gy>224 else ['down'] if gy<216 else [])
            if mode.startswith('upper-return-') and mode.split('-')[-1].isdigit():
                lane=int(mode.split('-')[-1]);keys=['left','up'] if gy>lane else ['right']
            if mode=='upper-return-diagonal':keys=['left','up'] if gy>96 else ['right','up']
            if mode=='historic_upper':keys=['right'] if f<60 else ['up'] if f<135 else ['left','up'] if f<195 else ['right']
            if mode=='door_865_136':keys=['left'] if o['x']>875 else ['right'] if o['x']<855 else ['up'] if gy>136 else []
            if mode=='snow_exit_lower':keys=['down'] if gy<450 else ['up'] if gy>454 else ['right']
            if mode=='snow_exit_diagonal':keys=['right']+(['down'] if gy<450 else ['up'] if gy>454 else [])
            if mode.startswith('lane-'):
                lane=int(mode.split('-')[1])
                if abs(gy-lane)>2:keys=['up' if gy>lane else 'down']
            if mode=='right_up':keys+=['up']
            if mode=='right_down':keys+=['down']
            if mode=='up_120_then_right' and gy>120:keys=['up']
            if mode=='down_260_then_right' and gy<260:keys=['down']
            if mode=='left_up_detour':keys=['left'] if f<60 else ['up'] if gy>120 else ['right']
            if mode=='right_attack' and f%4<2:keys+=['attack']
            if mode=='right_jump' and f%60<2:keys+=['jump']
            e.step(keys);after=observe(e.ram_view());trace.append(keys)
            if f%30==29:samples.append(dict(frame=f+1,**after))
            transition=after['chapter']!=before['chapter'] or ((o['x']-after['x']>600 or after['room_raw']!=before['room_raw']) and after['time_remaining']-o['time_remaining']>15)
            if transition or after['hp']==0 or after['lives']<before['lives']:break
        r=dict(mode=mode,frames=f+1,room_exit=transition,before=before,after=after,samples=samples,headless=True)
        p=out/mode;p.mkdir();(p/'result.json').write_text(json.dumps(r,indent=2));(p/'inputs.jsonl').write_text(''.join(json.dumps(dict(frame=i+1,buttons=k))+'\n' for i,k in enumerate(trace)))
        (p/'final.state').write_bytes(e.save());(p/'final.ram').write_bytes(e.ram());return r
    finally:e.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--frame',type=int,default=600);p.add_argument('--lanes',action='store_true');p.add_argument('--narrow-gap',action='store_true');p.add_argument('--return-route',action='store_true');p.add_argument('--upper-return',action='store_true');p.add_argument('--door',action='store_true');p.add_argument('--modes',nargs='+',help='Named native walking mechanisms');a=p.parse_args();a.output.mkdir(exist_ok=False)
    modes=['right','right_up','right_down','up_120_then_right','down_260_then_right','left_up_detour','right_attack','right_jump']
    if a.lanes:modes=[f'lane-{lane}' for lane in (144,152,168,184,200,216,232,248,264,280,296,312)]
    if a.narrow_gap:modes=[f'lane-{lane}' for lane in (202,204,206,208,210,212,214)]
    if a.return_route:modes=['left','left_up','left_down','return_830_220']
    if a.upper_return:modes=['upper-return-88','upper-return-96','upper-return-104','upper-return-112','upper-return-diagonal','historic_upper']
    if a.door:modes=['door_865_136']
    if a.modes:modes=a.modes
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,max_tasks_per_child=1) as pool:results=list(pool.map(trial,[(a.source,a.output,a.frame,mode) for mode in modes]))
    (a.output/'report.json').write_text(json.dumps(results,indent=2))
    for r in results:print(json.dumps({k:r[k] for k in ('mode','frames','room_exit','after')}),flush=True)
