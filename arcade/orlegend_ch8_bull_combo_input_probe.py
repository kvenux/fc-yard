import sys,json
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM,action
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-bull-combo-input-probe-01');out.mkdir(exist_ok=False);e=Emulator(ROM,deterministic=True,headless=True);raw=Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-15/checkpoints/depth-020.state').read_bytes();rows=[]
for name in ['combat','hold_attack','pulse1','pulse4','face_hold','face_pulse1','abc','wait']:
 e.restore(raw);initial=o=observation(e);inputs=[]
 for t in range(720):
  if name=='combat':k=action(o,t,{'distance':56,'align':14,'jump':0,'rush':0,'period':4})
  elif name=='wait':k=[]
  elif name=='abc':k=['attack','jump','c']
  else:
   period=2 if 'pulse1' in name else 8 if name=='pulse4' else 1
   k=['attack'] if period==1 or t%period<period//2 else []
   if name.startswith('face') and o['enemies']:k+=['right' if o['enemies'][0]['x']>=o['x'] else 'left']
  e.step(k);inputs.append(k);o=observation(e)
  if o['hp']<=0 or o['lives']<2:break
 row={'name':name,'frames':len(inputs),'o':o,'clock':e.ram_view()[0xc06f]};rows.append(row);print(json.dumps(row),flush=True)
 if o['hp']>0 and o['lives']==2:
  (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':name,'inputs':inputs}]}))
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
