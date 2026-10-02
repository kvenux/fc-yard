import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT.parent/'arcade'))
from emulator import Emulator
e=Emulator(ROOT/'roms/contra.nes',ROOT/'cores/fceumm_libretro.dll',deterministic=True)
def step(mask):
 e.mask=(mask&252)|((mask&1)<<8)|((mask&2)>>1);e.core.retro_run();e.frame+=1
r=json.loads(Path(sys.argv[1]).read_text());limit=int(sys.argv[2])
for mask,n in r['actions']:
 for _ in range(n):
  if e.frame>=limit:break
  step(mask)
 if e.frame>=limit:break
saved=e.save();rows=[]
try:
 for move in [-100,-64,-32,-16,0,16,32]:
  for duck in [False,True]:
   for pulse in [2,4,8,0]:
    e.restore(saved,limit);dead=False
    for f in range(960):
     d=(64 if move<0 else 128) if f<abs(move) else (128 if f==abs(move) else (32 if duck else 0))
     fire=2 if pulse==0 or f%pulse==0 else 0
     step(d|fire);m=e.ram()
     if m[0x90]==2:dead=True;break
    tanks=[dict(hp=m[0x578+i],x=m[0x33e+i],routine=m[0x4b8+i]) for i in range(16) if m[0x528+i]==18 and m[0x4b8+i]]
    row=dict(move=move,duck=duck,pulse=pulse,dead=dead,frames=f+1,x=m[0x334],tanks=tanks);rows.append(row)
 print(json.dumps(sorted(rows,key=lambda r:(r['dead'],sum(t['hp'] for t in r['tanks'])))),flush=True)
 (ROOT/'runs/tank-probe.json').write_text(json.dumps(rows,indent=2))
finally:e.close()
