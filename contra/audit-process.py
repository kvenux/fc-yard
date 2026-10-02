"""Capture moment-to-moment replay events without changing game inputs."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT.parent/'arcade'))
from emulator import Emulator
p=Path(sys.argv[1]);r=json.loads(p.read_text());assert r['oneLifeClearVerified'] and r['replayEqual']
assert hashlib.sha256((ROOT/'roms/contra.nes').read_bytes()).hexdigest()==r['romSha256']
assert hashlib.sha256((ROOT/'cores/fceumm_libretro.dll').read_bytes()).hexdigest()==r['coreSha256']
e=Emulator(ROOT/'roms/contra.nes',ROOT/'cores/fceumm_libretro.dll',deterministic=True);events=[];samples=[];previous=None
try:
 for mask,count in r['actions']:
  e.mask=(mask&252)|((mask&1)<<8)|((mask&2)>>1)
  for _ in range(count):
   e.core.retro_run();e.frame+=1;m=e.ram()
   y=m[0x31a]+(m[0xba] if m[0xba]<128 else m[0xba]-256)*256
   enemies=[dict(slot=i,type=m[0x528+i],hp=m[0x578+i],x=m[0x33e+i],y=m[0x324+i]) for i in range(16) if m[0x4b8+i]]
   nearby=[t for t in enemies if abs(t['x']-m[0x334])<96 and abs(t['y']-y)<48]
   row=dict(frame=e.frame,stage=m[0x30],x=m[0x334],y=y,jump=m[0xa0]&1,weapon=m[0xaa]&15,playerState=m[0x90],input=mask,nearby=nearby)
   if previous and row['stage']!=previous['stage']:events.append(dict(kind='stage',**row))
   if previous and m[0x18]==5 and m[0x90]==1:
    for kind,changed in [('weapon',row['weapon']!=previous['weapon']),('jump_start',row['jump'] and not previous['jump']),('landing',not row['jump'] and previous['jump'])]:
     if changed:events.append(dict(kind=kind,**row))
   if e.frame%60==0:samples.append(row)
   previous=row
 assert e.fingerprint()==r['expected']
 out=dict(run=p.parent.name,replayEqual=True,events=events,samples=samples)
 (p.parent/'process-audit.json').write_text(json.dumps(out,separators=(',',':')))
 print(json.dumps(dict(run=p.parent.name,replayEqual=True,events=len(events),samples=len(samples))))
finally:e.close()
