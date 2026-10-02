"""Export HUD samples from a fresh, fully verified native execution."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT.parent/'arcade'))
from emulator import Emulator
p=Path(sys.argv[1]);r=json.loads(p.read_text());assert r['oneLifeClearVerified']
combat_path=p.parent/'combat-audit.json';combat=json.loads(combat_path.read_text()) if combat_path.exists() else None
if combat:assert combat['run']==p.parent.name and combat['replayEqual']
gun_frames=[event['frame'] for event in combat['events'] if event['kind']=='gun'] if combat else []
e=Emulator(ROOT/'roms/contra.nes',ROOT/'cores/fceumm_libretro.dll',deterministic=True);rows=[];deaths=0;previous=False
def sample():
 m=e.ram();rows.append(dict(frame=e.frame,stage=m[0x30],score=m[0x7e2]+256*m[0x7e3],lives=m[0x32]+1,weapon=m[0xaa]&15,deaths=deaths,status=m[0x18],gunKills=sum(f<=e.frame for f in gun_frames) if combat else None))
try:
 sample();last_stage=0
 for mask,count in r['actions']:
  e.mask=(mask&252)|((mask&1)<<8)|((mask&2)>>1)
  for _ in range(count):
   e.core.retro_run();e.frame+=1;m=e.ram();dead=m[0x90]==2
   if dead and not previous:deaths+=1
   previous=dead
   if e.frame%60==0 or m[0x30]!=last_stage:sample()
   last_stage=m[0x30]
 assert e.fingerprint()==r['expected'];assert deaths==0;sample()
 (p.parent/'replay-telemetry.json').write_text(json.dumps(dict(run=p.parent.name,replayEqual=True,deaths=deaths,rows=rows),separators=(',',':')))
 print(json.dumps(dict(run=p.parent.name,samples=len(rows),deaths=deaths,replayEqual=True)))
finally:e.close()
