"""Ordinary-button command calibration; candidate RAM fields are read-only."""
import argparse,json
from pathlib import Path
from emulator import Emulator
from orlegend import ROM,observe
p=argparse.ArgumentParser();p.add_argument('mode');p.add_argument('--state',default='arcade/runs/orlegend/full-policy-cold-05/entry-0002584-0000.state');p.add_argument('--output',required=True);p.add_argument('--warmup',type=int,default=0);p.add_argument('--hold',type=int,default=300);p.add_argument('--frames',type=int,default=600);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
e=Emulator(ROM,deterministic=True);e.restore(Path(a.state).read_bytes());rows=[];trace=[]
try:
 if a.warmup:e.step([],a.warmup)
 for f in range(a.frames):
  if a.mode=='abc':keys=['attack','jump','c'] if f<a.hold else []
  elif a.mode=='ac_b':keys=['attack','c']+(['jump'] if f>=10 else []) if f<300 else []
  elif a.mode=='abd':keys=['attack','jump','d'] if f<300 else []
  elif a.mode=='abc_pulse':keys=['attack','jump','c'] if f<300 and f%4<2 else []
  elif a.mode=='ac_b_pulse':keys=['attack','c']+(['jump'] if f%4<2 else []) if f<300 else []
  elif a.mode=='acd':keys=['attack','c','d'] if f<300 else []
  else:keys=[]
  e.step(keys);r=e.ram();o=observe(r);trace.append({'frame':f+1,'buttons':keys})
  if f%10==9:rows.append({'frame':f+1,'meter_candidate':r[0x1bf4d],'timer_candidate':r[0x1bf74],'invulnerable_candidate':r[0x1bf61],**o})
  if f in (59,179,299,599):
   e.picture().save(out/f'frame-{f+1}.png');(out/f'frame-{f+1}.ram').write_bytes(r);(out/f'frame-{f+1}.state').write_bytes(e.save())
 (out/'samples.json').write_text(json.dumps(rows,indent=2));(out/'inputs.jsonl').write_text('\n'.join(map(json.dumps,trace))+'\n');(out/'final.state').write_bytes(e.save());(out/'final.ram').write_bytes(e.ram());print(rows[29],flush=True)
finally:e.close()
