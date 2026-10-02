"""Determine which ordinary input rearms consecutive cursor moves."""
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_resources import resources
e=Emulator(ROM,deterministic=True,headless=True);raw=Path('arcade/runs/orlegend/moves-charge-safe-01/frame-600.state').read_bytes();rows=[]
try:
    for reset in [[],['up'],['down'],['c'],['attack']]:
        e.restore(raw);e.step(['left'],6);e.step([],90);e.step(['c'],2);e.step([],8);e.step(['left'],2);first=resources(e.ram());e.step(reset,2);e.step([],2);e.step(['left'],2);second=resources(e.ram());rows.append((reset,first['selected'],second['selected']))
finally:e.close()
print(rows)
