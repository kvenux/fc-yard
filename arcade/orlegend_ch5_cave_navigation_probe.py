import sys,json;sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
from orlegend_bt import Controller
out=Path('arcade/runs/orlegend/bt/one-life-ch5-cave-navigation-practice-01');out.mkdir(exist_ok=False);raw=Path('arcade/runs/orlegend/bt/one-life-ch5-finish-parallel-beam-practice-01/checkpoints/depth-048.state').read_bytes();e=Emulator(ROM,deterministic=True,headless=True);rows=[]
recipes={'up':[(['up'],120),(['right','up'],480)],'left_up':[(['left'],60),(['up'],120),(['right','up'],420)],'up_left':[(['up','left'],80),(['up','right'],520)],'down':[(['down'],80),(['right'],520)],'down_right':[(['down','right'],600)],'down_left':[(['down','left'],80),(['down','right'],520)]}
for name,recipe in recipes.items():
 for attack in [False,True]:
  e.restore(raw);inputs=[]
  for k,n in recipe:
   for t in range(n):
    keys=k+(['attack'] if attack and t%4<2 else []);e.step(keys);inputs.append(keys)
    if observation(e)['hp']==0:break
   if observation(e)['hp']==0:break
  o=observation(e);label=f'{name}-{attack}';(out/(label+'-inputs.json')).write_text(json.dumps(inputs));(out/(label+'.state')).write_bytes(e.save());rows.append({'name':label,'after':o});print(label,o['hp'],o['x'],o['y'],o['enemies'],flush=True)
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
