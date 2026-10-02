"""Ordinary input sequences for multiple menu selections."""
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_resources import resources
e=Emulator(ROM,deterministic=True,headless=True);raw=Path('arcade/runs/orlegend/moves-charge-safe-01/frame-600.state').read_bytes();rows=[]
recipes={'double_c':[(['c'],2),([],8),(['c'],2),([],8)],'a_c':[(['attack'],2),([],30),(['c'],2),([],8)],'hold_c':[(['c','left'],2),([],8)]}
try:
    for name,recipe in recipes.items():
        e.restore(raw);e.step(['left'],6);e.step([],90);e.step(['c'],2);e.step([],8);e.step(['left'],2);e.step([],8);first=resources(e.ram())['selected']
        for k,n in recipe:e.step(k,n)
        e.step(['left'],2);e.step([],8);rows.append((name,first,resources(e.ram())['selected']))
finally:e.close()
print(rows)
