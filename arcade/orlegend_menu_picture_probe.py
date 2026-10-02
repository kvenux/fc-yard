from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_resources import resources
e=Emulator(ROM,deterministic=True,headless=False)
e.restore(Path('arcade/runs/orlegend/moves-charge-safe-01/frame-600.state').read_bytes());e.step(['left'],6);e.step([],90)
for name,k,n in [('safe',[],1),('open',['c'],2),('wait',[],8),('left',['left'],2),('wait2',[],8),('left2',['left'],2),('wait3',[],8)]:
 e.step(k,n);e.picture().save('arcade/runs/orlegend/menu-'+name+'.png');print(name,resources(e.ram()))
e.close()
