import sys,json
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
from orlegend_bt import Controller
out=Path('arcade/runs/orlegend/bt/one-life-ch8-dragon-68-exit-practice-01');out.mkdir(exist_ok=False);e=Emulator(ROM,deterministic=True,headless=True);e.restore(Path('arcade/runs/orlegend/bt/one-life-ch8-dragon-ground-wave-clear-probe-01/True-3.state').read_bytes());initial=o=observation(e);ctrl=Controller(json.loads(Path('arcade/orlegend-bt-ch8-search-policy-14.json').read_text()));inputs=[]
for f in range(3600):
 k=ctrl.choose(o,f);e.step(k);inputs.append(k);o=observation(e)
 if o['hp']<=0 or o['lives']<2 or o['stage_raw']==1795:break
result={'frames':len(inputs),'after':o,'clock':e.ram_view()[0xc06f],'fingerprint':e.fingerprint()};(out/'result.json').write_text(json.dumps(result,indent=2));(out/'final.state').write_bytes(e.save());(out/'exit-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'dragon_68_exit','inputs':inputs}]}));print(json.dumps(result));e.close()
