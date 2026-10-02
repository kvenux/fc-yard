from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_resources import resources
states=[Path('arcade/runs/orlegend/moves-charge-safe-01/frame-600.state'),Path('arcade/runs/orlegend/bt/one-life-ch4-boss-dps-practice-03/initial.state'),Path('arcade/runs/orlegend/bt/one-life-ch3-plan-cold-04/final.state')]
e=Emulator(ROM,deterministic=True,headless=True)
try:
 for state in states:
  print(str(state))
  for keys in [['up'],['down'],['left'],['right'],['up','left'],['up','right'],['down','left'],['down','right']]:
   e.restore(state.read_bytes());e.step([],1);e.step(['c'],2);e.step([],8);e.step(keys,2);e.step([],8);print(keys,resources(e.ram()))
finally:e.close()
