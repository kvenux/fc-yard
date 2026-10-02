"""Count confirmed gun destructions during an independently verified boot replay."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT.parent/'arcade'))
from emulator import Emulator
p=Path(sys.argv[1]);r=json.loads(p.read_text());assert r['replayEqual']
rom=ROOT/'roms/contra.nes';core=ROOT/'cores/fceumm_libretro.dll'
assert hashlib.sha256(rom.read_bytes()).hexdigest()==r['romSha256'];assert hashlib.sha256(core.read_bytes()).hexdigest()==r['coreSha256']
e=Emulator(rom,core,deterministic=True);events=[];last=bytes(e.ram());deaths=0
try:
 for mask,n in r['actions']:
  e.mask=(mask&252)|((mask&1)<<8)|((mask&2)>>1)
  for _ in range(n):
   e.core.retro_run();e.frame+=1;m=bytes(e.ram());stage=last[0x30]
   if m[0x90]==2 and last[0x90]!=2:deaths+=1
   score=m[0x7e2]+256*m[0x7e3];old_score=last[0x7e2]+256*last[0x7e3]
   if stage not in [1,3] and stage<8 and score>old_score:
    for i in range(16):
     typ=last[0x528+i]
     if typ in [4,6,7,14] and last[0x4b8+i] and 0<last[0x578+i]<240 and m[0x528+i]==typ and m[0x578+i]==0:
      events.append(dict(frame=e.frame,stage=stage+1,type=typ,kind='sniper' if typ==6 else 'gun',x=last[0x33e+i],y=last[0x324+i],scoreGain=score-old_score))
   last=m
 assert e.fingerprint()==r['expected'];assert deaths==r['deaths']
 by_stage={str(s):sum(x['stage']==s and x['kind']=='gun' for x in events) for s in range(1,9)}
 data=dict(run=p.parent.name,replayEqual=True,frames=r['frames'],deaths=deaths,finalScore=r['final']['score']*100,gunKills=sum(x['kind']=='gun' for x in events),sniperKills=sum(x['kind']=='sniper' for x in events),gunKillsByStage=by_stage,events=events)
 (p.parent/'combat-audit.json').write_text(json.dumps(data,indent=2));print(json.dumps({k:v for k,v in data.items() if k!='events'}),flush=True)
finally:e.close()
