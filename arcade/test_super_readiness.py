"""Do not spend a ready special on a boss waiting off-screen for its next phase."""
from orlegend_bt import Controller
c=Controller({'parameters':{},'tree':{'type':'action','name':'input_plan','params':{'runs':[{'frames':1,'buttons':[]}]}}})
o={'stage_raw':1030,'hp':64,'x':1900,'y':132,'player_state':2,'air_mask':0,
   'resources':{'meter':96},'enemies':[{'slot':0,'hp':136,'x':1735,'y':119,'state':1}]}
p={'scenes':[1030],'dx':450,'dy':60,'min_hp':1,'known_boss':True,'exclude_enemy_states':[1]}
c.boss_slots={0}
assert not c.super_ready({'o':o,'frame':100},p)
assert c.super_command({'o':o,'frame':100},{},p).status=='FAILURE'
o['enemies'][0]['state']=3
assert c.super_ready({'o':o,'frame':100},p)
print('Off-screen boss phase preserves special: PASS')
