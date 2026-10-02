"""Independent cold replay of a growing, ordinary-input trace; never restores state."""
import sys,json,time
from pathlib import Path
from emulator import Emulator
from orlegend import ROM,sha,observe
folder=Path(sys.argv[1]);meta=json.loads((folder/'manifest.json').read_text());assert meta['start']=='poweron'
e=Emulator(ROM,deterministic=True);assert sha(ROM)==meta['rom_sha256'] and sha(e.core_path)==meta['core_sha256']
n=0;pending='';start=time.perf_counter();coins=0;held=False
try:
 with (folder/'inputs.jsonl').open() as stream:
  while True:
   line=stream.readline()
   if not line:
    if (folder/'result.json').exists():
     result=json.loads((folder/'result.json').read_text())
     if n==result['frames']:break
    time.sleep(.1);continue
   pending+=line
   if not pending.endswith('\n'):continue
   row=json.loads(pending);pending='';assert row['frame']==n+1;keys=row['buttons'];e.step(keys);n+=1
   pressed='coin' in keys;coins+=int(pressed and not held);held=pressed
   if n%20000==0:
    progress={'frame':n,'wall_seconds':time.perf_counter()-start,**observe(e.ram())};(folder/'replay-progress.json').write_text(json.dumps(progress,indent=2));print('REPLAY_PROGRESS',n,progress['stage_raw'],flush=True)
   if n%300==0 and observe(e.ram())['stage_byte']>=8:e.picture().save(folder/f'verified-ending-{n:07d}.png')
 expected=result['expected'];actual=e.fingerprint();equal=actual==expected
 replay={'equal':equal,'actual':actual,'expected':expected,'start':'poweron','restores':0,'frames':n,'coins':coins,'continues':coins-1,'wall_seconds':time.perf_counter()-start}
 (folder/'replay.json').write_text(json.dumps(replay,indent=2));e.picture().save(folder/'replay-final.png');(folder/'replay-final.state').write_bytes(e.save());(folder/'replay-final.ram').write_bytes(e.ram());print('REPLAY',json.dumps(replay),flush=True)
 if not equal:raise RuntimeError('Cold replay final fingerprint mismatch')
finally:e.close()
