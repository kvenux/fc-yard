from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_resources import resources
e=Emulator(ROM,deterministic=True,headless=True);r=Path('arcade/runs/orlegend/moves-charge-safe-01/frame-600.state').read_bytes()
try:
 for keys in [['up'],['down'],['left'],['right'],['up','left'],['up','right'],['down','left'],['down','right']]:
  e.restore(r);e.step(['left'],6);e.step([],90);e.step(['c'],2);e.step([],8);e.step(['left'],2);e.step([],8);e.step(keys,2);e.step([],8);print(keys,resources(e.ram()))
finally:e.close()
