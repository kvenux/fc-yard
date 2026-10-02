import sys,json
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-dragon-finish-probe-01');plan=json.loads((out/'finish_10-plan.json').read_text());e=Emulator(ROM,deterministic=True,headless=True);e.restore(Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-04/checkpoints/depth-075.state').read_bytes());inputs=[]
for t,k in enumerate(plan['macros'][0]['inputs']):
 e.step(k);inputs.append(k);o=observation(e)
 if not o['enemies'] and o['player_state']==2:
  name=f'finish10-short-{t+1}';(out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':plan['initial'],'after':o,'macros':[{'name':name,'inputs':inputs}]}));print(json.dumps({'name':name,'o':o,'clock':e.ram_view()[0xc06f]}));break
r=e.ram_view();print('STATIC',json.dumps([{'i':i,'type':r[b+4],'id':r[b+0x7f],'x':int.from_bytes(r[b+0x14:b+0x16],'little'),'y':int.from_bytes(r[b+0x16:b+0x18],'little')} for i in range(80) if r[(b:=0xc266+0x98*i)+1]==2]));e.close()
