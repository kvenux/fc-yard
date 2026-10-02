import json,subprocess,sys
from pathlib import Path
p=Path('arcade/runs/kovsh');macro=json.loads((p/'campaign-003/maze-solution.json').read_text());prefix=[]
for keys in macro:
 for f in range(30):prefix.append([k for k in keys if (k!='jump' or f<2) and (k!='attack' or f%4<2)])
c=dict(period=4,distance=32,align=8,jump=0,route_v2=True,focus_boss=True,mpc=True,adaptive=True,fast_preview=True,vision_navigation=True,workers=4,break_obstacles=True,prefix_inputs=prefix)
subprocess.run([sys.executable,'arcade/kovsh.py','--state',str(p/'campaign-003/frame-010200.state'),'--frames','300000','--config',json.dumps(c),'--output',str(p/'maze-002')],check=True)
