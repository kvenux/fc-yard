import json,subprocess,sys
from pathlib import Path
p=Path('arcade/runs/kovsh');prefix=[['left']]*50+[['up']]*80+[['right']]*300
c=dict(period=4,distance=32,align=8,jump=0,route_v2=True,focus_boss=True,mpc=True,adaptive=True,fast_preview=True,vision_navigation=True,workers=4,break_obstacles=True,navigation_mpc=True,prefix_inputs=prefix)
subprocess.run([sys.executable,'arcade/kovsh.py','--state',str(p/'maze-002/frame-010800.state'),'--frames','300000','--config',json.dumps(c),'--output',str(p/'temple-001')],check=True)
