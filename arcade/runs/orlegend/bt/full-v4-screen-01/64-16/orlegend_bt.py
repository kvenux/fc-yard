"""JSON behavior tree; ordinary controls only, original route semantics preserved."""
import json
from pathlib import Path
from behavior_tree import Node, Result
from orlegend import action

class Controller:
    def __init__(self, spec):
        self.spec = spec
        self.config = spec['parameters']
        self.scene = None
        self.age = self.phase = 0
        self.events = []
        self.cooldown = 0
        self.evade_cooldown = 0
        self.last_action = None
        conditions = {'route': self.route_guard, 'crowd_fire': self.fire_guard, 'boss_close': self.boss_close}
        actions = {name: getattr(self, name) for name in (
            'statue','rat_exit','tree','maze_exit','spider','cave','return_left',
            'maze_waypoints','door','bridge','plain_exit','nav_y','combat','use_fire','evade_vertical')}
        self.root = Node(spec['tree'], conditions, actions)

    def choose(self, o, frame):
        if o['stage_raw'] != self.scene:
            self.scene, self.age, self.phase = o['stage_raw'], 0, 0
            self.root.halt()
        self.age += 1
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
            'door': lambda: s == 256 and not es and o['x']>1900,
            'bridge': lambda: s == 1793 and not es,
            'plain_exit': lambda: s in (772,1537) and not es,
            'nav_y': lambda: not es and 'nav_y' in c,
        }
        return guards[name]()

    @staticmethod
    def output(keys):return Result('SUCCESS',keys)
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
        o=x['o'];f=x['frame']
        if o['y']<330:keys=['down','right']
        elif o['x']<350:keys=['right']
        elif o['y']<430:keys=['down','right']
        else:keys=['right']
        if f%60==2:return self.output([])
        if f%90<2:keys.append('jump')
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
        o=x['o'];tx=1960 if o.get('door_open') else 1980;ty=125 if o.get('door_open') else 146;keys=[]
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
    def nav_y(self,x,m,p):return self.output(self.navigate(x['o'],x['c']['nav_y']))
    @staticmethod
    def navigate(o,y):return ['right']+(['up' if o['y']>y else 'down'] if abs(o['y']-y)>3 else [])
    def combat(self,x,m,p):return self.output(action(x['o'],x['frame'],x['c']))

    def boss_close(self,x,p):
        o=x['o']
        return o['stage_raw'] in p['scenes'] and x['frame']>=self.evade_cooldown and any(e['hp']>=p['min_hp'] and abs(e['x']-o['x'])<p['dx'] and abs(e['y']-o['y'])<p['dy'] for e in o['enemies'])
    def evade_vertical(self,x,m,p):
        o=x['o'];f=x['frame']
        if not m:
            boss=min((e for e in o['enemies'] if e['hp']>=p.get('min_hp',100)),key=lambda e:abs(e['x']-o['x']))
            direction='down' if o['y']>=boss['y'] else 'up'
            target=max(p['min_y'],min(p['max_y'],o['y']+(p['displacement'] if direction=='down' else -p['displacement'])))
            m.update(start=f,target=target)
        if f-m['start']>=p['hold'] or abs(o['y']-m['target'])<3:
            self.evade_cooldown=f+p['cooldown'];return self.output([])
        return Result('RUNNING',['down' if o['y']<m['target'] else 'up'])

    def fire_guard(self,x,p):
        o=x['o'];r=o['resources'];inv=r['inventory'];selected=r['selected']
        if o['stage_raw'] not in p['scenes'] or x['frame']<self.cooldown or not 0<=selected<len(inv):return False
        if 'allowed_player_states' in p and o.get('player_state') not in p['allowed_player_states']:return False
        if inv[selected]['id']!=15 or inv[selected]['count']<=p['reserve']:return False
        near=[e for e in o['enemies'] if e['hp']>=p.get('min_enemy_hp',0) and abs(e['x']-o['x'])<p['range_x'] and abs(e['y']-o['y'])<p['range_y']]
        return len(near)>=p['crowd'] and x['frame']>=p.get('min_frame',0)
    def use_fire(self,x,m,p):
        o=x['o'];f=x['frame'];count=sum(i['count'] for i in o['resources']['inventory'] if i['id']==15)
        if not m:m.update(count=count,start=f)
        if count<m['count']:
            self.events.append({'frame':f,'event':'fire_consumed','before':m['count'],'after':count,'scene':o['stage_raw']});self.cooldown=f+p['cooldown'];return self.output([])
        if f-m['start']>=p['timeout']:
            self.events.append({'frame':f,'event':'fire_timeout','scene':o['stage_raw']});self.cooldown=f+p['cooldown'];return Result('FAILURE',[])
        return Result('RUNNING',['d'] if (f-m['start'])%4<2 else [])

def load(path):return json.loads(Path(path).read_text())
