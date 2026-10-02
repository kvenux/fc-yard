"""Deterministic, stateful KOVSH behavior trees using observed game state.

Motion/HP history are observable cues, not claims about decoded attack animations.
All output is ordinary arcade input. No randomness, coins, or continues.
"""
from collections import deque


STRATEGIES = {
    'pressure': '持续压制：同线贴近，普攻连击，击退后追击',
    'counter': '错线反击：避开迎面接近，沿相邻纵线靠近再切入',
    'flank': '绕背：贴身时跨过目标再转向攻击，受伤后纵向脱离',
    'adds_first': '先清杂兵：近身低血杂兵优先，随后集中首领',
    'isolate': '隔离首领：脱离两侧夹击，将首领与杂兵拉开',
    'jump_in': '跳入近身：远距离跳跃接近，落地后普攻连击',
    'combo_chase': '连招追击：普攻起手，命中后接方向指令，击退再追',
    'survival': '综合生存：受伤脱离、夹击脱身、清残血、反击首领',
    'formation_sweep': '扫线推进：接近和对齐时持续攻击，近身多人使用纵向范围指令',
}


def ground(entity):
    # Ground fields can be uninitialized at boot. Validate the coordinate identity.
    value = entity.get('ground_y', entity['y'])
    return value if value + entity.get('height', 0) == entity['y'] else entity['y']


class Selector:
    """Ordered guarded actions: first eligible branch owns this tick."""
    def __init__(self, branches):
        self.branches = branches

    def tick(self):
        for name, condition, action in self.branches:
            if condition():
                return name, action()
        raise RuntimeError('Behavior selector must have a fallback')


class BehaviorTree:
    def __init__(self, strategy='survival', boss_slot=None):
        if strategy not in STRATEGIES:
            raise ValueError(strategy)
        self.strategy, self.boss_slot = strategy, boss_slot
        self.previous = None
        self.last_hit = -1000
        self.last_item = -1000
        self.last_jump = -1000
        self.last_flank = -1000
        self.last_combo = -1000
        self.last_stall_escape = -1000
        self.last_special = -1000
        self.escape_until = -1
        self.escape_direction = 'up'
        self.combo = deque()
        self.events = []
        self.branch = None
        self.attack_started = None
        self.attack_hp = None
        self.hit_confirmed = False
        self.face = 'right'
        self.item_before = None
        self.item_sequence = deque()
        self.item_direct_failed = False
        self.item_attempts = 0
        self.selector = Selector([
            ('dead_wait', lambda: self.o['hp'] <= 0, lambda: []),
            ('hurt_escape', self.hurt_escape, self.evade),
            ('finish_escape_movement', lambda: self.f < self.escape_until, lambda: [self.escape_direction]),
            ('finish_item_sequence', lambda: bool(self.item_sequence), lambda: self.item_sequence.popleft()),
            ('escape_pincer', self.pincered, self.evade),
            ('navigate_exit', lambda: self.target is None, lambda: ['right']),
            ('sweep_formation', lambda: self.strategy=='formation_sweep', self.sweep_formation),
            ('use_aligned_item', self.item_ready, self.use_item),
            ('finish_hit_combo', self.combo_ready, lambda: self.combo.popleft()),
            ('avoid_airborne_contact', self.airborne_danger, self.evade),
            ('break_ineffective_attack', self.stalled_attack, self.reposition),
            ('approach_on_offset_lane', self.offset_approach, self.approach_offset),
            ('jump_into_range', self.jump_ready, self.jump_in),
            ('align_attack_lane', lambda: abs(self.dy) > 7, self.align),
            ('chase_knockback', lambda: abs(self.dx) > 30, self.chase),
            ('cross_to_back', self.flank_ready, self.flank),
            ('face_target', lambda: self.face != self.desired_face, self.turn),
            ('start_confirmed_combo', self.start_combo_ready, self.start_combo),
            ('close_range_special', self.special_ready, self.special),
            ('basic_attack', lambda: True, self.attack),
        ])

    def tick(self, observation, frame):
        self.o, self.f = observation, frame
        self.face=observation.get('facing',self.face)
        self.enemies = [e for e in observation['enemies']
                        if not (observation['chapter'] == 0 and e['slot'] == 1 and e['hp'] == 424)]
        if self.previous and observation['hp'] < self.previous['hp']:
            self.last_hit = frame
            self.combo.clear()
            self.attack_started = None
        if self.item_before is not None and frame - self.last_item > 75:
            consumed = {k: n-observation['inventory'].get(k, 0)
                        for k, n in self.item_before.items() if n > observation['inventory'].get(k, 0)}
            self.events.append({'frame': frame, 'item_consumed': consumed,
                                'confirmed_inventory_delta': bool(consumed)})
            if not consumed:self.item_direct_failed=True
            self.item_before = None
        self.target = self.choose_target()
        if self.target:
            self.dx = self.target['x'] - observation['x']
            self.dy = ground(self.target) - ground(observation)
            self.desired_face = 'right' if self.dx >= 0 else 'left'
            self.hit_confirmed = bool(self.attack_hp and self.attack_hp[0] == self.target['slot']
                                      and self.target['hp'] < self.attack_hp[1])
        else:
            self.dx = self.dy = 0
            self.combo.clear()
            self.attack_started = None
        branch, keys = self.selector.tick()
        if branch != self.branch:
            self.events.append({'frame': frame, 'branch': branch, 'hp': observation['hp'],
                                'target': self.target['slot'] if self.target else None})
            self.branch = branch
        if 'left' in keys: self.face = 'left'
        if 'right' in keys: self.face = 'right'
        self.previous = observation
        return keys

    def choose_target(self):
        if not self.enemies: return None
        distance = lambda e: abs(e['x']-self.o['x']) + 3*abs(ground(e)-ground(self.o))
        boss = next((e for e in self.enemies if e['slot'] == self.boss_slot), None)
        if boss is None:
            boss = max(self.enemies, key=lambda e: e['hp'])
        nearby = [e for e in self.enemies if e is not boss and distance(e) < 110]
        if self.strategy == 'adds_first' and nearby:
            return min(nearby, key=lambda e: (e['hp'], distance(e)))
        if self.strategy == 'survival':
            weak = [e for e in nearby if e['hp'] <= 16]
            if weak: return min(weak, key=distance)
        if self.strategy in ('pressure', 'counter', 'flank', 'isolate', 'jump_in', 'combo_chase', 'survival'):
            blockers = [e for e in nearby if distance(e) < 35 and abs(ground(e)-ground(self.o)) < 10]
            if blockers and distance(boss) > 90: return min(blockers, key=distance)
            return boss
        return min(self.enemies, key=distance)

    def sweep_formation(self):
        keys=[]
        if abs(self.dy)>8:keys.append('down' if self.dy>0 else 'up')
        if abs(self.dx)>32 or self.f%60==0:keys.append(self.desired_face)
        if self.f%4<2:keys.append('attack')
        close=[e for e in self.enemies if abs(e['x']-self.o['x'])<75 and abs(ground(e)-ground(self.o))<22]
        if len(close)>=2 and self.f%36<9:
            keys=([['down'],['up'],['attack']])[self.f%36//3]
        return keys

    def hurt_escape(self):
        return self.strategy != 'pressure' and self.f-self.last_hit < 18 and bool(self.enemies)

    def evade(self):
        if self.f < self.escape_until:return [self.escape_direction]
        y = ground(self.o)
        above = sum(e['hp'] for e in self.enemies if ground(e) < y)
        below = sum(e['hp'] for e in self.enemies if ground(e) >= y)
        self.escape_direction='up' if above < below else 'down'
        self.escape_until=self.f+18
        return [self.escape_direction]

    def pincered(self):
        if self.strategy not in ('isolate', 'survival'): return False
        close = [e for e in self.enemies if abs(e['x']-self.o['x']) < 55 and abs(ground(e)-ground(self.o)) < 13]
        return any(e['x'] < self.o['x'] for e in close) and any(e['x'] > self.o['x'] for e in close)

    def item_ready(self):
        return (self.target is not None and bool(self.o['inventory']) and self.f-self.last_item > 360
                and abs(self.dy) <= 8 and 40 <= abs(self.dx) <= 150
                and self.o['height'] == 0 and self.target.get('height', 0) == 0
                and (self.target['hp'] > 100 or len(self.enemies) >= 3 or self.o['time_remaining'] < 25))

    def use_item(self):
        self.last_item = self.f
        self.item_before = dict(self.o['inventory'])
        # Selected-item semantics are only partially decoded. Actual consumption is audited.
        self.item_attempts+=1
        if str(self.o['selected_item']) in self.o['inventory'] and not self.item_direct_failed:
            sequence = [[self.desired_face]]*2 + [[]]*33 + [['d']]*4 + [[]]*16
        else:
            direction=('up','right','down','left')[(self.item_attempts-1)%4]
            sequence = [[self.desired_face]] + [[]]*34 + [['c']]*4 + [[]]*16
            sequence += [[direction]]*4 + [[]]*11 + [['attack']]*4 + [[]]*21
            sequence += [[self.desired_face]]*4 + [[]] + [['d']]*4 + [[]]*16
        self.item_sequence.extend(sequence)
        return self.item_sequence.popleft()

    def combo_ready(self):
        if not self.combo: return False
        if self.target is None or abs(self.dy) > 18 or abs(self.dx) > 65:
            self.combo.clear()
            return False
        return True

    def stalled_attack(self):
        return (self.target is not None and self.attack_started is not None
                and self.f-self.attack_started >= 60 and not self.hit_confirmed
                and self.f-self.last_stall_escape > 120)

    def reposition(self):
        self.last_stall_escape = self.f
        direction = self.evade()
        self.combo.extend([direction+['jump']]*2 + [direction]*16)
        self.attack_started = None
        return self.combo.popleft()

    def airborne_danger(self):
        return (self.strategy in ('counter', 'isolate', 'survival') and self.target is not None
                and self.target.get('height', 0) < -15 and abs(self.dx) < 65 and abs(self.dy) < 15)

    def offset_approach(self):
        return (self.target is not None and self.strategy in ('counter', 'isolate', 'survival')
                and 55 < abs(self.dx) < 180 and abs(self.dy) < 20)

    def approach_offset(self):
        keys = [self.desired_face]
        # Commit to one side of the lane; don't oscillate at its center.
        if abs(self.dy) < 16: keys += ['up' if self.dy >= 0 else 'down']
        return keys

    def jump_ready(self):
        return (self.strategy == 'jump_in' and abs(self.dx) > 80 and abs(self.dy) < 15
                and self.o['height'] == 0 and self.f-self.last_jump > 90)

    def jump_in(self):
        self.last_jump = self.f
        return [self.desired_face, 'jump']

    def align(self):
        self.attack_started = None
        keys=['down' if self.dy > 0 else 'up'] + ([self.desired_face] if abs(self.dx) > 30 else [])
        if abs(self.dx)<85 and self.f%4<2:keys.append('attack')
        return keys

    def chase(self):
        self.attack_started = None
        return [self.desired_face] + (['attack'] if abs(self.dx) < 100 and self.f%4 < 2 else [])

    def flank_ready(self):
        return self.strategy == 'flank' and abs(self.dx) < 24 and self.f-self.last_flank > 120

    def flank(self):
        self.last_flank = self.f
        self.combo.extend([[self.desired_face]]*14 + [['left' if self.desired_face == 'right' else 'right']]*2)
        return self.combo.popleft()

    def turn(self):
        return [self.desired_face]

    def start_combo_ready(self):
        return (self.strategy == 'combo_chase' and self.hit_confirmed and self.attack_started is not None
                and self.f-self.attack_started >= 24 and self.f-self.last_combo > 90)

    def start_combo(self):
        self.last_combo = self.f
        back = 'left' if self.desired_face == 'right' else 'right'
        self.combo.extend([[back]]*3 + [[self.desired_face]]*3 + [['attack']]*3 + [[]]*6)
        self.attack_started = None
        return self.combo.popleft()

    def special_ready(self):
        return (self.target is not None and abs(self.dx) < 48 and abs(self.dy) <= 8
                and self.target.get('height',0) >= -8 and self.f-self.last_special >= 60
                and self.attack_started is not None and self.f-self.attack_started >= 24)

    def special(self):
        self.last_special=self.f
        face=self.desired_face
        back='left' if face=='right' else 'right'
        if self.strategy in ('counter','jump_in'): command=[['up'],['down'],['attack']]
        elif self.strategy in ('adds_first','survival'): command=[['down'],[],['down','attack']]
        elif self.strategy=='isolate': command=[['down'],['up'],['attack']]
        else:command=[[back],[face],['attack']]
        self.combo.extend([keys for keys in command for _ in range(3)]+[[]]*3)
        self.attack_started=None
        return self.combo.popleft()

    def attack(self):
        if self.attack_started is None:
            self.attack_started = self.f
            self.attack_hp = (self.target['slot'], self.target['hp'])
        elapsed=self.f-self.attack_started
        # A turn requested during recovery can be ignored by the game. Repeat the
        # facing input briefly during a combo instead of treating intent as state.
        keys=[self.desired_face] if elapsed%24<3 else []
        if elapsed%4<2:keys.append('attack')
        return keys


def configurations(boss_slot):
    return [{'behavior_tree': name, 'boss_slot': boss_slot, 'period': 4, 'distance': 30,
             'align': 7, 'jump': 0, 'use_item': False, 'ground_alignment': True}
            for name in STRATEGIES]
