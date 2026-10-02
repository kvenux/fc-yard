"""Join checkpoint-contiguous training segments, then require cold replay verification."""
import argparse,json,hashlib,shutil
from pathlib import Path
from orlegend import sha
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('segments',nargs='+');a=p.parse_args();folders=[Path(v).resolve() for v in a.segments];out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
metas=[json.loads((f/'manifest.json').read_text()) for f in folders];results=[json.loads((f/'result.json').read_text()) for f in folders]
assert metas[0]['start']=='poweron'
for i in range(1,len(folders)):
 assert sha(folders[i]/'initial.state')==sha(folders[i-1]/'final.state'), 'Non-contiguous checkpoint seam'
 assert metas[i]['rom_sha256']==metas[0]['rom_sha256'] and metas[i]['core_sha256']==metas[0]['core_sha256']
n=0;segments=[]
with (out/'inputs.jsonl').open('w') as w:
 for f,result in zip(folders,results):
  start=n
  for row in (f/'inputs.jsonl').read_text().splitlines():
   record=json.loads(row);n+=1;w.write(json.dumps({'frame':n,'buttons':record['buttons']})+'\n')
  assert n-start==result['frames']
  segments.append({'folder':str(f),'start_frame':start,'end_frame':n,'inputs_sha256':sha(f/'inputs.jsonl'),'manifest_sha256':sha(f/'manifest.json')})
meta={**metas[0],'start':'poweron','segments':segments,'full_game_clear_verified':False,'method':'checkpoint-contiguous input concatenation; no restores during verification or playback'}
(out/'manifest.json').write_text(json.dumps(meta,indent=2))
result={**results[-1],'frames':n,'continues':sum(r['continues'] for r in results),'full_game_clear_verified':False,'segments':segments}
(out/'result.json').write_text(json.dumps(result,indent=2))
for file in ['final.state','final.ram','final.png',*[f.name for f in folders[-1].glob('ending-*.png')]]:shutil.copy2(folders[-1]/file,out/file)
print(json.dumps({'frames':n,'continues':result['continues'],'output':str(out)},indent=2))
