"""JSON behavior tree; ordinary controls only, original route semantics preserved."""
import json
from bisect import bisect_right
from pathlib import Path
from behavior_tree import Node, Result
from orlegend import action
from orlegend_survival import Combat

class Controller:
    def __init__(self, spec):
        self.spec = spec
        self.config = spec['parameters']
        self.scene = None
        self.age = self.phase = 0
        self.events = []
        self.cooldown = 0
        self.evade_cooldown = 0
        self.super_cooldown = 0
        self.charge_cooldown = 0
        self.last_action = None
        self.navigation = {}
        self.boss_slots = set()
        self.experimental_combat = Combat()
        self.threat_cooldowns = {}
        self.actor_positions = {}
        self.actor_velocities = {}
        self.input_plans = {}
        conditions = {'route': self.route_guard, 'crowd_fire': self.fire_guard, 'boss_close': self.boss_close,'charge_ready':self.charge_ready,'super_ready':self.super_ready,'item_ready':self.item_ready,'combat_phase':self.combat_phase,'plan_ready':self.plan_ready}
        actions = {name: getattr(self, name) for name in (
            'statue','rat_exit','tree','maze_exit','spider','cave','return_left',
            'maze_waypoints','door','bridge','plain_exit','nav_y','combat','use_fire','evade_vertical','charge_meter','super_command','use_item','select_item','aimed_item','input_plan')}
        self.root = Node(spec['tree'], conditions, actions)

    def choose(self, o, frame):
        if o['stage_raw'] != self.scene:
            self.scene, self.age, self.phase = o['stage_raw'], 0, 0
            self.root.halt()
            self.navigation.clear()
            self.boss_slots.clear()
            self.experimental_combat.target=self.experimental_combat.face=None
            self.actor_positions.clear();self.actor_velocities.clear()
        self.age += 1
        self.boss_slots.update(e['slot'] for e in o['enemies'] if e['hp']>=100)
        self.actor_velocities={e['slot']:(e['x']-self.actor_positions.get(e['slot'],(e['x'],e['y']))[0],e['y']-self.actor_positions.get(e['slot'],(e['x'],e['y']))[1]) for e in o['enemies']}
        self.actor_positions={e['slot']:(e['x'],e['y']) for e in o['enemies']}
        c = {**self.config, **self.config.get('scenes', {}).get(str(self.scene), {})}
        ctx = {'o': o, 'frame': frame, 'c': c}
        result = self.root.tick(ctx)
        self.last_action = result.action
        if result.status == 'FAILURE':
            raise RuntimeError('Tree has no applicable input action')
        return result.buttons

    def route_guard(self, x, p):
        o, c = x['o'], x['c'];s = o['stage_raw'];es = o['enemies'];name = p['name']
        guards = {
            'statue': lambda: s == 2 and self.config.get('push_statue', True),
            'rat_exit': lambda: s == 1538 and not es,
            'tree': lambda: s == 1281 and o.get('tree_hits',16)<16 and o['x']>600,
            'maze_exit': lambda: s == 1283 and not es,
            'spider': lambda: s == 1028 and c.get('spider_route',True) and len(es)==1 and es[0]['slot']==0 and es[0]['y']<130,
            'cave': lambda: s == 257 and self.config.get('cave_escape',True) and o['x']<700,
            'return_left': lambda: s == 514 and not es,
            'maze_waypoints': lambda: s == 513 and not es,
            'door': lambda: s == 256 and not es and o['x']>c.get('gate_start',1900),
            'bridge': lambda: s == 1793 and not es,
            'plain_exit': lambda: s in (772,1537) and not es,
            'nav_y': lambda: not es and 'nav_y' in c,
        }
        return guards[name]()

    @staticmethod
    def output(keys):return Result('SUCCESS',keys)
    def plan_ready(self,x,p):
        index=x['frame']-p['start_frame'] if 'start_frame' in p else self.age-1
        return x['o']['stage_raw'] in p['scenes'] and 0<=index<p['frames']
    def input_plan(self,x,m,p):
        index=x['frame']-p['start_frame'] if 'start_frame' in p else self.age-1
        if id(p) not in self.input_plans:
            end=0;ends=[]
            for run in p['runs']:
                if run['frames']<=0:raise ValueError('Input plan runs must have positive duration')
                end+=run['frames'];ends.append(end)
            self.input_plans[id(p)]=ends
        offset=bisect_right(self.input_plans[id(p)],index)
        if not 0<=offset<len(p['runs']):raise RuntimeError('Input plan duration does not match its guard')
        return self.output(p['runs'][offset]['buttons'])
    def statue(self,x,m,p):
        o=x['o']
        if self.phase==0:
            if abs(o['x']-200)<=5:self.phase=1
            else:return self.output(['left' if o['x']>200 else 'right'])
        if self.phase==1:
            if o['y']<=121:self.phase=2
            else:return self.output(['up'])
        return self.output(['right'])
    def rat_exit(self,x,m,p):return self.output(['left']+(['up'] if x['o']['y']>175 else []))
    def tree(self,x,m,p):
        o=x['o'];t=o['tree']
        return self.output(action({**o,'enemies':[{'slot':-1,'x':t[0],'y':t[1]+10,'hp':16-o['tree_hits']}]},x['frame'],{**x['c'],'distance':36,'align':5,'jump':0,'rush':0}))
    def maze_exit(self,x,m,p):
        o=x['o'];keys=[]
        if abs(o['x']-256)>3:keys.append('left' if o['x']>256 else 'right')
        if o['y']>116:keys.append('up')
        return self.output(keys)
    def spider(self,x,m,p):
        o=x['o'];f=x['frame'];target=x['c'].get('spider_x',1900)
        if o['x']<target-5:return self.output(['right'])
        if o['y']>125:return self.output(['up'])
        return self.output((['left'] if f%12==0 else [])+(['attack'] if f%4<2 else []))
    def cave(self,x,m,p):
        o=x['o'];f=x['frame'];c=x['c']
        if c.get('cave_clock')=='local':
            self.navigation.setdefault('start',f);f-=self.navigation['start']
        if c.get('cave_mode')=='combat':return self.combat(x,m,p)
        if c.get('cave_mode')=='adaptive':
            n=self.navigation;position=(o['x'],o['y']);previous=n.get('position');n['position']=position
            stalled=(position==previous) if c.get('cave_stall_axis','xy')=='xy' else (previous is not None and o['y']==previous[1])
            n['stalled']=n.get('stalled',0)+1 if stalled else 0
            if n['stalled']>=c.get('cave_stall',30):
                n['direction']='left' if n.get('direction','right')=='right' else 'right';n['stalled']=0
                self.events.append({'frame':f,'event':'cave_turn','x':o['x'],'y':o['y'],'direction':n['direction']})
            keys=['down',n.get('direction','right')] if o['y']<430 else ['right']
        elif c.get('cave_mode')=='dash':
            if o['y']<c.get('cave_dash_y',430):keys=['down'] if f%16 not in (2,3) else []
            else:keys=['right'] if f%16 not in (2,3) else []
        elif c.get('cave_mode')=='points':
            points=c['cave_points'];tx,ty=points[min(self.phase,len(points)-1)]
            if abs(o['x']-tx)<8 and abs(o['y']-ty)<8 and self.phase<len(points)-1:
                self.phase+=1;tx,ty=points[self.phase]
            keys=[]
            if c.get('cave_axis')=='x' and abs(o['x']-tx)>4:keys=['right' if o['x']<tx else 'left']
            elif abs(o['y']-ty)>4:keys=['down' if o['y']<ty else 'up']
            elif abs(o['x']-tx)>4:keys=['right' if o['x']<tx else 'left']
        elif c.get('cave_mode')=='right':keys=['right']
        elif c.get('cave_mode')=='down':keys=['down']
        elif c.get('cave_mode')=='downleft':keys=['down','left']
        elif c.get('cave_mode')=='slope':keys=['down','left'] if o['y']<330 else ['down','right'] if o['y']<430 else ['right']
        elif c.get('cave_mode')=='zigzag':
            keys=['down','right'] if o['y']<c.get('cave_turn_y',225) else ['down','left'] if o['y']<330 else ['down','right'] if o['y']<430 else ['right']
        elif c.get('cave_mode')=='waypoint':
            tx,ty=c.get('cave_target',[650,430]);keys=[]
            if abs(o['x']-tx)>4:keys.append('right' if o['x']<tx else 'left')
            if abs(o['y']-ty)>4:keys.append('down' if o['y']<ty else 'up')
        elif o['y']<330:keys=['down','right']
        elif o['x']<350:keys=['right']
        elif o['y']<430:keys=['down','right']
        else:keys=['right']
        dash=c.get('cave_dash',0)
        if dash and f%dash in (0,1,4,5):return self.output([])
        if not dash and f%60==2:return self.output([])
        attack=c.get('cave_attack',0);jump=c.get('cave_jump',90)
        if attack and f%attack<attack//2:keys.append('attack')
        if jump and f%jump<2:keys=[k for k in keys if k!='attack']+['jump']
        return self.output(keys)
    def return_left(self,x,m,p):
        o=x['o'];y=220 if o['x']>170 else 90;keys=['left']
        if abs(o['y']-y)>3:keys.append('up' if o['y']>y else 'down')
        return self.output(keys)
    def maze_waypoints(self,x,m,p):
        o=x['o'];points=[(900,250),(900,160),(995,115)]
        if o['x']<850:self.phase=0
        tx,ty=points[min(self.phase,2)]
        if abs(o['x']-tx)<8 and abs(o['y']-ty)<8 and self.phase<2:self.phase+=1
        keys=[]
        if abs(o['x']-tx)>3:keys.append('left' if o['x']>tx else 'right')
        if abs(o['y']-ty)>3:keys.append('up' if o['y']>ty else 'down')
        if self.phase==0 and x['frame']%4<2:keys.append('attack')
        return self.output(keys)
    def door(self,x,m,p):
        o=x['o'];c=x['c'];tx=c.get('gate_x',1960 if o.get('door_open') else 1980);ty=c.get('gate_y',125 if o.get('door_open') else 146);keys=[]
        if abs(o['x']-tx)>3:keys.append('left' if o['x']>tx else 'right')
        if abs(o['y']-ty)>3:keys.append('up' if o['y']>ty else 'down')
        if not o.get('door_open') and abs(o['x']-tx)<=4:
            if x['frame']%12==0:keys.append('left')
            if self.phase==0 and x['frame']%4<2:keys.append('attack')
        return self.output(keys)
    def bridge(self,x,m,p):
        o=x['o'];y=x['c'].get('bridge_y',124 if 900<=o['x']<1075 else 155)
        return self.output(action(o,x['frame'],{**x['c'],'nav_y':y}) if o['enemies'] else self.navigate(o,y))
    def plain_exit(self,x,m,p):return self.output(self.navigate(x['o'],160))
    def nav_y(self,x,m,p):
        o=x['o'];c=x['c'];f=x['frame'];keys=self.navigate(o,c['nav_y']);period=c.get('nav_attack',0)
        if c.get('gate_detour') and c.get('gate_detour_start',1500)<=o['x']<c.get('gate_detour_end',1800):keys=['down','right']
        if c.get('nav_recover'):
            n=self.navigation;position=(o['x'],o['y']);n['nav_stalled']=n.get('nav_stalled',0)+1 if position==n.get('nav_position') else 0;n['nav_position']=position
            if n['nav_stalled']>=c.get('nav_stall',60):
                n['nav_recover_until']=f+c.get('nav_recover_hold',30);n['nav_stalled']=0
                self.events.append({'frame':f,'event':'nav_backoff','x':o['x'],'y':o['y']})
            if f<n.get('nav_recover_until',-1):keys=['left']
        if period and x['frame']%period<period//2:keys.append('attack')
        return self.output(keys)
    @staticmethod
    def navigate(o,y):return ['right']+(['up' if o['y']>y else 'down'] if abs(o['y']-y)>3 else [])
    def combat(self,x,m,p):
        c={**x['c'],**p};o=x['o']
        if c.get('reserve_meter') and o['resources']['meter']==96:c.update(rush=0,jump=0)
        if c.get('focus_known_boss'):
            targets=[e for e in o['enemies'] if e['slot'] in self.boss_slots]
            if targets:o={**o,'enemies':targets}
        if c.get('combat','legacy')!='legacy':
            if c.get('boss_focus'):
                targets=[e for e in o['enemies'] if e['slot'] in self.boss_slots]
                if targets:o={**o,'enemies':targets}
            return self.output(self.experimental_combat(o,x['frame'],c))
        return self.output(action(o,x['frame'],c))

    def combat_phase(self,x,p):
        o=x['o'];return o['stage_raw'] in p['scenes'] and any(e['hp']>=p.get('min_hp',24) and (not p.get('known_boss') or e['slot'] in self.boss_slots) and abs(e['x']-o['x'])<p.get('dx',10000) for e in o['enemies'])

    def charge_ready(self,x,p):
        o=x['o']
        if o['stage_raw'] not in p['scenes'] or o['resources']['meter']>=96 or x['frame']<self.charge_cooldown:return False
        if o['y']<p.get('min_y',0):return False
        if not p.get('min_x',-10000)<=o['x']<=p.get('max_x',10000):return False
        if p.get('require_boss') and not any(e['hp']>=100 for e in o['enemies']):return False
        return o['player_state']==2 and not any(e.get('state') not in p.get('ignore_enemy_states',[]) and abs(e['x']-o['x'])<p.get('safe_dx',0) and abs(e['y']-o['y'])<p.get('safe_dy',80) for e in o['enemies'])

    def charge_meter(self,x,m,p):
        o=x['o'];f=x['frame']
        if not m:m['start']=f
        if o['resources']['meter']>=96:
            self.events.append({'frame':f,'event':'charge_full','hp':o['hp'],'scene':o['stage_raw']});return self.output([])
        if p.get('abort_on_threat') and any(e.get('state') not in p.get('ignore_enemy_states',[]) and abs(e['x']-o['x'])<p['safe_dx'] and abs(e['y']-o['y'])<p['safe_dy'] for e in o['enemies']):
            self.charge_cooldown=f+p.get('cooldown',15);return self.output([])
        if f-m['start']>=p.get('max_hold',10000):
            self.events.append({'frame':f,'event':'charge_burst','meter':o['resources']['meter'],'hp':o['hp'],'scene':o['stage_raw']});self.charge_cooldown=f+p.get('cooldown',15);return self.output([])
        if f-m['start']>=p.get('timeout',600):
            self.charge_cooldown=f+120;return Result('FAILURE',[])
        return Result('RUNNING',['attack','jump','c'])

    def super_ready(self,x,p):
        o=x['o']
        return o['stage_raw'] in p['scenes'] and o['resources']['meter']==96 and o['player_state']==2 and (not p.get('ground_only') or not o['air_mask']) and x['frame']>=self.super_cooldown and any(e['hp']>=p.get('min_hp',40) and e.get('state') not in p.get('exclude_enemy_states',[]) and (not p.get('known_boss') or e['slot'] in self.boss_slots) and abs(e['x']-o['x'])<p['dx'] and abs(e['y']-o['y'])<p['dy'] for e in o['enemies'])

    def super_command(self,x,m,p):
        o=x['o'];f=x['frame']
        if not m:
            targets=([e for e in o['enemies'] if e['slot'] in self.boss_slots] or o['enemies']) if p.get('known_boss') else ([e for e in o['enemies'] if e['hp']>=80] or o['enemies']) if p.get('boss_focus') else o['enemies']
            targets=[e for e in targets if e.get('state') not in p.get('exclude_enemy_states',[])]
            if not targets:return Result('FAILURE',[])
            target=min(targets,key=lambda e:abs(e['x']-o['x'])+3*abs(e['y']-o['y']));forward='right' if target['x']>=o['x'] else 'left';back='left' if forward=='right' else 'right'
            # Menu freezes facing while the ROM command parser accepts the sequence.
            turn=[] if p.get('fast_prepare') and o.get('player_facing')==forward else [[forward]]*p.get('turn_hold',6)+[[]]*p.get('turn_release',6)
            recipe=turn+[['c']]*2+[[]]*p.get('menu_wait',8)
            for keys in [[back],[back,'down'],['down'],[forward,'down'],[forward],[back],[forward],['attack']]:recipe += [keys]*p.get('hold',4)
            m.update(start=f,recipe=recipe,confirmed=False)
        if o['player_state']==6 and o['player_move']==35 and not m['confirmed']:
            m['confirmed']=True;self.events.append({'frame':f,'event':'super_confirmed','hp':o['hp'],'scene':o['stage_raw']})
        age=f-m['start']
        if age<len(m['recipe']):return Result('RUNNING',m['recipe'][age])
        if o['player_state']==6 and age<len(m['recipe'])+360:return Result('RUNNING',[])
        if age<len(m['recipe'])+12:return Result('RUNNING',[])
        self.events.append({'frame':f,'event':'super_finished' if m['confirmed'] else 'super_failed','scene':o['stage_raw']});self.super_cooldown=f+p.get('cooldown',30)
        # A completed special closes the menu itself; failed commands need C to close it.
        return self.output([] if m['confirmed'] else ['c'])

    def boss_close(self,x,p):
        o=x['o']
        cooldown=self.threat_cooldowns.get(p['channel'],0) if 'channel' in p else self.evade_cooldown
        return o['stage_raw'] in p['scenes'] and x['frame']>=cooldown and any(p['min_hp']<=e['hp']<=p.get('max_hp',4095) and (not p.get('known_boss') or e['slot'] in self.boss_slots) and ('enemy_states' not in p or e.get('state') in p['enemy_states']) and ('enemy_moves' not in p or e.get('move') in p['enemy_moves']) and ('closing_speed' not in p or p['closing_speed']<=abs(self.actor_velocities.get(e['slot'],(0,0))[0])<=32 and self.actor_velocities.get(e['slot'],(0,0))[0]*(e['x']-o['x'])<0) and abs(e['x']-o['x'])<p['dx'] and abs(e['y']-o['y'])<p['dy'] for e in o['enemies'])
    def evade_vertical(self,x,m,p):
        o=x['o'];f=x['frame']
        if not m:
            boss=min((e for e in o['enemies'] if e['hp']>=p.get('min_hp',100) and (not p.get('known_boss') or e['slot'] in self.boss_slots)),key=lambda e:abs(e['x']-o['x']))
            direction='down' if o['y']>=boss['y'] else 'up'
            target=max(p['min_y'],min(p['max_y'],o['y']+(p['displacement'] if direction=='down' else -p['displacement'])))
            m.update(start=f,target=target)
        if f-m['start']>=p['hold'] or abs(o['y']-m['target'])<3:
            if 'channel' in p:self.threat_cooldowns[p['channel']]=f+p['cooldown']
            else:self.evade_cooldown=f+p['cooldown']
            return self.output([])
        return Result('RUNNING',['down' if o['y']<m['target'] else 'up'])

    def fire_guard(self,x,p):
        o=x['o'];r=o['resources'];inv=r['inventory'];selected=r['selected']
        if o['stage_raw'] not in p['scenes'] or x['frame']<self.cooldown or not 0<=selected<len(inv):return False
        if r['meter']<p.get('min_meter',0):return False
        if 'allowed_player_states' in p and o.get('player_state') not in p['allowed_player_states']:return False
        if inv[selected]['id']!=15 or inv[selected]['count']<=p['reserve']:return False
        near=[e for e in o['enemies'] if e['hp']>=p.get('min_enemy_hp',0) and abs(e['x']-o['x'])<p['range_x'] and abs(e['y']-o['y'])<p['range_y']]
        return len(near)>=p['crowd'] and x['frame']>=p.get('min_frame',0)

    def item_ready(self,x,p):
        o=x['o'];r=o['resources'];inv=r['inventory'];index=r['selected']
        if o['stage_raw'] not in p['scenes'] or x['frame']<self.cooldown or o['player_state']!=2 or not 0<=index<len(inv):return False
        def usable(i):return i['id'] in p['ids'] and i['count']>p.get('reserves',{}).get(str(i['id']),0)
        available=any(usable(i) for i in inv) if p.get('choose') else usable(inv[index])
        return available and any(p.get('min_hp',1)<=e['hp']<=p.get('max_hp',4095) and (not p.get('known_boss') or e['slot'] in self.boss_slots) and (not p.get('ground_enemy') or not e.get('air_mask',0)) and ('allowed_enemy_states' not in p or e.get('state') in p['allowed_enemy_states']) and p.get('min_dx',0)<=abs(e['x']-o['x'])<p['dx'] and abs(e['y']-o['y'])<p['dy'] for e in o['enemies'])

    def select_item(self,x,m,p):
        o=x['o'];f=x['frame'];inv=o['resources']['inventory'];selected=o['resources']['selected']
        if not m:
            ident=next(ident for ident in p['ids'] if any(i['id']==ident and i['count']>p.get('reserves',{}).get(str(ident),0) for i in inv));target=next(i for i,v in enumerate(inv) if v['id']==ident)
            if selected==target and not (p.get('radial_select') and o['resources'].get('menu_open')):return self.use_item(x,m,p)
            m.update(id=ident,target=target,count=sum(i['count'] for i in inv if i['id']==ident),start=f,phase='open',phase_start=f)
            if p.get('radial_select') and o['resources'].get('menu_open'):m['phase']='select'
        if 'phase' not in m:return self.use_item(x,m,p)
        if f-m['start']>=150:
            self.events.append({'frame':f,'event':'item_selection_timeout','id':m['id'],'scene':o['stage_raw']});self.cooldown=f+90;return self.output(['c'])
        age=f-m['phase_start']
        if m['phase']=='open':
            if age<10:return Result('RUNNING',['c'] if age<2 else [])
            m.update(phase='select',phase_start=f);age=0
        if m['phase']=='select':
            if p.get('radial_select') and not o['resources'].get('menu_open'):
                m.update(phase='open',phase_start=f);return Result('RUNNING',['c'])
            if 0<=selected<len(inv) and inv[selected]['id']==m['id']:
                m.update(phase='confirm',phase_start=f);age=0
            else:
                if p.get('radial_select'):
                    # Menu directions address fixed slots; they do not rotate the cursor.
                    directions=[['up'],['left'],['down'],['right'],['up','left'],['down','left'],['down','right'],['up','right']]
                    if len(inv)==3:directions=[[['up'],['left'],['right']][m['target']]]
                    elif len(inv)==4:directions=[[['up'],['down'],['left'],['right']][m['target']]]
                    return Result('RUNNING',directions[(age//8)%len(directions)] if age%8<2 else [])
                direction='right' if p.get('short_select') and selected>m['target'] else 'left'
                return Result('RUNNING',[direction] if age%8<2 else [])
        if m['phase']=='confirm':
            if age<14:return Result('RUNNING',['attack'] if age<2 else [])
            self.events.append({'frame':f,'event':'item_selected','id':m['id'],'selected':selected,'scene':o['stage_raw']});m.pop('phase');m['start']=f
        return self.use_item(x,m,p)

    def aimed_item(self,x,m,p):
        o=x['o'];f=x['frame']
        if not m:m.update(start=f,prepare=True,item_memory={})
        if m['prepare']:
            targets=[v for v in o['enemies'] if v['hp']>=p.get('min_hp',40)]
            if not targets:return Result('FAILURE',[])
            target=max(targets,key=lambda v:v['hp']);face='right' if target['x']>=o['x'] else 'left';dy=target['y']-o['y']
            if f-m['start']>=p.get('prepare_timeout',180):self.cooldown=f+60;return Result('FAILURE',[])
            if abs(dy)>p.get('aim_y',14):return Result('RUNNING',['down' if dy>0 else 'up'])
            if o['player_facing']!=face:return Result('RUNNING',[face])
            if o['player_state']!=2 or o['air_mask']:return Result('RUNNING',[])
            m['prepare']=False
        return self.select_item(x,m['item_memory'],p)

    def use_item(self,x,m,p):
        o=x['o'];f=x['frame'];inv=o['resources']['inventory']
        if not m:
            item=inv[o['resources']['selected']];m.update(id=item['id'],count=sum(i['count'] for i in inv if i['id']==item['id']),start=f)
        count=sum(i['count'] for i in inv if i['id']==m['id'])
        if count<m['count']:
            self.events.append({'frame':f,'event':'item_consumed','id':m['id'],'before':m['count'],'after':count,'scene':o['stage_raw']});self.cooldown=f+p.get('cooldown',180);return self.output([])
        if f-m['start']>=p.get('timeout',45):
            self.events.append({'frame':f,'event':'item_timeout','id':m['id'],'scene':o['stage_raw']});self.cooldown=f+60;return Result('FAILURE',[])
        return Result('RUNNING',['d'] if (f-m['start'])%4<2 else [])
    def use_fire(self,x,m,p):
        o=x['o'];f=x['frame'];count=sum(i['count'] for i in o['resources']['inventory'] if i['id']==15)
        if not m:m.update(count=count,start=f)
        if count<m['count']:
            self.events.append({'frame':f,'event':'fire_consumed','before':m['count'],'after':count,'scene':o['stage_raw']});self.cooldown=f+p['cooldown'];return self.output([])
        if f-m['start']>=p['timeout']:
            self.events.append({'frame':f,'event':'fire_timeout','scene':o['stage_raw']});self.cooldown=f+p['cooldown'];return Result('FAILURE',[])
        return Result('RUNNING',['d'] if (f-m['start'])%4<2 else [])

def load(path):return json.loads(Path(path).read_text())
