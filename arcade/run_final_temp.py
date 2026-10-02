import json,subprocess,sys
from pathlib import Path
r=Path('arcade/runs/kovsh');prefix=json.loads((r/'two-life-wall-001/river-inputs.json').read_text())
c=dict(period=4,distance=32,align=8,jump=0,route_v2=True,focus_boss=True,mpc=True,horizon=180,commit=30,hp_weight=100,fast_preview=True,vision_navigation=True,workers=4,break_obstacles=True,navigation_mpc=True,navigation_from=1,bamboo_gate=True,prefix_inputs=prefix)
subprocess.run([sys.executable,'arcade/kovsh.py','--state',str(r/'two-life-wall-001/frame-022800.state'),'--frames','200000','--config',json.dumps(c),'--output',str(r/'two-life-final-001')],check=True)
