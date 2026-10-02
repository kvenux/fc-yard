"""Read-only differences for normal menu open/selection/close inputs."""
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_resources import resources
e=Emulator(ROM,deterministic=True,headless=True)
try:
 e.restore(Path('arcade/runs/orlegend/moves-charge-safe-01/frame-600.state').read_bytes());e.step([],90);before=e.ram()
 for name,keys,n in [('open',['c'],2),('open_wait',[],8),('left',['left'],2),('left_wait',[],8),('confirm',['attack'],2),('confirm_wait',[],12)]:
  e.step(keys,n);r=e.ram();changes=[]
  for lo,hi in [(0x11180,0x111c0),(0x1be3c,0x1bf80),(0x1c6c0,0x1c6e0)]:
   changes += [(hex(i),before[i],r[i]) for i in range(lo,hi) if before[i]!=r[i]]
  print(name,resources(r),changes);before=r
finally:e.close()
