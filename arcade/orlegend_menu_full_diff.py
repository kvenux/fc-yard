from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
e=Emulator(ROM,deterministic=True,headless=True);e.restore(Path('arcade/runs/orlegend/moves-charge-safe-01/frame-600.state').read_bytes());e.step(['left'],6);e.step([],90);old=e.ram()
for name,k,n in [('open',['c'],2),('wait',[],8),('confirm',['attack'],2),('waitclose',[],30),('reopen',['c'],2)]:
 e.step(k,n);r=e.ram();print(name,observation(e)['player_move'],[(hex(i),old[i],r[i]) for i in range(len(r)) if old[i]!=r[i] and not(0x11a00<i<0x1be00)][:150]);old=r
e.close()
