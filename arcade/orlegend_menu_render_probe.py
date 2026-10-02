"""Verify cursor behavior with and without core drawing, not frontend screenshots."""
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_resources import resources
e=Emulator(ROM,deterministic=True,headless=True);raw=Path('arcade/runs/orlegend/moves-charge-safe-01/frame-600.state').read_bytes();rows=[]
try:
    for av in [2,3]:
        e.av_enable=av;e.restore(raw);e.step(['left'],6);e.step([],90);e.step(['c'],2);e.step([],8);trace=[]
        for n in range(6):e.step(['left'],2);e.step([],8);trace.append(resources(e.ram())['selected'])
        rows.append((av,trace,e.fingerprint()['ram']))
finally:e.close()
print(rows)
