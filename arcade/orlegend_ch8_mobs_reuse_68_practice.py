import sys,json,gzip
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-mobs-reuse-68-practice-01');out.mkdir(exist_ok=False);e=Emulator(ROM,deterministic=True,headless=True);e.restore(Path('arcade/runs/orlegend/bt/one-life-ch8-dragon-68-exit-practice-02/final.state').read_bytes());initial=o=observation(e);inputs=[];trace=[]
for pool,depth in [(8,10),(9,31),(10,38)]:
 p=Path(f'arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-{pool:02}/checkpoints/depth-{depth:03}.json.gz');d=json.loads(gzip.decompress(p.read_bytes()))
 for m in d['macros']:
  for k in m['inputs']:
   e.step(k);inputs.append(k);o=observation(e)
   if o['hp']<=0 or o['lives']<2:break
  if o['hp']<=0 or o['lives']<2:break
 trace.append({'pool':pool,'frames':len(inputs),'after':o,'clock':e.ram_view()[0xc06f]})
 if o['hp']<=0 or o['lives']<2:break
result={'frames':len(inputs),'after':o,'clock':e.ram_view()[0xc06f],'trace':trace};(out/'result.json').write_text(json.dumps(result,indent=2));(out/'final.state').write_bytes(e.save());(out/'mobs-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'mobs_68_reused_inputs','inputs':inputs}]}));print(json.dumps(result));e.close()
