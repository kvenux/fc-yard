"""Replay a contiguous training input chain from cold power-on, without restoring."""
import argparse,json,time,shutil,hashlib
from pathlib import Path
from emulator import Emulator,ROOT
from orlegend import ROM,sha,observe
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('segments',nargs='+');a=p.parse_args();folders=[Path(x).resolve() for x in a.segments];out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
metas=[json.loads((f/'manifest.json').read_text()) for f in folders]
assert metas[0]['start']=='poweron'
for i in range(1,len(folders)):
 assert sha(folders[i]/'initial.state')==sha(folders[i-1]/'final.state'),f'Non-contiguous seam {i}'
 assert metas[i]['rom_sha256']==metas[0]['rom_sha256'] and metas[i]['core_sha256']==metas[0]['core_sha256']
e=Emulator(ROM,deterministic=True);assert sha(ROM)==metas[0]['rom_sha256'] and sha(e.core_path)==metas[0]['core_sha256']
n=0;coins=0;held=False;segments=[];seams=[];start=time.perf_counter()
try:
 with (out/'inputs.jsonl').open('w') as stream:
  for si,f in enumerate(folders):
   while not (f/'result.json').exists():time.sleep(1)
   result=json.loads((f/'result.json').read_text());begin=n
   for line in (f/'inputs.jsonl').read_text().splitlines():
    row=json.loads(line);keys=row['buttons'];assert row['frame']==n-begin+1
    e.step(keys);n+=1;stream.write(json.dumps({'frame':n,'buttons':keys})+'\n')
    pressed='coin' in keys;coins+=int(pressed and not held);held=pressed
    if n%20000==0:
     progress={'frame':n,'wall_seconds':time.perf_counter()-start,'segment':si,**observe(e.ram())};(out/'progress.json').write_text(json.dumps(progress,indent=2));print('PROGRESS',n,progress['stage_raw'],flush=True);e.picture().save(out/'current.png')
   assert n-begin==result['frames']
   actual=e.fingerprint();expected_state=sha(f/'final.state');expected_ram=sha(f/'final.ram')
   seam={'segment':si,'frame':n,'state_equal':actual['state']==expected_state,'ram_equal':actual['ram']==expected_ram,'actual':actual,'expected_state':expected_state,'expected_ram':expected_ram};seams.append(seam);print('SEAM',json.dumps(seam),flush=True)
   (out/'seams.json').write_text(json.dumps(seams,indent=2))
   if not seam['ram_equal']:raise RuntimeError('Cold replay RAM diverged at checkpoint seam')
   segments.append({'folder':str(f),'start_frame':begin,'end_frame':n,'inputs_sha256':sha(f/'inputs.jsonl'),'manifest_sha256':sha(f/'manifest.json')})
 expected=result['expected'];actual=e.fingerprint();equal=actual==expected
 replay={'equal':equal,'actual':actual,'expected':expected,'frames':n,'coins':coins,'continues':coins-1,'start':'poweron','restores':0,'wall_seconds':time.perf_counter()-start,'seams':seams}
 (out/'replay.json').write_text(json.dumps(replay,indent=2));(out/'manifest.json').write_text(json.dumps({**metas[0],'segments':segments,'start':'poweron','verification_restores':0,'full_game_clear_verified':False},indent=2))
 (out/'result.json').write_text(json.dumps({**result,'frames':n,'continues':coins-1,'expected':actual,'full_game_clear_verified':False},indent=2))
 (out/'final.state').write_bytes(e.save());(out/'final.ram').write_bytes(e.ram());e.picture().save(out/'final.png')
 for file in folders[-1].glob('ending-*.png'):shutil.copy2(file,out/file.name)
 print('VERIFIED',json.dumps(replay),flush=True)
 if not equal:raise RuntimeError('Final fingerprint mismatch')
finally:e.close()
