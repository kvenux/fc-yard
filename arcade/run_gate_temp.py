import json,subprocess,sys
from pathlib import Path
p=Path('arcade/runs/kovsh');prefix=json.loads((p/'chapter4-combo-003/gate2-inputs.json').read_text())
c=dict(period=4,distance=32,align=8,jump=0,route_v2=True,focus_boss=True,mpc=True,horizon=240,commit=60,hp_weight=10,fast_preview=True,vision_navigation=True,workers=4,break_obstacles=True,navigation_mpc=True,prefix_inputs=prefix)
subprocess.run([sys.executable,'arcade/kovsh.py','--state',str(p/'chapter4-combo-003/frame-006000.state'),'--frames','300000','--config',json.dumps(c),'--output',str(p/'chapter4-gate-001')],check=True)
