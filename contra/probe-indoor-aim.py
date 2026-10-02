import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT.parent/'arcade'))
from emulator import Emulator
p=Path(sys.argv[1]);e=Emulator(ROOT/'roms/contra.nes',ROOT/'cores/fceumm_libretro.dll',deterministic=True);saved=(p/'final.state').read_bytes();e.restore(saved);m=e.ram();start_x=m[0x334]
slots=[i for i in range(16) if m[0x528+i]==20 and m[0x4b8+i]];initial=sum(m[0x578+i] for i in slots)
print('items',[(m[0x33e+i],m[0x324+i],m[0x5a8+i]&7) for i in range(16) if m[0x528+i]==0 and m[0x4b8+i]],flush=True)
rows=[]
try:
 for x in [80,112,176]:
  for mode in [4,5]:
   continuous=bool(mode&1);jump=bool(mode&2)
   e.restore(saved);dead=False
   for f in range(640):
    mask=(64 if x<start_x else 128) if f<abs(x-start_x) else (32 if mode&4 else 0)
    mask|=2 if continuous or f%8<4 else 0
    if jump and f%32==0:mask|=1
    e.mask=(mask&252)|((mask&1)<<8)|((mask&2)>>1);e.core.retro_run();m=e.ram();dead|=m[0x90]==2
   hp=sum(m[0x578+i] for i in slots if m[0x528+i]==20 and m[0x4b8+i]);rows.append(dict(x=x,endX=m[0x334],jump=jump,continuous=continuous,dead=dead,damage=initial-hp,weapon=m[0xaa]&15))
 rows.sort(key=lambda r:(r['dead'],-r['damage']));print(json.dumps(rows),flush=True)
 (ROOT/'runs/one-life-aim-probe.json').write_text(json.dumps(rows,indent=2))
finally:e.close()
