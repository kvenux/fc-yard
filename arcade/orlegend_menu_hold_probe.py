"""Normal-input item cursor calibration, with no memory writes."""
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_resources import resources
from orlegend_bt_train import observation
e=Emulator(ROM,deterministic=True,headless=True)
raw=Path('arcade/runs/orlegend/moves-charge-safe-01/frame-600.state').read_bytes()
try:
 for hold in [1,2,4,8,16,30,60,120]:
  e.restore(raw);e.step(['left'],6);e.step([],90);e.step(['c'],2);e.step([],8)
  row=[]
  for direction in ['left','left','right','right','left']:
   e.step([direction],hold);e.step([],16);row.append(resources(e.ram())['selected'])
  print(hold,row,observation(e)['player_state'],flush=True)
finally:e.close()
