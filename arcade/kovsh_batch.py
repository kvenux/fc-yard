"""Fast headless checkpoint curriculum: parallel real-input policy trials.

No coin, continue, RAM writes, or within-episode restore. These are local
training episodes, not independent full-game clears. Render winners later.
"""
import argparse
import concurrent.futures
import itertools
import json
import os
import time
from pathlib import Path
from emulator import Emulator
from kovsh import ROM, CORE, observe, action, sha, Navigator


def forecast_worker(connection):
    from kovsh import evaluate_candidate
    e=Emulator(ROM,core=CORE,deterministic=True,headless=True)
    try:
        while True:
            request=connection.recv()
            if request is None:break
            state,o,f,c=request
            choices=[{**c,'distance':d,'special':s,'special_period':36}
                     for d,s in ((24,None),(48,None),(32,'du'),(48,'du'),(32,'qcf'),(48,'dash'),(40,'ud'))]
            choices += [{'hop':'up'},{'hop':'down'},{'fixed':['left']},{'fixed':['right']},{'use_after':16}]
            if c.get('expanded_techniques'):
                choices += [{**c,'distance':d,'special':s,'special_period':36,'face_period':60}
                            for d in (24,48) for s in ('bf','dd','ud')]
                choices += [{'fixed':['attack','jump','c']}]
            if c.get('combos'):
                choices += [{'flurry':p,'chain':chain} for p in (4,8,12) for chain in (False,True)]
            if c.get('behavior_forest'):
                from kovsh_behavior import STRATEGIES
                choices=[{'behavior_tree':name,'boss_slot':c['target_slot']} for name in STRATEGIES]
            results=[evaluate_candidate(e,state,o,f,c,x) for x in choices]
            index=max(range(len(results)),key=lambda i:results[i][0])
            if c.get('behavior_forest'):
                connection.send({'inputs':results[index][1], 'strategy':choices[index]['behavior_tree'],
                                 'predicted_value':results[index][0]})
            else:connection.send(results[index][1])
    finally:e.close();connection.close()


def trial(job):
    initial, output, number, config, limit, boss_slot = job
    folder=Path(output)/f'trial-{number:04d}'
    folder.mkdir()
    e=Emulator(ROM,core=CORE,deterministic=True,headless=True)
    e.restore(Path(initial).read_bytes())
    before=observe(e.ram());o=before;trace=[];samples=[];start=time.perf_counter()
    tree=None
    if config.get('behavior_tree'):
        from kovsh_behavior import BehaviorTree
        tree=BehaviorTree(config['behavior_tree'],None if config.get('room_exit') else boss_slot)
    boss_start=next(x['hp'] for x in before['enemies'] if x['slot']==boss_slot)
    boss_min=boss_start;cleared=False;events=[];last_d=-1000;previous=before;total_damage=0;room_transitions=[]
    worker=None;connection=None;pending=[];navigator=Navigator(config)
    if config.get('lookahead'):
        import multiprocessing
        connection,child=multiprocessing.Pipe()
        worker=multiprocessing.Process(target=forecast_worker,args=(child,))
        worker.start();child.close()
    try:
        for f in range(limit):
            if f%4==0:o=observe(e.ram_view())
            control=o
            if config.get('boss_focus'):
                target=[x for x in o['enemies'] if x['slot']==boss_slot]
                if target:control={**o,'enemies':target}
            keys=tree.tick(observe(e.ram_view()),f) if tree else action(control,f,config)
            if config.get('ram_navigation') and not o['enemies']:
                nav=navigator.choose(o,f,None)
                if nav is not None:keys=[k for k in nav if k!='attack' or f%4<2]
            if worker:
                if not pending:
                    o=observe(e.ram());connection.send((e.save(),o,f,config))
                    if not connection.poll(90):raise RuntimeError('Forecast timed out')
                    response=connection.recv()
                    if isinstance(response,dict):
                        pending=response['inputs']
                        events.append({'frame':f,'strategy':response['strategy'],'predicted_value':response['predicted_value']})
                    else:pending=response
                keys=pending.pop(0)
            dodge=config.get('dodge',0)
            if dodge and o['enemies']:
                near=min(o['enemies'],key=lambda x:abs(x['x']-o['x'])+3*abs(x['y']-o['y']))
                if abs(near['x']-o['x'])<60 and abs(near['y']-o['y'])<12 and f%120<dodge:
                    keys=['up' if o['y']>220 else 'down']
            # D uses the currently selected item; inventory deltas are audited.
            if config.get('use_item') and not worker and f%360 in (200,201,202,203):keys=['d']
            if 'd' in keys:last_d=f
            e.step(keys);trace.append(keys)
            if f%4==3:
                after=observe(e.ram_view())
                current={x['slot']:x['hp'] for x in after['enemies']}
                total_damage+=sum(max(0,x['hp']-current.get(x['slot'],0)) for x in previous['enemies'])
                room_changed=after['chapter']!=previous['chapter'] or (previous['x']-after['x']>600 and after['time_remaining']-previous['time_remaining']>15)
                if room_changed:room_transitions.append({'frame':f+1,'before':previous,'after':after})
                previous=after
                for item,n in o['inventory'].items():
                    if after['inventory'].get(item,0)<n and f-last_d<120:
                        events.append({'frame':f+1,'item':item,'before':n,'after':after['inventory'].get(item,0)})
                boss=next((x for x in after['enemies'] if x['slot']==boss_slot),None)
                raw_boss_hp=int.from_bytes(e.ram()[0xcf18+boss_slot*0x1a6+100:0xcf18+boss_slot*0x1a6+102],'little')
                boss_min=min(boss_min,boss['hp'] if boss else raw_boss_hp)
                room_complete=not after['enemies'] if tree or config.get('behavior_forest') else True
                goal=room_changed if config.get('room_exit') else not boss and raw_boss_hp==0 and room_complete
                if goal and after['lives']==before['lives'] and after['hp']>0:
                    cleared=True;break
                if after['lives']<before['lives'] or after['hp']==0:break
            if f%120==119:samples.append({'frame':f+1,**observe(e.ram())})
            if f%600==599:
                (folder/'progress.json').write_text(json.dumps({'frame':f+1,'observation':observe(e.ram()),'boss_min_hp':boss_min}))
                if worker or tree:
                    (folder/f'frame-{f+1:06d}.state').write_bytes(e.save())
                    (folder/f'frame-{f+1:06d}.ram').write_bytes(e.ram())
                if (Path(output)/'stop.json').exists():break
        after=observe(e.ram());seconds=time.perf_counter()-start
        fitness=(100000 if cleared else 0)+(boss_start-boss_min)*100+after['hp']*10-len(trace)*.01
        if config.get('room_exit'):
            fitness=(100000 if cleared else 0)+total_damage*10+after['hp']*100-len(trace)
        result={'trial':number,'config':config,'frames':len(trace),'seconds':seconds,
                'simulated_fps':len(trace)/seconds,'before':before,'after':after,
                'boss_start_hp':boss_start,'boss_min_hp':boss_min,'boss_defeated_candidate':cleared,
                'fitness':fitness,'scope':'checkpoint_practice','full_game_clear_verified':False,
                'rendered_replay_verified':False,'item_events':events}
        result.update(room_exit_candidate=cleared if config.get('room_exit') else False,
                      enemy_damage=total_damage,room_transitions=room_transitions,
                      video_frames_copied=0,headless=True)
        if tree:
            from collections import Counter
            result['behavior_branch_visits']=dict(Counter(x['branch'] for x in tree.events if 'branch' in x))
            result['room_clear_candidate']=cleared
            result['item_events'] += [x for x in tree.events if 'item_consumed' in x]
            (folder/'behavior-events.json').write_text(json.dumps(tree.events,indent=2))
        (folder/'inputs.jsonl').write_text(''.join(json.dumps({'frame':i+1,'buttons':k})+'\n' for i,k in enumerate(trace)))
        (folder/'final.state').write_bytes(e.save());(folder/'final.ram').write_bytes(e.ram())
        (folder/'samples.json').write_text(json.dumps(samples))
        (folder/'result.json').write_text(json.dumps(result,indent=2))
        return result
    finally:
        e.close()
        if worker:
            connection.send(None);worker.join(10)
            if worker.is_alive():worker.terminate();worker.join()
            connection.close()


def plot(out,results):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    ordered=results
    plt.rcParams['font.sans-serif']=['Microsoft YaHei','DejaVu Sans']
    fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True,layout='constrained')
    x=list(range(1,len(ordered)+1));fitness=[r['fitness'] for r in ordered]
    axes[0].plot(x,fitness,'.',label='本次评估')
    axes[0].plot(x,list(itertools.accumulate(fitness,max)),label='历史最佳');axes[0].legend()
    axes[0].set(title='风云再起 · 无画面并行策略评估（同一首领节点）',ylabel='训练目标得分')
    axes[1].plot(x,[r['boss_start_hp']-r['boss_min_hp'] for r in ordered],'.-')
    axes[1].set(ylabel='首领血量削减')
    axes[2].plot(x,[r['after']['hp'] for r in ordered],'.-',label='结束血量')
    axes[2].set(xlabel='已完成评估数（按完成顺序，非整局通关次数）',ylabel='己方血量')
    for ax in axes:ax.grid(alpha=.2)
    fig.savefig(out/'training-curve.png',dpi=140);plt.close(fig)


def main():
    global CORE
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--core',type=Path,default=CORE)
    p.add_argument('--workers',type=int,default=4);p.add_argument('--trials',type=int,default=48)
    p.add_argument('--frames',type=int,default=10000);p.add_argument('--boss-slot',type=int,required=True)
    p.add_argument('--lookahead',action='store_true')
    p.add_argument('--boss-priority',action='store_true')
    p.add_argument('--techniques',action='store_true')
    p.add_argument('--reactive-techniques',action='store_true')
    p.add_argument('--ground-alignment',action='store_true')
    p.add_argument('--committed',action='store_true')
    p.add_argument('--randomize',action='store_true')
    p.add_argument('--combos',action='store_true')
    p.add_argument('--behavior-trees',action='store_true',help='Evaluate eight named deterministic behavior trees')
    p.add_argument('--behavior-forest',action='store_true',help='Select among complete behavior trees by native lookahead')
    p.add_argument('--room-exit',action='store_true',help='Evaluate room advancement, including timer-reset exits')
    p.add_argument('--mechanisms',action='store_true',help='Compare named attack/chase mechanisms without parameter randomization')
    a=p.parse_args();CORE=a.core.resolve();os.environ['KOVSH_CORE']=str(CORE)
    a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'initial.state').write_bytes(a.state.read_bytes())
    configs=[]
    for distance,special,period in itertools.product((24,40,56,72),(None,'du','qcf','dash'),(4,8,12)):
        n=len(configs)
        configs.append(dict(period=period,distance=distance,align=8,jump=36 if n%7==0 else 0,
                            special=special,special_period=36,face_period=60 if n%2 else period,
                            boss_focus=n%3==0,dodge=24 if n%4==0 else 0,use_item=True))
    if a.lookahead:
        configs=[dict(period=4,distance=32,align=8,jump=0,lookahead=True,fast_preview=True,
                      horizon=h,commit=commit,hp_weight=hp,boss_focus=False,dodge=0,use_item=True)
                 for h,commit,hp in itertools.product((90,180),(60,90),(30,100))]
    if a.boss_priority:
        configs=[dict(period=4,distance=32,align=8,jump=0,lookahead=True,fast_preview=True,
                      horizon=h,commit=60,hp_weight=hp,boss_focus=False,dodge=0,use_item=True,
                      focus_large=focus,focus_slots=[a.boss_slot],target_slot=a.boss_slot,boss_damage_multiplier=3)
                 for h,hp,focus in itertools.product((180,360),(30,100),(False,True))]
    if a.techniques:
        configs=[dict(period=4,distance=32,align=8,jump=0,lookahead=True,fast_preview=True,
                      horizon=h,commit=commit,hp_weight=hp,boss_focus=False,dodge=0,use_item=True,
                      target_slot=a.boss_slot,boss_damage_multiplier=3,expanded_techniques=True)
                 for h,commit,hp in itertools.product((180,300),(30,60),(40,100))]
    if a.reactive_techniques:
        configs=[dict(period=period,distance=distance,align=6,jump=0,special=special,
                      special_period=36,face_period=60,boss_focus=False,dodge=0,use_item=True)
                 for distance,special,period in itertools.product((16,32,48,64),('bf','dd','ud'),(4,8,12,16))]
    if a.committed:
        configs=[dict(period=4,distance=32,align=8,jump=0,lookahead=True,fast_preview=True,
                      horizon=h,commit=h,hp_weight=hp,boss_focus=False,dodge=0,use_item=True,
                      target_slot=a.boss_slot,boss_damage_multiplier=3,expanded_techniques=True,ground_alignment=True)
                 for h,hp in itertools.product((90,120,180,240),(20,100))]
    if a.randomize:
        import random
        rng=random.Random(104)
        configs=[dict(period=rng.choice((4,6,8,12,16)),distance=rng.choice((8,16,24,40,56,72)),
                      align=rng.choice((4,8,12,20)),jump=rng.choice((0,24,36,48,60)),
                      special=rng.choice((None,'bf','dd','ud','dash','du','qcf')),
                      special_period=rng.choice((18,24,36,48,60)),face_period=rng.choice((4,30,60)),
                      boss_focus=rng.choice((False,True)),dodge=rng.choice((0,12,24,36)),
                      use_item=True,ground_alignment=True) for _ in range(a.trials)]
    if a.ground_alignment:
        configs=[{**c,'ground_alignment':True} for c in configs]
    if a.combos:
        configs=[dict(period=4,distance=32,align=8,jump=0,lookahead=True,fast_preview=True,
                      horizon=h,commit=30,hp_weight=hp,boss_focus=False,dodge=0,use_item=True,
                      target_slot=a.boss_slot,boss_damage_multiplier=3,expanded_techniques=True,
                      ground_alignment=True,combos=True)
                 for h,hp in itertools.product((180,240,300,360),(30,100))]
    if a.behavior_trees:
        from kovsh_behavior import configurations
        configs=configurations(a.boss_slot)
    if a.behavior_forest:
        configs=[dict(period=4,distance=30,align=7,jump=0,lookahead=True,fast_preview=True,
                      horizon=240,commit=120,hp_weight=100,boss_damage_multiplier=3,
                      target_slot=a.boss_slot,behavior_forest=True,ground_alignment=True)]
    if a.mechanisms:
        base=dict(period=4,distance=32,align=8,jump=0,face_period=60,ground_alignment=True,
                  facing_feedback=True,ram_navigation=True,bamboo_gate=True,gate_attack_stuck_only=True,
                  use_item=True,special_period=36)
        configs=[{**base,'strategy_label':'calibrated_normal','special':None},
                 {**base,'strategy_label':'fast_chase_normal','special':None,'attack_in_range':True},
                 {**base,'strategy_label':'fast_chase_qcf','special':'qcf','attack_in_range':True,'special_in_range':True},
                 {**base,'strategy_label':'fast_chase_low_sweep','special':'dd','attack_in_range':True,'special_in_range':True},
                 {**base,'strategy_label':'fast_chase_vertical_sweep','special':'du','attack_in_range':True,'special_in_range':True},
                 {**base,'strategy_label':'fast_chase_dash','special':'dash','attack_in_range':True,'special_in_range':True},
                 {**base,'strategy_label':'finish_weak_then_chase','special':None,'attack_in_range':True,'finish_weak':True},
                 {**base,'strategy_label':'cluster_then_sweep','special':'qcf','attack_in_range':True,'special_in_range':True,'focus_cluster':True}]
    if a.room_exit:configs=[{**c,'room_exit':True} for c in configs]
    manifest={'scope':'checkpoint_practice','state_sha256':sha(a.state),'source_sha256':sha(__file__),
              'rom_sha256':sha(ROM),'core_path':str(CORE),'core_sha256':sha(CORE),'workers':a.workers,'requested_trials':a.trials,
              'boss_slot':a.boss_slot,'no_rendering':True,'no_lookahead':not any(c.get('lookahead') for c in configs),'full_game_clear_verified':False}
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (a.output.parent/'active-batch.json').write_text(json.dumps({'directory':str(a.output.resolve())}))
    (a.output/'source.py').write_bytes(Path(__file__).read_bytes())
    policy=Path(__file__).with_name('kovsh.py')
    frontend=Path(__file__).with_name('emulator.py')
    (a.output/'policy.py').write_bytes(policy.read_bytes())
    (a.output/'frontend.py').write_bytes(frontend.read_bytes())
    if a.behavior_trees or a.behavior_forest:
        behavior=Path(__file__).with_name('kovsh_behavior.py')
        (a.output/'behavior.py').write_bytes(behavior.read_bytes())
        manifest['behavior_sha256']=sha(behavior)
    manifest.update(policy_sha256=sha(policy),frontend_sha256=sha(frontend))
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2))
    start=time.perf_counter();results=[]
    # FBNeo's DLL lifetime is process-scoped: never unload/reinitialize it for a second trial.
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers,max_tasks_per_child=1) as pool:
        jobs=[(str(a.state.resolve()),str(a.output.resolve()),i,c,a.frames,a.boss_slot) for i,c in enumerate(configs[:a.trials])]
        futures=[pool.submit(trial,j) for j in jobs]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result());best=max(results,key=lambda r:r['fitness']);elapsed=time.perf_counter()-start
            status={'completed':len(results),'total':len(jobs),'seconds':elapsed,
                    'total_simulated_frames':sum(r['frames'] for r in results),
                    'aggregate_fps':sum(r['frames'] for r in results)/elapsed,'best_trial':best['trial'],
                    'best_boss_remaining':best['boss_min_hp'],'best_hp':best['after']['hp'],
                    'candidate_wins':sum(r['boss_defeated_candidate'] for r in results)}
            (a.output/'status.json').write_text(json.dumps(status,indent=2))
            (a.output/'results.json').write_text(json.dumps(results,indent=2))
            print(json.dumps(status),flush=True)
    plot(a.output,results)


if __name__=='__main__':main()
