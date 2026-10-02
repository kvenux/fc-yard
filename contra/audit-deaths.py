import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'arcade'))
from emulator import Emulator
p=Path(sys.argv[1]);r=json.loads(p.read_text());e=Emulator(ROOT/'roms/contra.nes',ROOT/'cores/fceumm_libretro.dll',deterministic=True)
rows=[];dead=False
try:
 for mask,n in r['actions']:
  e.mask=(mask&252)|((mask&1)<<8)|((mask&2)>>1)
  for _ in range(n):
   e.core.retro_run();e.frame+=1;m=e.ram();now=m[0x90]==2
   if now and not dead:rows.append(dict(frame=e.frame,stage=m[0x30]+1,progress=m[0x64]*256+m[0x65],x=m[0x334],y=m[0x31a]));print(rows[-1],flush=True)
   dead=now
 assert e.fingerprint()==r['expected']
 (ROOT/'runs/death-audit.json').write_text(json.dumps({'source':str(p),'replayEqual':True,'deaths':rows},indent=2))
finally:e.close()
