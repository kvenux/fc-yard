"""Ordinary-input cursor calibration in both facing directions."""
import itertools,json
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
e=Emulator(ROM,deterministic=True,headless=True);raw=Path('arcade/runs/orlegend/moves-charge-safe-01/frame-600.state').read_bytes();rows=[]
try:
    for face,direction in itertools.product(['left','right'],['left','right','up','down']):
        e.restore(raw);e.step([face],6);e.step([],90);trace=[{'step':'before','o':observation(e)}];e.step(['c'],2);e.step([],8);trace.append({'step':'open','o':observation(e)})
        for n in range(3):e.step([direction],2);e.step([],8);trace.append({'step':str(n),'o':observation(e)})
        rows.append({'face':face,'direction':direction,'trace':trace})
finally:e.close()
Path('arcade/runs/orlegend/bt/one-life-menu-directions.json').write_text(json.dumps(rows,indent=2));print([(r['face'],r['direction'],[(t['o']['player_state'],t['o']['player_facing'],t['o']['resources']['selected']) for t in r['trace']]) for r in rows])
