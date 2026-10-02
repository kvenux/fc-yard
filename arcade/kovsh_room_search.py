"""Headless beam search over named, RAM-driven battle and navigation mechanisms."""
import argparse
import hashlib
import json
import multiprocessing
import os
import time
from pathlib import Path
from emulator import Emulator
from kovsh import CORE, ROM, OUT, observe, evaluate_candidate, sha, plan_choices

engine=None
def initialize():
    global engine
    from multiprocessing.util import Finalize
    engine=Emulator(ROM,core=Path(os.environ['KOVSH_CORE']),deterministic=True,headless=True)
    Finalize(None,engine.close,exitpriority=10)

def expand(job):
    state,before,frame,config,choice,parent=job
    _,inputs=evaluate_candidate(engine,state,before,frame,config,choice)
    after=observe(engine.ram_view())
    if after['hp']<=0 or after['lives']<before['lives']:return None
    transition=after['chapter']!=before['chapter'] or (before['x']-after['x']>600 and after['time_remaining']-before['time_remaining']>15)
    origin=config['origin']
    cleared_front=min([after['x']]+[e['x'] for e in after['enemies']])
    value=(after['score']-origin['score'])*.2+(after['hp']-origin['hp'])*40
    value+=(cleared_front-origin['x'])*3
    if not config.get('spawn_progress'):
        value-=sum(e['hp'] for e in after['enemies'])*35
    else:
        # A newly spawned wave is required progress. Penalizing all its HP
        # made an empty corridor score better than entering the next encounter.
        value-=sum(e['hp'] for e in after['enemies'])*2
    if transition:value+=100000
    return dict(state=engine.save(),after=after,inputs=inputs,parent=parent,value=value,
                transition=transition,tactic=choice.get('tactic','route'))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--core',type=Path,default=CORE);p.add_argument('--state',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--workers',type=int,default=4)
    p.add_argument('--width',type=int,default=12);p.add_argument('--step',type=int,default=180)
    p.add_argument('--depth',type=int,default=20)
    p.add_argument('--combat-rules',action='store_true')
    p.add_argument('--spawn-progress',action='store_true')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    os.environ['KOVSH_CORE']=str(a.core.resolve());state=a.state.read_bytes()
    e=Emulator(ROM,core=a.core,deterministic=True,headless=True);e.restore(state)
    initial=observe(e.ram_view());e.close()
    c=dict(period=4,distance=32,align=8,jump=0,face_period=60,facing_feedback=True,
           ground_alignment=True,horizon=a.step,commit=a.step,hp_weight=60,fast_preview=True,
           ram_navigation=True,bamboo_gate=True,gate_attack_stuck_only=True,bamboo_exit_lane=True,origin=initial)
    c['spawn_progress']=a.spawn_progress
    choices=[{**c,'tactic':'pressure','special':None},
             {**c,'tactic':'finish_weak','special':None,'finish_weak':True},
             {**c,'tactic':'quarter_circle_sweep','special':'qcf','special_period':36},
             {**c,'tactic':'low_sweep','special':'dd','special_period':36},
             {**c,'tactic':'vertical_sweep','special':'du','special_period':36},
             {**c,'tactic':'cluster_sweep','special':'qcf','special_period':36,'focus_cluster':True},
             {**c,'tactic':'forward_pressure','special':None,'focus_forward':True},
             {**c,'tactic':'fast_chase','special':None,'attack_in_range':True},
             {**c,'tactic':'fast_qcf_chase','special':'qcf','special_period':36,'attack_in_range':True,'special_in_range':True},
             {**c,'tactic':'fast_low_sweep_chase','special':'dd','special_period':36,'attack_in_range':True,'special_in_range':True},
             {**c,'tactic':'clear_rear_straggler','special':None,'attack_in_range':True,'focus_rear':True},
             {'tactic':'escape_upper_lane','hop':'up'},{'tactic':'escape_lower_lane','hop':'down'},
             {'tactic':'hold_combo','flurry':4}]
    if a.combat_rules:
        from kovsh_combat import MODES
        choices += [{'tactic':mode,'combat_rule':mode} for mode in MODES if mode!='hold_attack']
    manifest=dict(scope='checkpoint_room_search',core_path=str(a.core.resolve()),core_sha256=sha(a.core),
                  rom_sha256=sha(ROM),state_sha256=sha(a.state),source_sha256=sha(__file__),
                  policy_sha256=sha(Path(__file__).with_name('kovsh.py')),headless=True,
                  initial=initial,full_game_clear_verified=False,width=a.width,step=a.step,
                  strategies=[ch['tactic'] for ch in choices],spawn_progress=a.spawn_progress)
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (a.output/'source.py').write_bytes(Path(__file__).read_bytes())
    (a.output/'policy.py').write_bytes(Path(__file__).with_name('kovsh.py').read_bytes())
    (a.output/'initial.state').write_bytes(state)
    (OUT/'active-search.json').write_text(json.dumps({'directory':str(a.output.resolve())}))
    beam=[dict(state=state,after=initial,path=[],tactics=[])];history=[];rollouts=0;start=time.perf_counter()
    with multiprocessing.Pool(a.workers,initializer=initialize) as pool:
        for depth in range(a.depth):
            jobs=[(b['state'],b['after'],len(b['path']),c,ch,i) for i,b in enumerate(beam) for ch in choices]
            candidates=[r for r in pool.map(expand,jobs,chunksize=1) if r is not None];rollouts+=len(jobs)
            for r in candidates:
                previous=beam[r['parent']];r['path']=previous['path']+r['inputs']
                r['tactics']=previous['tactics']+[r['tactic']]
            candidates.sort(key=lambda r:r['value'],reverse=True);selected=[];seen=set()
            for r in candidates:
                o=r['after'];signature=(o['x']//24,o['ground_y']//8,o['hp']//4,o['time_remaining'],
                                        tuple((e['slot'],e['hp']//4,e['x']//24,e['ground_y']//8) for e in o['enemies']))
                if signature in seen:continue
                seen.add(signature);selected.append(r)
                if len(selected)>=a.width:break
            if not selected:
                history.append(dict(depth=depth+1,rollouts=rollouts,reason='no_surviving_branch'));break
            best=selected[0];wins=[r for r in candidates if r['transition']]
            if wins:best=max(wins,key=lambda r:(r['after']['hp'],-len(r['path'])))
            status=dict(depth=depth+1,rollouts=rollouts,frames=len(best['path']),hp=best['after']['hp'],
                        boss_hp=sum(e['hp'] for e in best['after']['enemies']),x=best['after']['x'],
                        time_remaining=best['after']['time_remaining'],score=best['after']['score'],
                        objective=best['value'],seconds=time.perf_counter()-start,room_exit_candidate=bool(wins),
                        native_simulated_frames=rollouts*a.step,full_game_clear_verified=False)
            history.append(status);(a.output/'status.json').write_text(json.dumps(status,indent=2))
            print(json.dumps(status),flush=True)
            (a.output/'inputs.jsonl').write_text(''.join(json.dumps(dict(frame=i+1,buttons=keys))+'\n' for i,keys in enumerate(best['path'])))
            (a.output/'final.state').write_bytes(best['state'])
            (a.output/'result.json').write_text(json.dumps({**status,'before':initial,'after':best['after'],'tactics':best['tactics']},indent=2))
            if wins:break
            beam=selected
    (a.output/'history.json').write_text(json.dumps(history,indent=2))
    # A separate fresh process replays the actual inputs with no branch restores.
    import subprocess
    subprocess.run([os.sys.executable,__file__,'--verify',str(a.output)],check=True)

def verify(folder):
    m=json.loads((folder/'manifest.json').read_text());e=Emulator(ROM,core=Path(m['core_path']),deterministic=True,headless=True)
    assert sha(e.core_path)==m['core_sha256'] and sha(ROM)==m['rom_sha256']
    e.restore((folder/'initial.state').read_bytes());deaths=[];coins=0
    for i,line in enumerate((folder/'inputs.jsonl').read_text().splitlines(),1):
        keys=json.loads(line)['buttons'];coins+=int('coin' in keys);e.step(keys);o=observe(e.ram_view())
        if o['hp']==0 or o['lives']<m['initial']['lives']:deaths.append(i)
    equal=e.save()==(folder/'final.state').read_bytes()
    report=dict(state_equal=equal,after=o,deaths=deaths,extra_coin_frames=coins,
                headless=True,video_bytes_allocated=e.video_bytes is not None,full_game_clear_verified=False)
    (folder/'replay-audit.json').write_text(json.dumps(report,indent=2));e.close()
    assert equal and not deaths and not coins,'Native search path failed independent replay'

if __name__=='__main__':
    import sys
    if len(sys.argv)==3 and sys.argv[1]=='--verify':verify(Path(sys.argv[2]))
    else:main()
