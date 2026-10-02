"""Credit a lethal final hit, but not disappearance with HP remaining or a room change."""
from orlegend_beam_parallel import damage_increment
ram=bytearray(0x13000)
old={'stage_raw':1030,'enemies':[{'slot':0,'hp':2}]}
now={'stage_raw':1030,'enemies':[]}
assert damage_increment(old,now,{(1030,0)},ram)==(2,2)
ram[0x11a88:0x11a8a]=(2).to_bytes(2,'little')
assert damage_increment(old,now,{(1030,0)},ram)==(0,0)
ram[0x11a88:0x11a8a]=(520).to_bytes(2,'little')
assert damage_increment(old,now,{(1030,0)},ram)==(0,0)
ram[0x11a88:0x11a8a]=(0).to_bytes(2,'little')
now['stage_raw']=1280
assert damage_increment(old,now,{(1030,0)},ram)==(0,0)
print('Lethal hit, live disappearance, spawn and scene boundaries: PASS')
