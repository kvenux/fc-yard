"""Normal-input, mirrored command calibration from a charge practice state."""
import argparse,itertools,json
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=False);state=Path(a.state).read_bytes();e=Emulator(ROM,deterministic=True,headless=True);results=[]
try:
 for mode,forward,hold,menu,face in itertools.product(['super','wave','shrink'],['right','left'],[1,2,3,4,6],[False,True],[False,True]):
  e.restore(state);back='left' if forward=='right' else 'right';recipe=[[]]*90
  if face:recipe += [[forward]]*6+[[]]*6
  if menu:recipe += [['c']]*2+[[]]*8
  parts=[[back],[back,'down'],['down'],[forward,'down'],[forward],[back],[forward],['attack']] if mode=='super' else [['down'],[forward,'down'],[forward],['attack']] if mode=='wave' else [[forward],[back],[forward],[back],[forward]]
  for keys in parts:recipe += [keys]*hold
  recipe += [[]]*120;rows=[];moves=set();before=observation(e)
  for f,keys in enumerate(recipe,1):
   e.step(keys);r=e.ram_view();o=observation(e);moves.add((o['player_state'],o['player_move']))
   if f>85:rows.append({'frame':f,'buttons':keys,'hp':o['hp'],'meter':o['resources']['meter'],'state':o['player_state'],'move':o['player_move'],'facing':r[0x1bee2],'held':list(r[0x1c4b2:0x1c4b6]),'commands':[r[(0x11626+i*18+16)^1] for i in range(7)],'command_faces':[r[(0x11626+i*18+17)^1] for i in range(7)]})
  name=f'{mode}-{forward}-h{hold}-menu{int(menu)}-face{int(face)}';success=any(st==6 and mv in ([35] if mode=='super' else [29] if mode=='wave' else [36]) for st,mv in moves)
  row={'name':name,'success_candidate':success,'moves':sorted(moves),'before':before,'after':observation(e)};results.append(row)
  (out/(name+'.json')).write_text(json.dumps(rows));(out/'summary.json').write_text(json.dumps({'scope':'checkpoint command calibration only','results':results},indent=2))
  if success:print(json.dumps(row),flush=True)
finally:e.close()
