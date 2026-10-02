"""Beam search over native input rollouts for a short boss finishing window."""
import argparse
import json
import multiprocessing
import os
import time
from pathlib import Path
from emulator import Emulator
from kovsh import ROM, CORE, observe, evaluate_candidate, sha

core=None

def init():
    global core
    core=Emulator(ROM,core=Path(os.environ.get('KOVSH_CORE',CORE)),deterministic=True,headless=True)

def expand(job):
    state,o,f,c,choice,parent,slot=job
    _,seq=evaluate_candidate(core,state,o,f,c,choice)
    end=observe(core.ram())
    if end['hp']<=0 or end['lives']<o['lives']:return None
    b=next((x for x in end['enemies'] if x['slot']==slot),None)
    raw=int.from_bytes(core.ram()[0xcf18+slot*0x1a6+100:0xcf18+slot*0x1a6+102],'little')
    boss_hp=b['hp'] if b else raw
    score=-boss_hp*100+end['hp']*c.get('survival_weight',12)
    if c.get('clear_room'):score-=sum(x['hp'] for x in end['enemies'] if x['slot']!=slot)*20
    if b:score-=.1*(abs(b['x']-end['x'])+3*abs(b['ground_y']-end['ground_y']))
    return dict(state=core.save(),observation=end,parent=parent,seq=seq,score=score,
                boss_hp=boss_hp,win=boss_hp==0 and (not c.get('clear_room') or not end['enemies']))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--slot',type=int,default=1)
    p.add_argument('--core',type=Path,default=CORE)
    p.add_argument('--width',type=int,default=12);p.add_argument('--step',type=int,default=90)
    p.add_argument('--depth',type=int,default=12);p.add_argument('--workers',type=int,default=4)
    p.add_argument('--hp-weight',type=float,default=50)
    p.add_argument('--clear-room',action='store_true')
    a=p.parse_args();os.environ['KOVSH_CORE']=str(a.core.resolve());a.output.mkdir(parents=True,exist_ok=False);state=a.state.read_bytes()
    # Read initial RAM in a short-lived process-independent frontend, then close it.
    e=Emulator(ROM,core=a.core,deterministic=True,headless=True);e.restore(state);o=observe(e.ram());e.close()
    c=dict(period=4,distance=32,align=8,jump=0,horizon=a.step,commit=a.step,hp_weight=50,
           fast_preview=True,ground_alignment=True,target_slot=a.slot,boss_damage_multiplier=3,survival_weight=a.hp_weight,clear_room=a.clear_room)
    choices=[{**c,'distance':d,'special':s,'special_period':36} for d in (16,32,56) for s in (None,'bf','dd','ud','du','dash')]
    choices += [{'fixed':k} for k in ([],['up'],['down'],['left'],['right'],['jump'],['attack','jump'],['d'])]
    choices += [{'flurry':8,'chain':True},{'hop':'up'},{'hop':'down'}]
    beam=[dict(state=state,observation=o,path=[])];history=[];start=time.perf_counter();rollouts=0
    (a.output/'manifest.json').write_text(json.dumps(dict(scope='checkpoint_finishing_search',state_sha256=sha(a.state),core_path=str(a.core.resolve()),core_sha256=sha(a.core),source_sha256=sha(__file__),headless=True,full_game_clear_verified=False),indent=2))
    (a.output/'initial.state').write_bytes(state)
    (a.output.parent/'active-search.json').write_text(json.dumps({'directory':str(a.output.resolve())}))
    with multiprocessing.Pool(a.workers,initializer=init) as pool:
        for depth in range(a.depth):
            jobs=[(b['state'],b['observation'],depth*a.step,c,ch,i,a.slot) for i,b in enumerate(beam) for ch in choices]
            results=[x for x in pool.map(expand,jobs,chunksize=1) if x is not None];rollouts+=len(jobs)
            for r in results:r['path']=beam[r['parent']]['path']+r['seq']
            results.sort(key=lambda r:r['score'],reverse=True)
            seen=set();next_beam=[]
            for r in results:
                o=r['observation'];key=(r['boss_hp']//4,o['hp']//4,o['x']//24,o['ground_y']//8)
                if key in seen:continue
                seen.add(key);next_beam.append(r)
                if len(next_beam)>=a.width:break
            if not next_beam:break
            best=next_beam[0];status=dict(depth=depth+1,rollouts=rollouts,frames=(depth+1)*a.step,
                boss_hp=best['boss_hp'],hp=best['observation']['hp'],seconds=time.perf_counter()-start)
            history.append(status);(a.output/'status.json').write_text(json.dumps(status,indent=2));print(json.dumps(status),flush=True)
            winners=[r for r in results if r['win']]
            if winners:
                best=max(winners,key=lambda r:r['observation']['hp']);status['boss_defeated_candidate']=True
                (a.output/'inputs.jsonl').write_text(''.join(json.dumps({'frame':i+1,'buttons':k})+'\n' for i,k in enumerate(best['path'])))
                (a.output/'final.state').write_bytes(best['state'])
                (a.output/'result.json').write_text(json.dumps({**status,'after':best['observation'],'full_game_clear_verified':False},indent=2));break
            beam=next_beam
            import pickle
            (a.output/'beam-checkpoint.pkl').write_bytes(pickle.dumps({'beam':beam,'next_depth':depth+1}))
    (a.output/'history.json').write_text(json.dumps(history,indent=2))

if __name__=='__main__':main()
