"""Audit PGM rollback against uninterrupted native execution, with video disabled."""
import argparse,json,hashlib,time
from pathlib import Path
from emulator import Emulator
from kovsh import ROM,OUT,observe,sha
p=argparse.ArgumentParser();p.add_argument('--core',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False)
e=Emulator(ROM,core=a.core,deterministic=True,headless=True);start=time.perf_counter()
try:
 for i,line in enumerate((OUT/'one-life-bamboo-prefix.jsonl').read_text().splitlines(),1):
  e.step(json.loads(line)['buttons'])
  if i%20000==0:print(a.output.name,'warm frames',i,flush=True)
 expected=(OUT/'two-life-001/frame-047400.ram').read_bytes();prefix_equal=e.ram()==expected
 state=e.save();initial=observe(e.ram_view());rows=[json.loads(x)['buttons'] for x in (OUT/'two-life-001/inputs.jsonl').read_text().splitlines()[47400:48000]];hashes=[]
 for keys in rows:e.step(keys);hashes.append(hashlib.sha256(e.ram_view()).hexdigest())
 continuous=e.ram();continuous_state=e.save();continuous_obs=observe(continuous)
 e.restore(state);restored_initial_equal=e.ram()==expected;first_difference=None
 for i,keys in enumerate(rows,1):
  e.step(keys)
  if first_difference is None and hashlib.sha256(e.ram_view()).hexdigest()!=hashes[i-1]:first_difference=i
 restored=e.ram();restored_state=e.save()
 report={'core_sha256':sha(a.core),'headless':True,'video_bytes_allocated':e.video_bytes is not None,'frames_warmed':86890,'prefix_equal_to_recorded_ram':prefix_equal,'restored_initial_equal':restored_initial_equal,'first_ram_divergence_frame':first_difference,'ending_ram_equal':restored==continuous,'ending_state_equal':restored_state==continuous_state,'state_bytes':len(state),'initial':initial,'continuous_after':continuous_obs,'restored_after':observe(restored),'seconds':time.perf_counter()-start,'gameplay_clear_verified':False}
 (a.output/'checkpoint.state').write_bytes(state);(a.output/'checkpoint.ram').write_bytes(expected);(a.output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
finally:e.close()
