"""Read-only, cold-replay damage/life ledger for an existing ordinary-input run."""
import argparse,json,time
from collections import Counter,defaultdict,deque
from pathlib import Path
from emulator import Emulator
from orlegend import ROM,observe,sha

p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=False)
meta=json.loads((a.run/'manifest.json').read_text());assert meta['start']=='poweron'
e=Emulator(ROM,deterministic=True);assert sha(ROM)==meta['rom_sha256'] and sha(e.core_path)==meta['core_sha256']
stats=defaultdict(Counter);deaths=[];gains=[];recent=deque(maxlen=180);previous=None;checkpoint=None;started=time.perf_counter();coins=0;coinheld=False;lastcoin=-10000
try:
 with (a.run/'inputs.jsonl').open() as stream,(a.output/'events.jsonl').open('w') as events:
  for frame,line in enumerate(stream,1):
   row=json.loads(line);assert row['frame']==frame;keys=row['buttons'];e.step(keys);o=observe(e.ram())
   pressed='coin' in keys
   if pressed and not coinheld:coins+=1;lastcoin=frame
   coinheld=pressed
   if frame<2584:continue
   scene=str(o['stage_raw']);s=stats[scene];s['frames']+=1;s['attack_frames']+=int('attack' in keys);s['ab_frames']+=int('attack' in keys and 'jump' in keys)
   recent.append({'frame':frame,'buttons':keys,**o})
   if previous:
    before=previous
    damage=max(0,before['hp']-o['hp']) if 0<=o['hp']<before['hp']<=72 and before['stage_raw']==o['stage_raw'] else 0
    death=0<=o['lives']<before['lives']<=10
    if damage:s['damage']+=damage;s['damage_events']+=1
    if death:
     count=before['lives']-o['lives'];s['deaths']+=count
     item={'frame':frame,'scene':o['stage_raw'],'lost':count,'before':before,'after':o,'buttons':keys};deaths.append(item)
     if len(deaths)<=3:
      stem=a.output/f'death-{len(deaths):03d}'
      e.picture().save(stem.with_suffix('.png'));stem.with_suffix('.json').write_text(json.dumps(list(recent),indent=2))
      if checkpoint:
       f,state=checkpoint;stem.with_suffix('.state').write_bytes(state);stem.with_suffix('.origin.json').write_text(json.dumps({'frame':f,'scope':'practice checkpoint before death; not a complete run'}))
    if 0<=before['lives']<o['lives']<=10:
     gains.append({'frame':frame,'before':before['lives'],'after':o['lives'],'recent_coin':frame-lastcoin<1800,'scene':o['stage_raw']})
    if damage or death:events.write(json.dumps({'frame':frame,'damage':damage,'death':death,'before':before,'after':o,'buttons':keys})+'\n')
   previous=o
   if frame%120==0 and len(deaths)<3:checkpoint=(frame,e.save())
   if frame%20000==0:
    progress={'frame':frame,'deaths':sum(x['lost'] for x in deaths),'coins':coins,'wall':time.perf_counter()-started,**o}
    (a.output/'progress.json').write_text(json.dumps(progress,indent=2));events.flush();print(progress,flush=True)
 actual=e.fingerprint();expected=json.loads((a.run/'result.json').read_text())['expected']
 result={'frames':frame,'deaths':sum(x['lost'] for x in deaths),'death_events':deaths,'life_gains':gains,'coins':coins,'remaining':previous['lives'],'scenes':dict(stats),'replay_equal':actual==expected,'actual':actual,'expected':expected,'source_inputs_sha256':sha(a.run/'inputs.jsonl'),'wall':time.perf_counter()-started}
 (a.output/'result.json').write_text(json.dumps(result,indent=2));assert result['replay_equal'];print('DONE',result['deaths'],flush=True)
finally:e.close()
