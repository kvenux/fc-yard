"""Native boss damage comparison, fixed commands at one observed checkpoint."""
import concurrent.futures
import json
from pathlib import Path
from emulator import Emulator
from kovsh import OUT,ROM,observe,evaluate_candidate

SOURCE=OUT/'one-life-chapter4-final-040'
OUTPUT=OUT/'chapter4-boss-commands-042'

def trial(name):
    m=json.loads((SOURCE/'manifest.json').read_text());state=(SOURCE/'frame-005400.state').read_bytes()
    e=Emulator(ROM,core=Path(m['core_path']),deterministic=True,headless=True);e.restore(state);before=observe(e.ram_view())
    boss=max(before['enemies'],key=lambda x:x['hp'])
    c=dict(m['config'],horizon=600,commit=600,focus_large=True,focus_slots=[boss['slot']],target_slot=boss['slot'],boss_damage_multiplier=3)
    choices={mode:dict(c,special=mode,special_period=36) for mode in ('qcf','dd','du','bf','ud','dash')}
    choices.update(normal=dict(c,special=None),buffered_combo=dict(flurry=4,chain=True))
    try:
        value,keys=evaluate_candidate(e,state,before,5400,c,choices[name]);after=observe(e.ram_view())
        hp=int.from_bytes(e.ram_view()[0xcf18+boss['slot']*0x1a6+100:0xcf18+boss['slot']*0x1a6+102],'little')
        r=dict(name=name,boss_slot=boss['slot'],boss_damage=boss['hp']-hp,hp_delta=after['hp']-before['hp'],before=before,after=after,value=value,frames=len(keys),headless=True)
        p=OUTPUT/name;p.mkdir();(p/'result.json').write_text(json.dumps(r,indent=2));(p/'inputs.jsonl').write_text(''.join(json.dumps(dict(frame=i+1,buttons=k))+'\n' for i,k in enumerate(keys)))
        (p/'final.state').write_bytes(e.save());return r
    finally:e.close()

if __name__=='__main__':
    OUTPUT.mkdir(exist_ok=False)
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,max_tasks_per_child=1) as pool:results=list(pool.map(trial,['normal','qcf','dd','du','bf','ud','dash','buffered_combo']))
    (OUTPUT/'report.json').write_text(json.dumps(results,indent=2))
    for r in results:print(json.dumps({k:r[k] for k in ('name','boss_damage','hp_delta','frames')}),flush=True)
