from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
e=Emulator(ROM,deterministic=True,headless=False);e.restore(Path('arcade/runs/orlegend/bt/one-life-ch4-boss-dps-practice-03/initial.state').read_bytes());e.step([],2);e.picture().save('arcade/runs/orlegend/ch4-boss-initial.png');print(observation(e));e.close()

