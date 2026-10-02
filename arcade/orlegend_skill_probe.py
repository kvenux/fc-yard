"""Calibrate command moves using normal inputs from a practice checkpoint."""
import argparse,json
from pathlib import Path
from emulator import Emulator
from orlegend import ROM,observe
p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--output',required=True);p.add_argument('--skill',default='super');p.add_argument('--hold',type=int,default=2);p.add_argument('--warmup',type=int,default=0);p.add_argument('--repeat',type=int,default=1);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
e=Emulator(ROM,deterministic=True);e.restore(Path(a.state).read_bytes());before=observe(e.ram());recipe=[]
def append(keys,n):recipe.extend([keys]*n)
append([],4)
append([],a.warmup)
if a.skill=='super_face':append(['right'],2);append([],8)
if a.skill in ('super','super_face'):parts=[['left'],['left','down'],['down'],['right','down'],['right'],['left'],['right','attack']]
elif a.skill in ('super_clean','menu_super'):
 if a.skill=='menu_super':append(['c'],2);append([],8)
 parts=[['left'],['left','down'],['down'],['right','down'],['right'],['left'],['right'],['attack']]
elif a.skill=='wave_clean':parts=[['down'],['right','down'],['right'],['attack']]
elif a.skill=='super_separate':parts=[['right'],[],['left'],['left','down'],['down'],['right','down'],['right'],['left'],['right'],['attack']]
elif a.skill=='super_charge':
 append(['attack','jump','c'],120);append([],8);parts=[['left'],['left','down'],['down'],['right','down'],['right'],['left'],['right','attack']]
elif a.skill=='wave':parts=[['down'],['right','down'],['right','attack']]
elif a.skill=='jumpwave':
 append(['jump'],2);append([],10);parts=[['down'],['right','down'],['right','attack']]
elif a.skill=='use':parts=[['d']]
elif a.skill=='menu':parts=[['c']]
elif a.skill in ('menu_left','menu_right'):
 append(['c'],2);append([],8);append(['left' if a.skill=='menu_left' else 'right'],2);append([],8);append(['attack'],2);append([],12);parts=[['d']]
else:parts=[[]]
for repeat in range(a.repeat):
 for keys in parts:append(keys,a.hold)
 if repeat<a.repeat-1:append([],30)
append([],180);rows=[];trace=[]
try:
 for f,keys in enumerate(recipe,1):
  e.step(keys);r=e.ram();o=observe(r);rows.append({'frame':f,'buttons':keys,'action':[r[0x1be83],r[0x1be82]],'commands':[r[(0x11626+i*18+16)^1] for i in range(7)],'facing_candidate':r[0x1bee2],'meter':r[0x1bf4d],'mode':r[0x1bf4c],'inventory':list(r[0x1118a:0x1119a]),**o});trace.append({'frame':f,'buttons':keys})
  if f in [20,40,80,120,180]:e.picture().save(out/f'frame-{f}.png');(out/f'frame-{f}.ram').write_bytes(r)
 (out/'samples.json').write_text(json.dumps(rows,indent=2));(out/'inputs.jsonl').write_text('\n'.join(map(json.dumps,trace))+'\n');(out/'final.state').write_bytes(e.save());print({'before':before,'after':rows[-1]},flush=True)
finally:e.close()
