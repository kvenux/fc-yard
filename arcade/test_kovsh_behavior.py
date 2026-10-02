import sys,unittest,copy
sys.path.insert(0,'arcade')
from kovsh_behavior import BehaviorTree,STRATEGIES,ground
from kovsh import observe,action,Navigator,plan_choices
from kovsh_combat import Combat,MODES

def state():
 return dict(hp=80,lives=1,inventory={},selected_item=0,time_remaining=60,x=100,y=200,ground_y=200,height=0,chapter=6,enemies=[dict(slot=0,hp=600,x=180,y=200,ground_y=200,height=0)])
class SafetyTests(unittest.TestCase):
 def test_invalid_cursor_selects_item_before_throwing(self):
  o=state();o.update(inventory={'7':1},selected_item=None)
  choices=plan_choices(o,dict(tactical_choices=True))
  self.assertTrue(any('item_direction' in c for c in choices))
  self.assertFalse(any('use_after' in c for c in choices))
 def test_cave_return_remembers_route_below_trigger_x(self):
  o=state();o.update(chapter=3,room_raw=4,x=1168,ground_y=224,enemies=[],score=0)
  n=Navigator(dict(cave_return_exit=True))
  self.assertEqual(n.choose(o,0,None),['left'])
  o['x']=1000
  self.assertEqual(n.choose(o,1,None),['left'])
  o['x']=865
  self.assertEqual(n.choose(o,2,None),['up'])
  o.update(room_raw=3)
  self.assertIsNone(n.choose(o,3,None))
 def test_bamboo_exit_approaches_lower_lane_without_x_stop(self):
  o=state();o.update(chapter=3,x=2016,ground_y=153,enemies=[])
  n=Navigator(dict(bamboo_exit_lane=True,exit_lower_lane=True))
  self.assertEqual(n.choose(o,0,None),['right','down'])
  o['ground_y']=174
  self.assertEqual(n.choose(o,1,None),['right'])
 def test_bamboo_gate_does_not_redirect_following_rooms(self):
  o=state();o.update(chapter=3,room_raw=4,x=1510,ground_y=210,enemies=[],score=0)
  n=Navigator(dict(bamboo_gate=True,bamboo_exit_lane=True,exit_lower_lane=True))
  self.assertIsNone(n.choose(o,0,None))
 def test_combat_releases_attack_during_far_chase(self):
  for name in MODES:
   o=state();o['enemies'][0]['x']=400;o['actor_code']=0
   self.assertNotIn('attack',Combat(name).tick(o,0))
 def test_locked_strike_keeps_direction_when_enemy_crosses(self):
  t=Combat('locked_combo');o=state();o['actor_code']=1
  o['enemies'][0]['x']=80
  self.assertEqual(t.tick(o,0),['attack'])
  o['enemies'][0]['x']=130
  self.assertEqual(t.tick(o,1),['attack'])
 def test_combat_never_controls_dead_character(self):
  o=state();o['hp']=0
  for mode in MODES:self.assertEqual(Combat(mode).tick(o,0),[])
 def test_fast_chase_handles_empty_room_and_releases_far_attack(self):
  c=dict(period=4,distance=32,align=8,jump=0,attack_in_range=True,special_in_range=True,special='qcf')
  o=state();o['enemies']=[]
  self.assertEqual(action(o,0,c),['right'])
  o=state();o['enemies'][0]['x']=400
  self.assertEqual(action(o,0,c),['right'])
 def test_stale_item_slots_are_not_inventory(self):
  ram=bytearray(0x20000)
  ram[0x1294c:0x12954]=bytes([1,1,1,1,1,1,2,1])
  ram[0x12971]=0;ram[0x12973]=8
  o=observe(ram)
  self.assertEqual(o['inventory'],{})
  self.assertIsNone(o['selected_item'])
 def test_active_slots_and_cursor_use_distinct_fields(self):
  ram=bytearray(0x20000)
  ram[0x1294c:0x12954]=bytes([1,7,1,4,1,1,2,1])
  ram[0x12971]=2;ram[0x12973]=1;ram[0x1297c]=0
  o=observe(ram)
  self.assertEqual(o['inventory'],{'7':1,'4':1})
  self.assertEqual(o['selected_item'],4)
 def test_dead_character_never_attacks_or_spends_credit(self):
  for name in STRATEGIES:
   t=BehaviorTree(name,0);o=state();o['hp']=0
   self.assertEqual(t.tick(o,0),[])
 def test_damage_interrupts_committed_attack(self):
  t=BehaviorTree('survival',0);o=state();t.tick(o,0)
  t.combo.extend([['attack']]*20);o=copy.deepcopy(o);o['hp']-=12
  keys=t.tick(o,1)
  self.assertNotIn('attack',keys);self.assertFalse(t.combo)
 def test_empty_inventory_never_opens_item_menu(self):
  for name in STRATEGIES:
   t=BehaviorTree(name,0)
   for f in range(240):
    keys=t.tick(state(),f)
    self.assertFalse(set(keys)&{'c','d','coin','start'})
 def test_recovery_does_not_flip_escape_each_frame(self):
  t=BehaviorTree('survival',0);o=state();t.tick(o,0);o=copy.deepcopy(o);o['hp']=68
  first=t.tick(o,1)
  for f in range(2,18):
   shifted=copy.deepcopy(o);shifted['enemies'][0]['ground_y']=shifted['enemies'][0]['y']=190 if f%2 else 210
   self.assertEqual(t.tick(shifted,f),first)
 def test_invalid_ground_field_uses_visible_coordinate(self):
  self.assertEqual(ground({'y':200,'ground_y':0,'height':0}),200)
if __name__=='__main__':unittest.main()
