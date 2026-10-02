import subprocess,sys,json
from pathlib import Path
for offset in (32,48,64,96):
 c={'period':4,'distance':32,'align':8,'jump':0,'rush':30,'allow_continue':True,'enemy_y_offset':offset}
 subprocess.run([sys.executable,'arcade/orlegend_campaign.py','--state','arcade/runs/orlegend/spider.state','--output',f'arcade/runs/orlegend/spider-offset-{offset}','--frames','6000','--config',json.dumps(c)],check=True)
