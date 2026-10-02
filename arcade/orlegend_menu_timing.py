"""Find cursor animation debounce using normal key releases."""
import json
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_resources import resources
e=Emulator(ROM,deterministic=True,headless=True);raw=Path('arcade/runs/orlegend/moves-charge-safe-01/frame-600.state').read_bytes();rows=[]
try:
    for delay in [8,16,24,32,40,60]:
        e.restore(raw);e.step(['left'],6);e.step([],90);e.step(['c'],2);e.step([],8);e.step(['left'],2);first=resources(e.ram());e.step([],delay);e.step(['left'],2);second=resources(e.ram());rows.append({'delay':delay,'first':first,'second':second})
finally:e.close()
Path('arcade/runs/orlegend/bt/one-life-menu-timing.json').write_text(json.dumps(rows,indent=2));print([(v['delay'],v['first']['selected'],v['second']['selected']) for v in rows])
