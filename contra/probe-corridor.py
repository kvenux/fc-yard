import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT.parent/'arcade'))
from emulator import Emulator
p=Path(sys.argv[1]);r=json.loads((p/'result.json').read_text());saved=(p/'final.state').read_bytes()
e=Emulator(ROOT/'roms/contra.nes',ROOT/'cores/fceumm_libretro.dll',deterministic=True);rows=[]
try:
 for wait in range(0,256,16):
  for run in [32,64,96,128,160]:
   for drop in [32,64,96,128]:
    e.restore(saved,r['frames']);seq=[];dead=False
    for f in range(wait+run+drop+320):
     t=f-wait
     if t<0:mask=32
     elif t<run:mask=128|(1 if t==0 else 0)
     elif t<run+drop:mask=32|(1 if (t-run)%32==0 else 0)
     else:mask=128
     mask|=2 if f%8<4 else 0
     e.mask=(mask&252)|((mask&1)<<8)|((mask&2)>>1);e.core.retro_run();e.frame+=1;seq.append(mask);m=e.ram()
     if m[0x90]==2:dead=True;break
    progress=m[0x64]*256+m[0x65]
    rows.append(dict(wait=wait,run=run,drop=drop,dead=dead,progress=progress,frame=e.frame,x=m[0x334],y=m[0x31a]))
 rows.sort(key=lambda r:(r['dead'],-r['progress']));print(json.dumps(rows[:20]),flush=True)
 (ROOT/'runs/corridor-probe.json').write_text(json.dumps(rows,indent=2))
finally:e.close()
