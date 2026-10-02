import json,subprocess,sys
from pathlib import Path
p=Path('arcade/runs/kovsh');prefix=[['right']]*180
c=dict(period=4,distance=32,align=8,jump=0,route_v2=True,focus_boss=True,mpc=True,adaptive=True,fast_preview=True,vision_navigation=True,workers=4,break_obstacles=True,navigation_mpc=True,prefix_inputs=prefix)
subprocess.run([sys.executable,'arcade/kovsh.py','--state',str(p/'obstacle-003/frame-011400.state'),'--frames','300000','--config',json.dumps(c),'--output',str(p/'temple-002')],check=True)
