import sys,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'arcade'))
from emulator import Emulator
e=Emulator(ROOT/'roms/contra.nes',ROOT/'cores/fceumm_libretro.dll',deterministic=True)
directory=ROOT/'runs/native-20261001-164106';saved=(directory/'latest.state').read_bytes()
e.restore(saved);m=e.ram()
def collision(x,y):
    if y>=224:return 0
    yy=y+m[0xfc]
    if yy>=240:yy=(yy+16)&255
    xx=x+m[0xfd];nt=(m[0xff]&1)^(xx>=256);xx&=255
    col=xx>>4;offset=((yy>>2)&60)|(col>>2)|(64 if nt else 0)
    return (m[0x680+offset]>>((3-(col&3))*2))&3
print({'x':m[0x334],'y':m[0x31a],'scroll':m[0x64]*256+m[0x65],'vertical':m[0xfc],'horizontal':m[0xfd],'nt':m[0xff]&1},flush=True)
for y in range(8,224,16):print(f'{y:03}: '+''.join('.=~#'[collision(x,y)] for x in range(8,256,16)),flush=True)
rows=[]
for direction in [64,128]:
 for walk in [0,16,32,48,64,80,96,112,128]:
  for phase in [0,8,16,24]:
   e.restore(saved);dead=False;maxp=0
   for f in range(240):
    mask=direction|2|(1 if f>=walk and (f-walk+phase)%32<1 else 0)
    e.mask=(mask&252)|((mask&1)<<8)|((mask&2)>>1);e.core.retro_run();r=e.ram()
    if r[0x90]==2:dead=True
    maxp=max(maxp,r[0x64]*256+r[0x65])
   rows.append({'direction':direction,'walk':walk,'phase':phase,'dead':dead,'progress':r[0x64]*256+r[0x65],'maxProgress':maxp,'x':r[0x334],'y':r[0x31a]})
rows.sort(key=lambda r:(r['dead'],-r['maxProgress'],r['y']))
(ROOT/'runs/vertical-probes.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows[:12]),flush=True);e.close()
