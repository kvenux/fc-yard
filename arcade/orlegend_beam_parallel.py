"""Parallel practice rollouts; cold normal-input replay is the acceptance gate."""
import argparse,concurrent.futures,copy,gzip,json,time
from pathlib import Path
from emulator import Emulator
from orlegend import ROM,sha
from orlegend_bt import Controller
from orlegend_bt_train import observation
from orlegend_beam import keys

worker=None;worker_policy=None

def static_loot_keys(o,ram,t,allowed=None):
    allowed=set([5,6,7,8,9,10,11,15,17,18,19,20,21,22,23] if allowed is None else allowed)
    targets=[]
    for i in range(80):
        b=0xc266+0x98*i
        ident=ram[b+0x7f]
        if ram[b+1]!=2 or ram[b+4]!=28 or ident not in allowed:continue
        x=int.from_bytes(ram[b+0x14:b+0x16],'little');y=int.from_bytes(ram[b+0x16:b+0x18],'little')
        if 0<=x<10000 and 60<=y<=600:targets.append({'slot':-1,'x':x,'y':y,'hp':1})
    if not targets:return []
    target=min(targets,key=lambda e:abs(e['x']-o['x'])+3*abs(e['y']-o['y']))
    dx,dy=target['x']-o['x'],target['y']-o['y'];movement=[]
    if abs(dx)>12:movement.append('right' if dx>0 else 'left')
    if abs(dy)>5:movement.append('down' if dy>0 else 'up')
    if movement:return movement
    if t%12==0 and o['player_facing']!=('right' if dx>=0 else 'left'):return ['right' if dx>=0 else 'left']
    return ['attack'] if t%4<2 else []

def damage_increment(old,now,boss_keys,ram):
    if old['stage_raw']!=now['stage_raw']:return 0,0
    total=boss=0
    for enemy in old['enemies']:
        b=0x11a88+enemy['slot']*0x13e
        hp=int.from_bytes(ram[b:b+2],'little')
        lost=max(0,enemy['hp']-hp);total+=lost
        if (old['stage_raw'],enemy['slot']) in boss_keys:boss+=lost
    return total,boss
def initialize(policy):
    global worker,worker_policy
    worker=Emulator(ROM,deterministic=True,headless=True);worker_policy=policy

def rollout(job):
    state,old,done,boss_damage,elapsed,name,hold,chapter,lives,visited,boss_keys=job
    visited=list(visited)
    boss_keys=set(map(tuple,boss_keys))
    boss_keys.update((old['stage_raw'],v['slot']) for v in old['enemies'] if v['hp']>=100)
    worker.restore(state);inputs=[];ctrl=Controller(worker_policy) if name=='policy' else None;passed=False
    stop_charge_at_full=name=='charge' and old['resources']['meter']<96 and worker_policy['parameters'].get('search_charge_stop_at_full',False)
    charge_completed=False
    if name=='boss_policy':
        spec=copy.deepcopy(worker_policy);spec['parameters']['focus_known_boss']=True
        for branch in spec['tree']['children']:
            children=branch.get('children',[])
            if children and children[0].get('name')=='super_ready':
                children[0]['params']['known_boss']=True;children[1]['params']['known_boss']=True
        ctrl=Controller(spec);ctrl.scene=old['stage_raw'];ctrl.boss_slots={slot for scene,slot in boss_keys if scene==old['stage_raw']}
    if name=='adds_policy':
        ctrl=Controller(worker_policy)
    if name.startswith('item_') or name.startswith('finish_'):
        ident={'item_ice':6,'item_fire':15,'item_fire_finish':15,'item_tower':9}.get(name)
        if ident is None:ident=int(name.split('_')[1])
        allowed_scenes=worker_policy['parameters'].get('search_item_allowed_scenes',{}).get(str(ident),worker_policy['parameters'].get('search_item_scenes'))
        if allowed_scenes is not None and old['stage_raw'] not in allowed_scenes:return {'valid':False,'simulated':0}
        allowed_slots=worker_policy['parameters'].get('search_item_boss_slots',{}).get(str(ident))
        if allowed_slots is not None and not any(v['slot'] in allowed_slots and (old['stage_raw'],v['slot']) in boss_keys and v['hp']>0 for v in old['enemies']):return {'valid':False,'simulated':0}
        finishing=name=='item_fire_finish' or name.startswith('finish_')
        minimum,maximum=(1,39) if finishing else (40,4095)
        reserve=1 if ident==15 else 0
        last_fire_limit=worker_policy['parameters'].get('search_allow_last_fire_below',0)
        if name=='item_fire_finish' and last_fire_limit and any((old['stage_raw'],v['slot']) in boss_keys and 0<v['hp']<=last_fire_limit for v in old['enemies']):
            reserve=0;maximum=min(maximum,last_fire_limit)
        if finishing and not any((old['stage_raw'],v['slot']) in boss_keys and minimum<=v['hp']<=maximum for v in old['enemies']):return {'valid':False,'simulated':0}
        if not any(v['id']==ident and v['count']>reserve for v in old['resources']['inventory']) or not any(minimum<=v['hp']<=maximum for v in old['enemies']):return {'valid':False,'simulated':0}
        item_cooldown=99999 if worker_policy['parameters'].get('search_item_once',False) else 180
        spec=copy.deepcopy(worker_policy);spec['tree']['children'].insert(0,{'type':'sequence','children':[{'type':'condition','name':'item_ready','params':{'scenes':[old['stage_raw']],'choose':True,'ids':[ident],'reserves':{'15':reserve},'min_hp':minimum,'max_hp':maximum,'known_boss':finishing,'dx':800,'dy':180}},{'type':'action','name':'select_item','params':{'ids':[ident],'reserves':{'15':reserve},'radial_select':True,'timeout':45,'cooldown':item_cooldown}}]});ctrl=Controller(spec);ctrl.scene=old['stage_raw'];ctrl.boss_slots={slot for scene,slot in boss_keys if scene==old['stage_raw']}
        if ident in worker_policy['parameters'].get('search_item_ground_ids',[]):
            spec['tree']['children'][0]['children'][0]['params'].update(ground_enemy=True,allowed_enemy_states=[2,6])
            ctrl=Controller(spec);ctrl.scene=old['stage_raw'];ctrl.boss_slots={slot for scene,slot in boss_keys if scene==old['stage_raw']}
    count=hold*((10 if not old['enemies'] else 4) if ctrl else 4 if name=='static_loot' else 2 if name=='charge' else 1)
    for t in range(count+int(stop_charge_at_full)):
        if t==count and not charge_completed:break
        observed=old
        if name=='adds_policy':
            adds=[v for v in old['enemies'] if (old['stage_raw'],v['slot']) not in boss_keys]
            if adds:observed={**old,'enemies':adds}
        if name in ('boss_combat','boss_approach'):
            targets=[v for v in old['enemies'] if (old['stage_raw'],v['slot']) in boss_keys]
            if not targets:targets=sorted(old['enemies'],key=lambda v:v['hp'],reverse=True)[:1]
            observed={**old,'enemies':targets}
        if name=='boss_approach' and observed['enemies']:
            target=observed['enemies'][0];dx=target['x']-old['x'];dy=target['y']-old['y'];k=[]
            if abs(dx)>56:k.append('right' if dx>0 else 'left')
            if abs(dy)>14:k.append('down' if dy>0 else 'up')
            if abs(dx)<=56 and abs(dy)<=14 and t%4<2:k.append('attack')
            elif t%30<2:k=[v for v in k if v!='down']+['jump']
        elif name=='static_loot':k=static_loot_keys(old,worker.ram_view(),t,worker_policy['parameters'].get('search_loot_ids'))
        else:k=ctrl.choose(observed,elapsed+t) if ctrl else keys('combat' if name=='boss_combat' else name,observed,t)
        if charge_completed:k=[]
        worker.step(k);now=observation(worker);inputs.append(k)
        if now['lives']<lives or now['hp']<=0:return {'valid':False,'simulated':len(inputs),'o':now,'time_remaining':worker.ram_view()[0xc06f],'failure':'hp_zero' if now['hp']<=0 else 'lives_decreased'}
        damage,boss_hit=damage_increment(old,now,boss_keys,worker.ram_view());done+=damage;boss_damage+=boss_hit
        boss_keys.update((now['stage_raw'],v['slot']) for v in now['enemies'] if v['hp']>=100)
        old=now
        # Intro maps reuse a later playable scene ID; do not credit them as visited areas.
        if now.get('player_state')!=9 and now['stage_raw'] not in visited:visited.append(now['stage_raw'])
        if now['stage_byte']>=chapter:passed=True;break
        if charge_completed:break
        if stop_charge_at_full and now['resources']['meter']>=96:charge_completed=True
    ram=worker.ram_view()
    defeated=[(scene,slot) for scene,slot in boss_keys if scene==old['stage_raw'] and int.from_bytes(ram[0x11a88+slot*0x13e:0x11a8a+slot*0x13e],'little')==0]
    return {'valid':True,'simulated':len(inputs),'state':worker.save(),'o':old,'inputs':inputs,'damage_done':done,'boss_damage':boss_damage,'passed':passed,'visited':visited,'boss_keys':list(boss_keys),'defeated_boss_keys':defeated,'time_remaining':ram[0xc06f]}

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--output',required=True);p.add_argument('--policy',required=True);p.add_argument('--workers',type=int,default=6);p.add_argument('--width',type=int,default=24);p.add_argument('--depth',type=int,default=80);p.add_argument('--hold',type=int,default=60);p.add_argument('--time-penalty',type=float,default=0);p.add_argument('--items',action='store_true');p.add_argument('--item-ids',default='');p.add_argument('--boss-focus',action='store_true');p.add_argument('--fire-finish',action='store_true');a=p.parse_args()
    out=Path(a.output);out.mkdir(exist_ok=False);policy=json.loads(Path(a.policy).read_text());e=Emulator(ROM,deterministic=True,headless=True);raw=Path(a.state).read_bytes();e.restore(raw);initial=observation(e);root=e.save();core=e.core_path;e.close()
    (out/'initial.state').write_bytes(raw);(out/'policy.json').write_text(json.dumps(policy,indent=2));(out/'source.py').write_bytes(Path(__file__).read_bytes())
    dependencies=['emulator.py','orlegend.py','orlegend_resources.py','orlegend_bt_train.py','orlegend_bt.py','behavior_tree.py','orlegend_beam.py']
    for name in dependencies:(out/name).write_bytes(Path(__file__).with_name(name).read_bytes())
    (out/'source-hashes.json').write_text(json.dumps({name:sha(Path(__file__).with_name(name)) for name in dependencies},indent=2))
    (out/'manifest.json').write_text(json.dumps({'scope':'checkpoint branching practice; not a cold clear','state':a.state,'state_sha256':sha(a.state),'rom_sha256':sha(ROM),'core_sha256':sha(core),'workers':a.workers,'width':a.width,'depth':a.depth,'hold':a.hold,'options':vars(a)},indent=2))
    actions=['combat','left+attack','right+attack','up+attack','down+attack','up','down','left+jump','right+jump','up+right+jump','down+right+jump','up+left+jump','down+left+jump','policy','charge']
    if policy['parameters'].get('search_navigation_actions'):actions+=['right','left','up+right','down+right','up+left','down+left','wait']
    if policy['parameters'].get('search_rush'):actions+=['rush']
    if policy['parameters'].get('search_adds'):actions+=['adds_policy']
    if policy['parameters'].get('search_inventory_weight',0):actions+=['loot']
    if policy['parameters'].get('search_static_loot'):actions+=['static_loot']
    if a.items:actions+=['item_ice','item_fire','item_tower']
    if a.fire_finish:actions+=['item_fire_finish']
    actions+=['item_'+v for v in a.item_ids.split(',') if v]
    if a.boss_focus:actions+=['boss_policy','boss_combat','boss_approach']
    beam=[{'state':root,'o':initial,'plan':[],'elapsed':0,'damage_done':0,'boss_damage':0,'visited':[] if initial.get('player_state')==9 else [initial['stage_raw']],'boss_keys':[]}];goals=[];started=time.perf_counter();simulated=0
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers,initializer=initialize,initargs=(policy,)) as pool:
        for depth in range(a.depth):
            step_actions=list(actions)
            if policy['parameters'].get('search_auto_items'):
                present={v['id'] for n in beam for v in n['o']['resources']['inventory'] if v['count']>(1 if v['id']==15 else 0)}
                step_actions += [f'item_{ident}' for ident in sorted(present) if f'item_{ident}' not in step_actions]
                if policy['parameters'].get('search_item_finishes'):step_actions += [f'finish_{ident}' for ident in sorted(present) if ident!=15]
            pairs=[(parent,name) for parent in beam for name in step_actions]
            jobs=[(n['state'],n['o'],n['damage_done'],n['boss_damage'],n['elapsed'],name,a.hold,initial['stage_byte']+1,initial['lives'],n['visited'],n['boss_keys']) for n,name in pairs]
            candidates=[]
            for (parent,name),r in zip(pairs,pool.map(rollout,jobs,chunksize=1)):
                simulated+=r['simulated']
                if not r['valid']:continue
                o=r['o'];progress_weight=policy['parameters'].get('search_progress_weight',.04)
                if not any((o['stage_raw'],v['slot']) in set(map(tuple,r['boss_keys'])) for v in o['enemies']):
                    progress_weight=policy['parameters'].get('search_mob_progress_weights',{}).get(str(o['stage_raw']),progress_weight)
                progress=o['x']*progress_weight
                if o['stage_raw']==1283 and not o['enemies'] and policy['parameters'].get('search_navigation_actions'):progress=-abs(o['x']-256)*policy['parameters'].get('search_progress_weight',.04)-abs(o['y']-116)*.1
                target=policy['parameters'].get('search_progress_targets',{}).get(str(o['stage_raw']))
                if target and (not target.get('when_no_enemies') or not o['enemies']):progress=-abs(o['x']-target['x'])*target.get('weight_x',.04)-abs(o['y']-target['y'])*target.get('weight_y',.1)
                if o['stage_raw']==514:progress=-abs(o['x']-170)*.08-abs(o['y']-90)*.04
                elif o['stage_raw']==513 and not o['enemies']:progress=-abs(o['x']-995)*.08-abs(o['y']-115)*.04
                progress+=policy['parameters'].get('search_scene_progress_offsets',{}).get(str(o['stage_raw']),0)
                if o['stage_raw'] in policy['parameters'].get('search_boss_distance_scenes',[]):
                    known=set(map(tuple,r['boss_keys']))
                    targets=[v for v in o['enemies'] if (o['stage_raw'],v['slot']) in known]
                    if targets:
                        progress+=policy['parameters'].get('search_boss_phase_bonus',{}).get(str(o['stage_raw']),0)
                        distance=min(abs(v['x']-o['x'])+2*abs(v['y']-o['y']) for v in targets)
                        progress-=max(0,distance-policy['parameters'].get('search_boss_safe_distance',180))*policy['parameters'].get('search_boss_distance_weight',.15)
                if o['stage_raw'] in policy['parameters'].get('search_mob_backtrack_scenes',[]) and o['enemies'] and not any((o['stage_raw'],v['slot']) in set(map(tuple,r['boss_keys'])) for v in o['enemies']):
                    target=min(o['enemies'],key=lambda v:abs(v['x']-o['x'])+3*abs(v['y']-o['y']))
                    progress-=max(0,o['x']-target['x']-32)*policy['parameters'].get('search_mob_backtrack_weight',.8)+abs(o['y']-target['y'])*.3
                damage_score=r['boss_damage']*2+(r['damage_done']-r['boss_damage'])*policy['parameters'].get('search_mob_damage_weight',.2) if a.boss_focus else r['damage_done']*.8
                inventory_score=sum(v['count']*policy['parameters'].get('search_item_weights',{}).get(str(v['id']),policy['parameters'].get('search_inventory_weight',0)) for v in o['resources']['inventory'] if v['id']!=15)
                obstacle_score=policy['parameters'].get('search_tree_hits_weight',0)*min(16,max(0,o.get('tree_hits',0))) if o['stage_raw'] in policy['parameters'].get('search_tree_scenes',[]) else 0
                score=o['hp']*policy['parameters'].get('search_hp_weight',20)+damage_score+progress+o['resources']['meter']*policy['parameters'].get('search_meter_weight',.2)+inventory_score-len(o['enemies'])*policy['parameters'].get('search_enemy_count_weight',0)-(parent['elapsed']+len(r['inputs']))*a.time_penalty+400*(len(r['visited'])-1)+(100000 if r['passed'] else 0)
                score+=obstacle_score
                score+=policy['parameters'].get('search_boss_defeat_bonus',0)*len(r['defeated_boss_keys'])
                node={'state':r['state'],'o':o,'plan':parent['plan']+[{'name':name,'inputs':r['inputs']}],'elapsed':parent['elapsed']+len(r['inputs']),'damage_done':r['damage_done'],'boss_damage':r['boss_damage'],'score':score,'visited':r['visited'],'boss_keys':r['boss_keys'],'time_remaining':r['time_remaining']}
                (goals if r['passed'] else candidates).append(node)
            candidates.sort(key=lambda n:n['score'],reverse=True);beam=[];seen=set()
            for n in candidates:
                o=n['o'];res=o['resources'];sig=(o['stage_raw'],o['x']//25,o['y']//15,o['hp'],o['player_state'],o['player_move'],o['player_facing'],o['air_mask'],o.get('tree_hits',0),res['meter']//16,res['selected'],res.get('menu_open'),tuple((v['id'],v['count']) for v in res['inventory']),tuple((v['slot'],v['hp']//5,v['x']//100,v['y']//40,v['state']) for v in o['enemies']))
                if sig in seen:continue
                seen.add(sig);beam.append(n)
                if len(beam)>=a.width:break
            best=max(goals or beam,key=lambda n:(n['o']['hp'],n['score'])) if goals or beam else None
            wall=time.perf_counter()-started;summary={'scope':'checkpoint practice only; not a cold clear','depth':depth+1,'simulated_frames':simulated,'wall':wall,'aggregate_fps':simulated/wall,'workers':a.workers,'goals':len(goals),'best':{k:best[k] for k in ('o','elapsed','damage_done','boss_damage','boss_keys','visited','score')} if best else None}
            leader=max(goals or beam,key=lambda n:n['score']) if goals or beam else None
            summary['leader']={k:leader[k] for k in ('o','elapsed','score','time_remaining')} if leader else None
            (out/'progress.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
            if best:
                plan={'initial':initial,'after':best['o'],'macros':best['plan']}
                (out/'best.state').write_bytes(best['state']);(out/'plan.json').write_text(json.dumps(plan,indent=2))
                checkpoints=out/'checkpoints';checkpoints.mkdir(exist_ok=True)
                (checkpoints/f'depth-{depth+1:03d}.state').write_bytes(best['state'])
                (checkpoints/f'depth-{depth+1:03d}.json.gz').write_bytes(gzip.compress(json.dumps(plan).encode()))
                if leader is not best:
                    (checkpoints/f'leader-{depth+1:03d}.state').write_bytes(leader['state'])
                    (checkpoints/f'leader-{depth+1:03d}.json.gz').write_bytes(gzip.compress(json.dumps({'initial':initial,'after':leader['o'],'macros':leader['plan']}).encode()))
            if not beam or goals:break

if __name__=='__main__':main()
