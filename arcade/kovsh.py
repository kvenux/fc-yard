"""KOVSH V104: read-only observation, real-input heuristic experiments.

Partial observer: victory is deliberately not inferred from a scene number.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from emulator import Emulator, ROOT

OUT = ROOT / 'runs/kovsh'
ROM = ROOT / 'roms/kovsh.zip'
CORE = Path(os.environ.get('KOVSH_CORE', ROOT / 'cores/fbneo_libretro.dll'))

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def publish(path,body):
    temp=path.with_suffix(path.suffix+'.next')
    temp.write_bytes(body)
    for _ in range(5):
        try:temp.replace(path);return
        except PermissionError:time.sleep(.01)
    # A broadcast reader/antivirus must never abort a game episode.

def observe(r):
    def w(o):
        return int.from_bytes(r[o:o+2], 'little')
    def coordinate(o):
        return int.from_bytes(r[o:o+2], 'little',signed=True)
    enemies=[]
    for i in range(8):
        b=0xcf18+i*0x1a6
        if 0<w(b+100)<4096 and w(b+10):
            enemies.append(dict(slot=i,x=coordinate(b+14),y=coordinate(b+16),
                                ground_y=coordinate(b+28),height=coordinate(b+30),hp=w(b+100)))
    inv={};slots=[]
    # Only the first item_count entries are active. The remaining UI slots retain
    # stale quantities/IDs, including item 1, even with an empty inventory.
    item_count=min(r[0x12971],18)
    for b in range(0x1294c,0x1294c+item_count*2,2):
        slots.append({'id':r[b+1],'count':r[b]})
        if r[b] and 0<r[b+1]<64:inv[str(r[b+1])]=inv.get(str(r[b+1]),0)+r[b]
    selected_slot=r[0x12973]
    selected_item=slots[selected_slot]['id'] if selected_slot<len(slots) else None
    return dict(hp=w(0x114c4), lives=r[0x11b02], inventory=inv, selected_item=selected_item,
                item_count=item_count, inventory_slots=slots, selected_slot=selected_slot,
                facing='left' if r[0x114cd]&0x20 else 'right',
                actor_code=r[0x1146a],actor_phase=r[0x1146d],
                score=(w(0x11b08)<<16)|w(0x11b0a),time_remaining=max(0,r[0x1b21f]-1),
                x=coordinate(0x1146e),y=coordinate(0x11470),ground_y=coordinate(0x1147c),height=coordinate(0x1147e),
                chapter=w(0x1b1d8),room_raw=r[0x1b1db],room_phase_raw=r[0x1b1da],
                scene_raw=w(0x1b71c),section=r[0x1b713],enemies=enemies)

def action(o,f,c):
    keys=[]
    if c.get('ground_alignment'):
        o={**o,'y':o.get('ground_y',o['y']),
           'enemies':[{**x,'y':x.get('ground_y',x['y'])} for x in o['enemies']]}
    if c.get('focus_boss') and o['chapter']==0 and o['scene_raw']==257 and o['section']==4:
        valid=[e for e in o['enemies'] if not (e['slot']==1 and e['hp']==424)]
        boss=[e for e in valid if e['slot']==0 and e['hp']>30]
        o={**o,'enemies':boss or valid}
    if c.get('focus_large'):
        large=[e for e in o['enemies'] if e['hp']>60 or e['slot'] in c.get('focus_slots',[])]
        if large:o={**o,'enemies':large}
    if c.get('finish_weak'):
        weak=[e for e in o['enemies'] if e['hp']<=16]
        if weak:o={**o,'enemies':weak}
    if c.get('focus_forward'):
        forward=[e for e in o['enemies'] if e['x']>=o['x']-32]
        if forward:o={**o,'enemies':forward}
    if c.get('focus_rear'):
        rear=[e for e in o['enemies'] if e['x']<o['x']-80]
        if rear:o={**o,'enemies':rear}
    if c.get('focus_cluster') and o['enemies']:
        anchor=max(o['enemies'],key=lambda e:sum(1 for other in o['enemies'] if abs(other['x']-e['x'])<110 and abs(other['y']-e['y'])<20))
        group=[e for e in o['enemies'] if abs(e['x']-anchor['x'])<110 and abs(e['y']-anchor['y'])<20]
        o={**o,'enemies':group}
    if o['enemies']:
        e=min(o['enemies'],key=lambda e:abs(e['x']-o['x'])+3*abs(e['y']-o['y']))
        dx,dy=e['x']-o['x'],e['y']-o['y']
        if abs(dy)>c['align']:keys.append('down' if dy>0 else 'up')
        face='right' if dx>0 else 'left'
        if abs(dx)>c['distance'] or f%c.get('face_period',c['period'])==0 or (c.get('facing_feedback') and o.get('facing')!=face):
            keys.append('right' if dx>0 else 'left')
    else:
        keys.append(c.get('route','right'))
        if c.get('exit_x') and abs(o['x']-c['exit_x'])>8:
            keys=['right' if o['x']<c['exit_x'] else 'left']
        # Sweep the walkable lane when no enemy remains, to find stage exits.
        if c.get('sweep'):
            keys.append('up' if (f//240)%2 else 'down')
        if c.get('route_v2') and o['chapter']==0:
            if o['scene_raw']==0:
                if o['y']>=390:keys=['right','down']
                elif abs(o['x']-600)>8:keys=['left' if o['x']>600 else 'right']
                else:keys=['down']
            elif o['scene_raw']==1 and o['section']==2:keys=['left','down']
            else:keys=['right']+(['up'] if c.get('up_exit') else [])
        elif c.get('route_v2'):
            keys=['right']
    in_range=not c.get('attack_in_range') or not o['enemies'] or (abs(dx)<=80 and abs(dy)<=16)
    if o['enemies'] and in_range and f%c['period']<c['period']//2:keys.append('attack')
    if c.get('jump') and f%c['jump']<2:
        keys=[k for k in keys if k!='attack']+['jump']
    special_ready=not c.get('special_in_range') or not o['enemies'] or (abs(dx)<=80 and abs(dy)<=16) or (c.get('special')=='dash' and abs(dx)>80)
    if c.get('special') and o['enemies'] and special_ready:
        t=f%c.get('special_period',48)
        face='right' if dx>0 else 'left'
        sequence={'qcf':[['down'],['down',face],[face,'attack']],
                  'du':[['down'],['up'],['attack']],
                  'bf':[['left' if face=='right' else 'right'],[face],['attack']],
                  'dd':[['down'],[],['down','attack']],
                  'ud':[['up'],['down'],['attack']],
                  'dash':[[face],[],[face,'attack']]}
        if t<9:keys=sequence[c['special']][t//3]
    return keys

class Items:
    def __init__(self):
        self.started=None;self.last=-600;self.events=[];self.before={}
    def choose(self,o,f):
        if self.started is None:
            if f-self.last<300 or not o['inventory'] or not o['enemies'] or o['hp']==0:return None
            e=min(o['enemies'],key=lambda e:abs(e['x']-o['x'])+3*abs(e['y']-o['y']))
            if abs(e['y']-o['y'])>18:return None
            self.started=f;self.before=dict(o['inventory']);self.face='right' if e['x']>o['x'] else 'left'
            self.direct=str(o['selected_item']) in o['inventory']
        t=f-self.started
        if t==0:return [self.face]
        if t<35:return []
        if self.direct:
            if t==35:return ['d']
        else:
            if t==35:return ['c']
            if t==55:return [['up','right','down','left'][len(self.events)%4]]
            if t==70:return ['attack']
            if t==100:return ['d']
        end=90 if self.direct else 155
        if t<end:return []
        consumed={k:v-o['inventory'].get(k,0) for k,v in self.before.items() if v>o['inventory'].get(k,0)}
        self.events.append(dict(frame=f,consumed=consumed,confirmed=bool(consumed)))
        self.last=f;self.started=None
        return None

class Navigator:
    def __init__(self,config=None):
        self.config=config or {}
        self.position=None;self.changed=0;self.last_arrow=None;self.arrow_frame=-1000;self.chapter=None;self.events=[]
        self.escape_until=0;self.escape_keys=[];self.escape_attempts=0
        self.gate_position=None;self.gate_stalled=0
        self.room=None;self.cave_return=False
    def choose(self,o,f,picture):
        if o.get('room_raw')!=self.room:
            self.room=o.get('room_raw');self.cave_return=False
            self.position=None;self.changed=f;self.escape_until=0;self.escape_attempts=0
        if o['chapter']!=self.chapter:
            self.last_arrow=None;self.chapter=o['chapter'];self.position=None;self.changed=f
            self.escape_until=0;self.escape_attempts=0
        if self.config.get('cave_return_exit') and o['chapter']==3 and o.get('room_raw')==4 and not o['enemies']:
            if o['x']>=1150 or self.cave_return:
                self.cave_return=True
                if o['x']>875:return ['left']
                if o['x']<855:return ['right']
                return ['up'] if o.get('ground_y',o['y'])>136 else []
        bamboo=o['chapter']==3 and o.get('room_raw',0)==0
        if self.config.get('bamboo_exit_lane') and bamboo and not o['enemies'] and o['x']>1850:
            if self.config.get('exit_lower_lane'):
                return ['right']+(['down'] if o.get('ground_y',o['y'])<174 else [])
            if self.config.get('exit_diagonal'):
                return (['right'] if o['x']<2004 else [])+(['up'] if o.get('ground_y',o['y'])>162 else [])
            if o.get('ground_y',o['y'])>175:
                return ['left'] if o['x']>1900 else ['up']
            return ['right'] if o['x']<2004 else []
        if self.config.get('bamboo_gate') and bamboo and not o['enemies'] and 1400<o['x']<1740:
            if o.get('ground_y',o['y'])>152:
                return ['left'] if o['x']>1580 else ['up']
            if self.config.get('gate_attack_stuck_only'):
                position=(o['x'],o.get('ground_y',o['y']),o['score'])
                self.gate_stalled=self.gate_stalled+1 if position==self.gate_position else 0
                self.gate_position=position
                return ['right']+(['attack'] if self.gate_stalled>=24 else [])
            return ['right']+(['attack'] if f%120<80 else [])
        signature=(o['x']//8,o['y']//8,o['score'])
        if signature!=self.position:self.position=signature;self.changed=f
        if f<self.escape_until:return self.escape_keys
        if o['hp'] and f-self.changed>180:
            if self.config.get('break_obstacles') and not o['enemies']:
                self.escape_keys=[['right','attack'],['up','attack'],['right'],['down','attack'],['left'],['up']][self.escape_attempts%6]
            else:self.escape_keys=['down'] if self.escape_attempts%2==0 else ['up']
            self.escape_attempts+=1;self.escape_until=f+90
            self.events.append(dict(frame=f,buttons=self.escape_keys,reason='stuck_escape'))
            return self.escape_keys
        if o['chapter']>0 and picture is not None:
            if f%30==0:
                from kovsh_vision import arrow
                found=arrow(picture)
                if found:
                    self.last_arrow=found['buttons'];self.arrow_frame=f
                    self.events.append(dict(frame=f,**found))
            if f-self.arrow_frame<180:return self.last_arrow
        return None

def plan_choices(o,c):
    if c.get('tactical_choices') and o['enemies']:
        # Named battle mechanisms, rather than a distance/period parameter grid.
        choices=[{**c,'tactic':'pressure','distance':32,'special':None,'face_period':60},
                 {**c,'tactic':'finish_weak','distance':24,'special':None,'finish_weak':True,'face_period':60},
                 {**c,'tactic':'vertical_sweep','distance':32,'special':'du','special_period':36},
                 {**c,'tactic':'low_sweep','distance':32,'special':'dd','special_period':36},
                 {**c,'tactic':'quarter_circle_sweep','distance':32,'special':'qcf','special_period':36},
                 {**c,'tactic':'cluster_sweep','distance':32,'special':'qcf','special_period':36,'focus_cluster':True},
                 {**c,'tactic':'dash_chase','distance':32,'special':'dash','special_period':36},
                 {**c,'tactic':'forward_pressure','distance':32,'special':None,'focus_forward':True,'face_period':60},
                 {'tactic':'escape_upper_lane','hop':'up'},
                 {'tactic':'escape_lower_lane','hop':'down'}]
        if any(x.get('height',0)<-15 for x in o['enemies']):
            choices.append({**c,'tactic':'upper_counter','distance':32,'special':'ud','special_period':36})
            if c.get('air_combo') and any(x.get('height',0)<-15 and abs(x['x']-o['x'])<100 for x in o['enemies']):
                choices.append({'tactic':'jump_air_combo','air_pursuit':True})
        if any(abs(x['x']-o['x'])<45 and abs(x.get('ground_y',x['y'])-o.get('ground_y',o['y']))<10 for x in o['enemies']):
            choices.append({'tactic':'hold_combo','flurry':4})
        if o['inventory']:
            if str(o.get('selected_item')) in o['inventory']:
                choices.append({'tactic':'throw_selected_item','use_after':35})
            choices += [{'tactic':'select_throw_'+direction,'item_direction':direction} for direction in ('up','right','down','left')]
        if c.get('chase_mechanisms'):
            choices += [{**c,'tactic':'fast_aligned_chase','special':None,'attack_in_range':True},
                        {**c,'tactic':'fast_sweep_chase','special':'qcf','special_period':36,'attack_in_range':True,'special_in_range':True},
                        {**c,'tactic':'fast_low_sweep_chase','special':'dd','special_period':36,'attack_in_range':True,'special_in_range':True},
                        {**c,'tactic':'clear_rear_straggler','special':None,'attack_in_range':True,'focus_rear':True}]
        if c.get('combat_rules'):
            from kovsh_combat import MODES
            choices += [{'tactic':mode,'combat_rule':mode} for mode in c.get('combat_modes',MODES)]
        if c.get('boss_priority') and c.get('focus_slots'):
            choices += [{**c,'tactic':'boss_'+name,'focus_large':True,'special':special,
                         'special_period':36,'attack_in_range':True,'special_in_range':True}
                        for name,special in [('normal',None),('quarter_circle','qcf'),('low_sweep','dd'),('vertical_sweep','du')]]
        if c.get('contextual_choices'):
            close=any(abs(x['x']-o['x'])<=80 and abs(x['ground_y']-o['ground_y'])<=16 for x in o['enemies'])
            allowed={'escape_upper_lane','escape_lower_lane','fast_aligned_chase','fast_sweep_chase','fast_low_sweep_chase','dash_chase','clear_rear_straggler'}
            if close:allowed.update({'pressure','finish_weak','quarter_circle_sweep','vertical_sweep','low_sweep','hold_combo','upper_counter','jump_air_combo'})
            if len(o['enemies'])>=2:allowed.add('cluster_sweep')
            choices=[x for x in choices if x.get('combat_rule') or x['tactic'] in allowed or x['tactic']=='throw_selected_item' or 'item_direction' in x or x['tactic'].startswith('boss_')]
        return choices
    if c.get('behavior_forest') and o['enemies']:
        from kovsh_behavior import STRATEGIES
        return [{'behavior_tree':name,'boss_slot':c.get('target_slot')} for name in STRATEGIES]
    choices=[{**c,'distance':d,'special':s,'special_period':36,'period':p}
             for d in (24,48,72) for s in (None,'du','qcf','dash','bf','dd','ud') for p in (4,)]
    choices += [{**c,'distance':d,'special':None,'face_period':60,'period':p} for d in (32,56) for p in (4,8,12)]
    choices += [{'fixed':ks} for ks in [[],['up'],['down'],['left'],['right'],['jump'],['d'],['attack','jump']]]
    choices += [{'hop':direction} for direction in ('up','down','left','right')]
    if c.get('guard'):choices += [{'fixed':['left','c']},{'fixed':['right','c']}]
    if o['inventory']:
        choices += [{'item_direction':d} for d in ('up','down','left','right')]
        choices += [{'use_after':delay} for delay in (16,48,96)]
    if c.get('navigation_mpc') and not o['enemies']:
        choices += [{'travel':keys} for keys in [['right'],['left'],['up'],['down'],['right','up'],['right','down'],['left','up'],['left','down'],['right','attack'],['up','attack'],['down','attack'],['right','jump']]]
        choices += [{'detour':direction} for direction in ('up','down')]
        choices += [{'sidestep':direction} for direction in ('up','down')]
    return choices

def evaluate_candidate(e,state,o,f,c,choice):
    e.av_enable=2 if e.headless or c.get('fast_preview') else 3
    e.restore(state);seq=[];ram=e.ram_view();damage_total=0;early_damage=0;early_kills=0;early_clears=0
    def slot_health(r):return [int.from_bytes(r[0xcf18+i*0x1a6+100:0xcf18+i*0x1a6+102],'little') for i in range(8)]
    previous_hp=slot_health(ram)
    behavior=None;combat=None;navigator=Navigator(c)
    if choice.get('combat_rule'):
        from kovsh_combat import Combat
        combat=Combat(choice['combat_rule'])
    if choice.get('behavior_tree'):
        from kovsh_behavior import BehaviorTree
        behavior=BehaviorTree(choice['behavior_tree'],choice.get('boss_slot'))
    horizon=max(180,c.get('horizon',90)) if 'item_direction' in choice else c.get('horizon',90)
    if 'use_after' in choice:horizon=max(horizon,choice['use_after']+60)
    for t in range(horizon):
        obs=observe(ram)
        if combat:
            keys=combat.tick(obs,f+t)
        elif behavior:
            keys=behavior.tick(obs,f+t)
        elif choice.get('air_pursuit'):
            targets=[x for x in obs['enemies'] if x['height']<-15]
            if not targets:keys=action(obs,f+t,c)
            else:
                target=min(targets,key=lambda x:abs(x['x']-obs['x']))
                face='right' if target['x']>=obs['x'] else 'left'
                keys=[face] if abs(target['x']-obs['x'])>24 or obs['facing']!=face else []
                if t<2 and obs['height']==0:keys+=['jump']
                if t>=6 and obs['height']<-8 and (f+t)%4<2:keys+=['attack']
        elif 'flurry' in choice:
            target=min(o['enemies'],key=lambda x:abs(x['x']-o['x'])+3*abs(x.get('ground_y',x['y'])-o.get('ground_y',o['y']))) if o['enemies'] else {'x':o['x']+1}
            face='right' if target['x']>=o['x'] else 'left'
            back='left' if face=='right' else 'right'
            if t==0:keys=[face]
            elif t<48:keys=['attack'] if t%choice['flurry']<2 else []
            elif choice.get('chain') and t<120:
                u=t-48
                sequence=([[back],[face],['attack']]+[[]]*5+[[face],[],[face,'attack']]+[[]]*5)*2
                keys=sequence[min(u//3,len(sequence)-1)]
            elif t<120:keys=['attack'] if t%choice['flurry']<2 else []
            else:keys=action(obs,f+t,c)
        elif 'hop' in choice:
            keys=[choice['hop']]+(['jump'] if t<2 else []) if t<45 else action(obs,f+t,c)
        elif 'use_after' in choice:
            delay=choice['use_after']
            keys=[] if t<delay else ['d'] if t<delay+4 else action(obs,f+t,c)
        elif 'sidestep' in choice:
            keys=[choice['sidestep']] if t<30 else ['right']
        elif 'detour' in choice:
            keys=['left'] if t<30 else [choice['detour']] if t<90 else ['right']+(['attack'] if t%4<2 else [])
        elif 'travel' in choice:
            keys=[k for k in choice['travel'] if (k!='attack' or t%4<2) and (k!='jump' or t%36<2)]
        elif 'item_direction' in choice:
            keys=(['c'] if 35<=t<39 else [choice['item_direction']] if 55<=t<59 else ['attack'] if 70<=t<74 else ['d'] if 100<=t<104 else []) if t<120 else action(obs,f+t,c)
            if 95<=t<99 and obs['enemies']:
                target=min(obs['enemies'],key=lambda x:abs(x['x']-obs['x'])+3*abs(x['y']-obs['y']))
                keys=['right' if target['x']>obs['x'] else 'left']
        elif 'fixed' in choice:
            duration=45 if choice['fixed'] in [['up'],['down'],['left'],['right']] else 12
            keys=choice['fixed'] if t<duration else action(obs,f+t,c)
        else:keys=action(obs,f+t,choice)
        if c.get('ram_navigation') and not obs['enemies']:
            nav=navigator.choose(obs,f+t,None)
            if nav is not None:keys=[k for k in nav if k!='attack' or (f+t)%4<2]
        e.step(keys);seq.append(keys);current_hp=slot_health(ram)
        boss_slots=c.get('focus_slots',[]) if c.get('boss_priority') else []
        dealt=sum((old-new)*(c.get('boss_damage_multiplier',3) if i in boss_slots else c.get('boss_damage_multiplier',1) if i==c.get('target_slot') else 1) for i,(old,new) in enumerate(zip(previous_hp,current_hp))
                  if 0<=new<old<4096 and not (o['chapter']==0 and i==1 and old==424))
        damage_total+=dealt
        discount=(horizon-t)/horizon
        early_damage+=dealt*discount
        if c.get('time_efficiency'):
            current=observe(ram)
            active={enemy['slot'] for enemy in obs['enemies']}
            early_kills+=sum((4 if slot in boss_slots else .2 if boss_slots else 1) for slot in active if previous_hp[slot]>0 and current_hp[slot]==0)*discount
            if obs['enemies'] and not current['enemies']:early_clears+=discount
        previous_hp=current_hp
    old={x['slot']:x['hp'] for x in o['enemies']}
    end=observe(ram);new={x['slot']:x['hp'] for x in end['enemies']}
    damage=damage_total if c.get('incremental_damage',True) else sum(max(0,v-new.get(k,0)) for k,v in old.items() if v!=424)
    value=(end['hp']-o['hp'])*c.get('hp_weight',50)+(end['lives']-o['lives'])*20000+damage*25+(end['score']-o['score'])*.1
    value+=(end['time_remaining']-o['time_remaining'])*20
    if c.get('progress_reward'):
        if c.get('time_efficiency'):
            # Reward the time of actual kills, even if the slot is later reused.
            # Waiting after a clear cannot collect a persistent empty-room bonus.
            value+=early_damage*25+early_kills*500+early_clears*1200
            def front(obs):return min([obs['x']]+[x['x'] for x in obs['enemies']])
            value+=max(-600,min(600,front(end)-front(o)))*2
        else:
            killed=sum(1 for enemy in o['enemies'] if current_hp[enemy['slot']]==0)
            value+=killed*500
            if o['enemies'] and not end['enemies']:value+=1200
        if end['chapter']!=o['chapter'] or (o['x']-end['x']>600 and end['time_remaining']-o['time_remaining']>15):value+=15000
    if end['hp']==0:value-=20000
    targets=[x for x in end['enemies'] if x['hp']!=424]
    if targets:
        ykey='ground_y' if c.get('ground_alignment') else 'y'
        value-=min(abs(x['x']-end['x'])+3*abs(x[ykey]-end[ykey]) for x in targets)*.15
    if c.get('navigation_mpc') and not o['enemies']:
        value+=max(-100,min(100,end['x']-o['x']))*.3
        value-=c.get('visited',{}).get(f"{end['x']//24},{end['y']//24}",0)*3
        if end['x']<o['x']-600 or end['chapter']!=o['chapter']:value+=2000
        # Crossing a spawn boundary is progress, not an increased-distance penalty.
        if end['enemies']:value+=c.get('encounter_reward',500)
    commit=max(120,c.get('commit',90)) if 'item_direction' in choice else c.get('commit',c.get('horizon',90))
    if 'use_after' in choice:commit=max(commit,choice['use_after']+4)
    if 'flurry' in choice:commit=max(commit,120)
    if c.get('commit_native_combo') and choice.get('combat_rule'):
        # A locked target must survive beyond the old 15-frame replan boundary.
        # Execute only the already simulated sequence, bounded by its horizon.
        duration=120 if choice['combat_rule'] in ('locked_combo','ground_finisher') and o['hp']>=24 else 60
        commit=max(commit,min(horizon,duration))
    return value,seq[:commit]

def plan(e,o,f,c):
    state=e.save()
    return max((evaluate_candidate(e,state,o,f,c,x) for x in plan_choices(o,c)),key=lambda x:x[0])[1]

_candidate_core=None
def init_candidate_core():
    global _candidate_core
    from multiprocessing.util import Finalize
    _candidate_core=Emulator(ROM,core=CORE,deterministic=True,headless=True)
    Finalize(None,_candidate_core.close,exitpriority=10)

def candidate_task(request):
    value,inputs=evaluate_candidate(_candidate_core,*request)
    return value,inputs,_candidate_core.frame

def planner_worker(connection):
    e=Emulator(ROM,core=CORE,deterministic=True,headless=True)
    try:
        while True:
            request=connection.recv()
            if request is None:break
            state,o,f,c=request
            e.restore(state)
            connection.send(plan(e,o,f,c))
    finally:e.close();connection.close()

def bootstrap():
    e=Emulator(ROM,core=CORE,deterministic=True);trace=[]
    def advance(keys,n):
        for _ in range(n):
            e.step(keys);trace.append(dict(frame=len(trace)+1,buttons=keys))
    try:
        advance([],1800);advance(['coin'],2);advance([],60)
        advance(['start'],4);advance([],420);advance(['attack'],4);advance([],1500)
        if observe(e.ram())['lives']==0:
            advance(['attack'],4);advance([],1500)
        if observe(e.ram())['lives']==0:
            raise RuntimeError('Character selection did not complete')
        (OUT/'initial.state').write_bytes(e.save())
        (OUT/'initial.ram').write_bytes(e.ram());e.picture().save(OUT/'initial.png')
        (OUT/'boot-inputs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in trace))
        (OUT/'boot-manifest.json').write_text(json.dumps(dict(expected=e.fingerprint(),observation=observe(e.ram()),frames=len(trace),rom_sha256=sha(ROM),core_sha256=sha(e.core_path)),indent=2))
        print(observe(e.ram()))
    finally:e.close()

def run(a):
    out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
    initial=out/'initial.state'
    e=Emulator(ROM,core=CORE,deterministic=True,headless=getattr(a,'headless',False))
    prefix_path=getattr(a,'poweron_prefix',None)
    if prefix_path:
        prefix_bytes=Path(prefix_path).read_bytes()
        (out/'poweron-prefix.jsonl').write_bytes(prefix_bytes)
        prefix_life=None;prefix_deaths=[];prefix_started=False;prefix_coins=0;previous_keys=[]
        for i,line in enumerate(prefix_bytes.decode('utf-8').splitlines(),1):
            keys=json.loads(line)['buttons']
            prefix_coins+=int('coin' in keys and 'coin' not in previous_keys);previous_keys=keys
            e.step(keys)
            r=e.ram_view();hp=r[0x114c4]|(r[0x114c5]<<8);lives=r[0x11b02]
            if prefix_coins and 'start' in keys:prefix_started=True
            if prefix_started and hp>0 and prefix_life is None:prefix_life=lives
            if prefix_life is not None and (hp==0 or lives<prefix_life):
                prefix_deaths.append({'frame':i,'hp':hp,'lives':lives})
                if getattr(a,'no_life_loss',False):
                    (out/'prefix-audit.json').write_text(json.dumps({'coins':prefix_coins,'deaths':prefix_deaths,'no_life_loss':False}))
                    e.close();raise RuntimeError('Power-on prefix already contains a death; one-life route rejected')
            if i%12000==0:print(json.dumps({'warming_poweron_frames':i}),flush=True)
        prefix_audit={'frames':i,'coins':prefix_coins,'initial_lives':prefix_life,'deaths':prefix_deaths,'no_life_loss':not prefix_deaths}
        (out/'prefix-audit.json').write_text(json.dumps(prefix_audit,indent=2))
        if getattr(a,'expect_prefix_ram',None):
            equal=e.ram()==Path(a.expect_prefix_ram).read_bytes()
            prefix_audit['ram_equal']=equal
            (out/'prefix-audit.json').write_text(json.dumps(prefix_audit,indent=2))
            if not equal:e.close();raise RuntimeError('Continuous prefix RAM differs from reference; training rejected')
        initial.write_bytes(e.save())
    else:
        initial.write_bytes(Path(a.state).read_bytes())
        e.restore(initial.read_bytes())
    c=json.loads(a.config);samples=[];trace=[];start=time.perf_counter();items=Items();navigator=Navigator(c)
    tree=None
    if c.get('behavior_tree'):
        from kovsh_behavior import BehaviorTree
        tree=BehaviorTree(c['behavior_tree'],c.get('boss_slot'))
        c['mpc']=False
    worker=None;connection=None;pool=None;failed=False
    if c.get('mpc'):
        import multiprocessing
        if c.get('workers',1)>1:
            pool=multiprocessing.Pool(min(6,c['workers']),initializer=init_candidate_core)
        else:
            connection,child=multiprocessing.Pipe()
            worker=multiprocessing.Process(target=planner_worker,args=(child,),daemon=True);worker.start();child.close()
    before=observe(e.ram())
    manifest=dict(game='kovsh',scope='checkpoint_practice',full_game_clear_verified=False,
                  core_path=str(e.core_path.resolve()),core_sha256=sha(e.core_path),rom_sha256=sha(ROM),state_sha256=sha(initial),
                  source_sha256=sha(__file__),frontend_sha256=sha(ROOT/'emulator.py'),config=c)
    manifest.update(headless=bool(getattr(a,'headless',False)),no_life_loss=bool(getattr(a,'no_life_loss',False)))
    if prefix_path:
        manifest.update(scope='continuous_poweron_policy',start='poweron',
                        prefix_sha256=sha(out/'poweron-prefix.jsonl'))
    if tree or c.get('behavior_forest'):
        behavior=ROOT/'kovsh_behavior.py'
        manifest['behavior_sha256']=sha(behavior)
        (out/'behavior.py').write_bytes(behavior.read_bytes())
    if c.get('combat_rules'):
        combat_source=ROOT/'kovsh_combat.py'
        manifest['combat_sha256']=sha(combat_source)
        (out/'combat.py').write_bytes(combat_source.read_bytes())
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    (OUT/'active-training.json').write_text(json.dumps({'directory':str(out.resolve())}))
    try:
        zero=0;pending=[];consumptions=[];last_d=-1000;boss_slots=set();boss_chapter=before['chapter'];visited={};was_navigation=False;room_transitions=[];forecast_frames=0;forecast_rollouts=0
        for f in range(a.frames):
            o=observe(e.ram_view());keys=tree.tick(o,f) if tree else action(o,f,c)
            threats=[x for x in o['enemies'] if not (o['chapter']==0 and x['hp']==424)]
            nav_keys=navigator.choose(o,f,None if getattr(a,'headless',False) else e.picture()) if c.get('vision_navigation') and (not tree or not threats) else None
            navigation_mpc=c.get('navigation_mpc') and o['chapter']>=c.get('navigation_from',2) and not threats
            if was_navigation and threats:pending=[]
            was_navigation=bool(navigation_mpc)
            if c.get('bamboo_gate') and o['chapter']==3 and o.get('room_raw',0)==0 and not threats and 1400<o['x']<1740:
                navigation_mpc=False
            if navigation_mpc:
                nav_keys=None
                if f%30==0:
                    cell=f"{o['x']//24},{o['y']//24}";visited[cell]=visited.get(cell,0)+1
            if o['chapter']!=boss_chapter:boss_slots=set();boss_chapter=o['chapter']
            boss_slots.intersection_update(x['slot'] for x in threats)
            boss_slots.update(x['slot'] for x in threats if x['hp']>60)
            prefix=c.get('prefix_inputs',[])
            use_mpc=f>=len(prefix) and c.get('mpc') and o['hp']>0 and (threats or navigation_mpc) and nav_keys is None and (not c.get('boss_only') or boss_slots)
            if use_mpc:
                if not pending:
                    planning={**c,'horizon':180 if boss_slots else 90,'commit':60 if boss_slots else 90} if c.get('adaptive') else dict(c)
                    planning['focus_slots']=list(boss_slots)
                    planning.pop('prefix_inputs',None)
                    if c.get('deadline_survival'):
                        planning['hp_weight']=100 if o['hp']<24 else 50 if o['time_remaining']<25 else 60
                    if c.get('health_budget'):
                        planning['hp_weight']=8 if o['hp']>=40 else 24 if o['hp']>=24 else 100
                    if c.get('adaptive_commit') and threats:
                        nearest=min(abs(x['x']-o['x'])+3*abs(x['ground_y']-o['ground_y']) for x in threats)
                        close_weak=any(x['hp']<=16 and abs(x['x']-o['x'])<85 and abs(x['ground_y']-o['ground_y'])<16 and x['height']>=-8 for x in threats)
                        planning['commit']=15 if close_weak else 60 if nearest>160 else 30
                        if c.get('recovery_commit') and o.get('actor_code') in (1,2):
                            planning['commit']=max(30,planning['commit'])
                    if navigation_mpc:planning.update(horizon=180,commit=60,visited=visited)
                    state=e.save()
                    if pool:
                        choices=plan_choices(o,planning)
                        results=pool.map_async(candidate_task,[(state,o,f,planning,x) for x in choices]).get(180)
                        forecast_frames+=sum(r[2] for r in results);forecast_rollouts+=len(results)
                        selected=max(range(len(results)),key=lambda i:results[i][0])
                        pending=results[selected][1]
                        with (out/'decision-events.jsonl').open('a') as audit:
                            audit.write(json.dumps({'frame':f,'tactic':choices[selected].get('tactic',choices[selected].get('behavior_tree','legacy')),
                                                    'predicted_value':results[selected][0],'hp':o['hp'],'timer':o['time_remaining'],
                                                    'observation':o,'forecast_native_frames':forecast_frames})+'\n')
                    else:
                        connection.send((state,o,f,planning))
                        if not connection.poll(180):raise RuntimeError('Planner timed out')
                        pending=connection.recv()
                keys=pending.pop(0)
            else:pending=[]
            if nav_keys is not None:
                keys=[k for k in nav_keys if k!='attack' or f%4<2];pending=[]
            if c.get('items'):
                item_keys=items.choose(o,f)
                if item_keys is not None:keys=item_keys
            if f<len(prefix):keys=prefix[f]
            if 'd' in keys:last_d=f
            e.step(keys);trace.append(dict(frame=f+1,buttons=keys))
            after=observe(e.ram_view());zero=zero+1 if after['lives']==0 else 0
            room_changed=after['chapter']!=o['chapter'] or (o['x']-after['x']>600 and after['time_remaining']-o['time_remaining']>15)
            if room_changed:room_transitions.append(dict(frame=f+1,before=o,after=after))
            if after['lives']==o['lives'] and after['chapter']==o['chapter']:
                for item,count in o['inventory'].items():
                    remaining=after['inventory'].get(item,0)
                    if remaining<count and f-last_d<120:
                        consumptions.append(dict(frame=f+1,item_id=item,before=count,after=remaining,status='inventory_decrease_after_D'))
            if f%30==29:
                if not getattr(a,'headless',False):publish(out/'live.jpg',e.jpeg())
                live=dict(frame=f+1,observation=after,buttons=keys,seconds=time.perf_counter()-start,config=c,
                          item_events=[dict(item_id=x['item_id'],status='consumed_unconfirmed_effect',frame=x['frame']) for x in consumptions[-5:]],
                          forecast_native_frames=forecast_frames if pool else None,forecast_rollouts=forecast_rollouts if pool else None)
                publish(out/'live.json',json.dumps(live).encode())
            if f%600==599:
                samples.append(dict(frame=f+1,**after))
                if not getattr(a,'headless',False):e.picture().save(out/f'frame-{f+1:06d}.png')
                (out/f'frame-{f+1:06d}.ram').write_bytes(e.ram())
                (out/f'frame-{f+1:06d}.state').write_bytes(e.save())
                (out/'status.json').write_text(json.dumps(samples[-1]))
                with (out/'inputs.partial.jsonl').open('a',encoding='utf-8') as audit:
                    audit.write(''.join(json.dumps(row)+'\n' for row in trace[-600:]))
            if zero>300:break
            if getattr(a,'no_life_loss',False) and before['hp']>0 and (after['hp']==0 or after['lives']<before['lives']):break
            if getattr(a,'stop_room_exit',False) and room_changed:break
            if getattr(a,'stop_chapter_exit',False) and after['chapter']!=before['chapter']:break
            if f%60==59 and (out/'stop.json').exists():break
        if not getattr(a,'headless',False):e.picture().save(out/'final.png')
        (out/'final.state').write_bytes(e.save())
        (out/'final.ram').write_bytes(e.ram())
        (out/'inputs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in trace))
        (out/'samples.json').write_text(json.dumps(samples,indent=2))
        (out/'item-events.json').write_text(json.dumps(items.events,indent=2))
        (out/'item-consumptions.json').write_text(json.dumps(consumptions,indent=2))
        (out/'navigation-events.json').write_text(json.dumps(navigator.events,indent=2))
        if tree:(out/'behavior-events.json').write_text(json.dumps(tree.events,indent=2))
        termination='stop_request' if (out/'stop.json').exists() else 'life_lost' if after['hp']==0 or after['lives']<before['lives'] else 'chapter_exit' if getattr(a,'stop_chapter_exit',False) and after['chapter']!=before['chapter'] else 'room_exit' if getattr(a,'stop_room_exit',False) and room_transitions else 'frame_budget'
        result=dict(config=c,before=before,after=after,frames=len(trace),seconds=time.perf_counter()-start,expected=e.fingerprint(),full_game_clear_verified=False,termination=termination,room_transitions=room_transitions,
                    forecast_native_frames=forecast_frames if pool else None,forecast_rollouts=forecast_rollouts if pool else None,
                    video_frames_copied=0 if getattr(a,'headless',False) else None)
        (out/'result.json').write_text(json.dumps(result,indent=2))
    except BaseException as exc:
        failed=True
        (out/'failure.json').write_text(json.dumps({'error':repr(exc),'frames_recorded':len(trace)}))
        (out/'inputs.interrupted.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in trace))
        raise
    finally:
        e.close()
        if pool:
            pool.terminate() if failed else pool.close()
            pool.join()
        if worker:
            connection.send(None);worker.join(10)
            if worker.is_alive():worker.terminate();worker.join()
            connection.close()
    subprocess.run([sys.executable,__file__,'--replay',str(out)],check=True)
    result['replay_equal']=result['expected']==json.loads((out/'replay-fingerprint.json').read_text())
    result['trajectory_equal']=json.loads((out/'replay-trajectory.json').read_text())['all_equal']
    (out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)

def replay(folder):
    p=Path(folder);m=json.loads((p/'manifest.json').read_text());e=Emulator(ROM,core=Path(m.get('core_path',CORE)),deterministic=True,headless=m.get('headless',False))
    assert sha(p/'source.py')==m['source_sha256'],'Recorded policy source changed'
    import importlib.util
    spec=importlib.util.spec_from_file_location('recorded_policy',p/'source.py')
    frozen=importlib.util.module_from_spec(spec);spec.loader.exec_module(frozen)
    samples={r['frame']:r for r in json.loads((p/'samples.json').read_text())};checks=[]
    try:
        assert sha(ROM)==m['rom_sha256'] and sha(e.core_path)==m['core_sha256'] and sha(p/'initial.state')==m['state_sha256']
        if m.get('start')=='poweron':
            assert sha(p/'poweron-prefix.jsonl')==m['prefix_sha256']
            for line in (p/'poweron-prefix.jsonl').read_text().splitlines():
                e.step(json.loads(line)['buttons'])
        else:
            e.restore((p/'initial.state').read_bytes())
        for i,line in enumerate((p/'inputs.jsonl').read_text().splitlines()):
            row=json.loads(line);assert row['frame']==i+1;e.step(row['buttons'])
            if i+1 in samples:
                from PIL import Image
                expected=samples[i+1];actual=frozen.observe(e.ram())
                comparable={k:v for k,v in expected.items() if k!='frame'}
                checks.append(dict(frame=i+1,observation_equal=all(actual.get(k)==v for k,v in comparable.items()),
                                   ram_equal=e.ram()==(p/f'frame-{i+1:06d}.ram').read_bytes(),
                                   video_equal=None if m.get('headless') else e.picture().tobytes()==Image.open(p/f'frame-{i+1:06d}.png').convert('RGB').tobytes()))
        # Short policies still have a terminal RAM/state check. No 600-frame
        # sample is expected for a one-frame cold-prefix validation.
        checks.append(dict(frame=i+1,terminal=True,
                           observation_equal=frozen.observe(e.ram())==frozen.observe((p/'final.ram').read_bytes()),
                           ram_equal=e.ram()==(p/'final.ram').read_bytes(),
                           state_equal=e.save()==(p/'final.state').read_bytes(),video_equal=None))
        (p/'replay-fingerprint.json').write_text(json.dumps(e.fingerprint(),indent=2))
        (p/'replay-final.ram').write_bytes(e.ram())
        (p/'replay-final.state').write_bytes(e.save())
        if not m.get('headless'):e.picture().save(p/'replay-final.png')
        (p/'replay-trajectory.json').write_text(json.dumps(dict(checks=checks,all_equal=bool(checks) and all(x['observation_equal'] and x['ram_equal'] and x.get('state_equal',True) and x['video_equal'] is not False for x in checks),replay_frontend_sha256=sha(ROOT/'emulator.py')),indent=2))
    finally:e.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bootstrap',action='store_true');p.add_argument('--replay')
    p.add_argument('--state',default=str(OUT/'initial.state'));p.add_argument('--frames',type=int,default=24000)
    p.add_argument('--core',type=Path,default=CORE,help='KOVSH-only core; saved in the run manifest and inherited by forecast workers')
    p.add_argument('--poweron-prefix',help='Replay this input trace from boot before policy execution; never restore the scoring instance')
    p.add_argument('--headless',action='store_true',help='Disable video output and all image capture')
    p.add_argument('--no-life-loss',action='store_true',help='Stop on any death or life decrement')
    p.add_argument('--stop-room-exit',action='store_true',help='Stop at an observed chapter change or position-wrap with timer reset')
    p.add_argument('--stop-chapter-exit',action='store_true',help='Continue through room changes and stop when chapter advances')
    p.add_argument('--expect-prefix-ram',help='Require an exact RAM match before continuing the power-on route')
    p.add_argument('--config',default='{"period":8,"distance":40,"align":8,"jump":0,"sweep":true}')
    p.add_argument('--output',default=str(OUT/time.strftime('trial-%Y%m%d-%H%M%S')))
    a=p.parse_args()
    CORE=a.core.resolve();os.environ['KOVSH_CORE']=str(CORE)
    if a.bootstrap:bootstrap()
    elif a.replay:replay(a.replay)
    else:run(a)
