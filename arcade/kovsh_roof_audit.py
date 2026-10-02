"""Locate the earliest roof input divergence across continuous and restored runs."""
import sys,json,hashlib,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from emulator import Emulator
from kovsh import ROM,OUT,observe
mode=sys.argv[1]; out=OUT/('roof-audit-'+mode);out.mkdir(exist_ok=True)
e=Emulator(ROM,deterministic=True);e.av_enable=2
try:
 if mode=='continuous':
  chain=json.loads((OUT/'roof-entry-cold-chain.json').read_text())
  segments=[{'file':'boot-inputs.jsonl'}]+chain['parts']
  for part in segments:
   p=OUT/part.get('directory','')/part.get('file','inputs.jsonl')
   rows=p.read_text().splitlines()
   for line in rows[:part.get('frames',len(rows))]:e.step(json.loads(line)['buttons'])
 else:
  p=OUT/('roof-entry-cold/final.state' if mode=='cold' else 'two-life-roof-001/initial.state')
  e.restore(p.read_bytes())
 roof=OUT/'two-life-roof-001'; checks=[]
 with (out/'hashes.jsonl').open('w') as f:
  for i,line in enumerate((roof/'inputs.jsonl').read_text().splitlines()[:17400],1):
   e.step(json.loads(line)['buttons']);ram=e.ram()
   f.write(json.dumps([i,hashlib.sha256(ram).hexdigest()])+'\n')
   if i%600==0:
    same=ram==(roof/f'frame-{i:06d}.ram').read_bytes();checks.append({'frame':i,'ram_equal':same,'obs':observe(ram)})
    (out/'progress.json').write_text(json.dumps(checks[-1]));print(mode,i,same,flush=True)
 (out/'report.json').write_text(json.dumps(checks,indent=2))
finally:e.close()
