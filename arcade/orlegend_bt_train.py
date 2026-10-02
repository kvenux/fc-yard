"""Chapter-gated behavior tree evaluations and independent normal-input replay."""
import argparse,collections,json,time
from pathlib import Path
from emulator import Emulator
from orlegend import ROM,OUT,observe,sha
from orlegend_resources import resources
from orlegend_campaign import Controller as Legacy
from orlegend_bt import Controller,load

def observation(e):
 r=e.ram_view();o=observe(r);o['resources']=resources(r);o['player_state']=r[0x1be83];o['player_move']=r[0x1be82];o['player_facing']='left' if r[0x1bee2]&0x40 else 'right';o['air_mask']=r[0x1bee2]&0x30;o['door_open']=bool(r[0x1b8b1]);b=0xc266+r[0x11625]*0x98
 o['tree_hits']=r[0x11624];o['tree']=[int.from_bytes(r[b+0x14:b+0x16],'little'),int.from_bytes(r[b+0x16:b+0x18],'little')]
 for enemy in o['enemies']:
  b=0x11a40+enemy['slot']*0x13e;enemy.update(state=r[b+0x33],move=r[b+0x32],facing='left' if r[b+0x92]&0x40 else 'right',air_mask=r[b+0x92]&0x30)
 return o

def run(a):
 out=Path(a.output);out.mkdir(parents=True,exist_ok=False);spec=load(a.tree);bt=Controller(spec);old_ctrl=Legacy(spec['parameters']);e=Emulator(ROM,deterministic=True,headless=True)
 started=time.perf_counter();deaths=damage=continues=0;chapter_deaths=collections.Counter();hits=collections.Counter();history=[];health_events=[];health_context=[];recent=collections.deque(maxlen=a.trace_window or 1);last_scene=None;scene_entry={};frames=0;equivalent=True if a.compare_legacy or a.equivalence_inputs else None;reason='budget'
 sources=['behavior_tree.py','orlegend_bt.py','orlegend_bt_train.py','orlegend.py','orlegend_campaign.py','orlegend_resources.py','orlegend_survival.py','emulator.py']
 for name in sources:(out/name).write_bytes(Path(__file__).with_name(name).read_bytes())
 (out/'tree.json').write_text(json.dumps(spec,indent=2));meta={'start':'checkpoint' if a.state else 'poweron','tree_sha256':sha(a.tree),'rom_sha256':sha(ROM),'core_sha256':sha(e.core_path),'stop_stage':a.stop_stage,'restores':int(bool(a.state)),'first_death_ends':a.first_death,'continue_allowed':a.allow_continue,'sources':{n:sha(Path(__file__).with_name(n)) for n in sources},'equivalence_inputs':a.equivalence_inputs,'record':a.record}
 (out/'manifest.json').write_text(json.dumps(meta,indent=2));stream=(out/'inputs.jsonl').open('w') if a.record else None
 old=observation(e)
 def step(keys):
  nonlocal frames,deaths,damage,old
  e.step(keys);frames+=1;now=observation(e)
  if a.trace_window:recent.append({'frame':frames,'observation':old,'action':bt.last_action,'buttons':keys})
  if 0<=now['lives']<old['lives']<=2:
   lost=old['lives']-now['lives'];deaths+=lost;chapter_deaths[str(old['stage_byte']+1)]+=lost
   health_events.append({'frame':frames,'event':'death','before':old,'after':now,'action':bt.last_action,'buttons':keys})
  if 0<=now['hp']<old['hp']<=72:
   damage+=old['hp']-now['hp'];health_events.append({'frame':frames,'event':'damage','amount':old['hp']-now['hp'],'before':old,'after':now,'action':bt.last_action,'buttons':keys})
   if a.trace_window:health_context.append({'frame':frames,'context':list(recent)})
  if stream:stream.write(json.dumps({'frame':frames,'buttons':keys})+'\n')
  old=now
  return now
 try:
  if a.state:e.restore(Path(a.state).read_bytes());old=observation(e);(out/'initial.state').write_bytes(Path(a.state).read_bytes())
  if a.equivalence_inputs:
   for i,line in enumerate(Path(a.equivalence_inputs).open()):
    o=observation(e)
    if i>=2584:
     keys=bt.choose(o,i-2584);legacy=old_ctrl.choose(o,i-2584);hits[bt.last_action]+=1
     if keys!=legacy:
      equivalent=False;history.append({'frame':i+1,'bt':keys,'legacy':legacy,'observation':o});reason='mismatch';break
    step(json.loads(line)['buttons'])
    if (i+1)%100000==0:print('EQUIVALENCE',i+1,flush=True)
   else:reason='equivalent_recorded_trajectory'
  else:
   if not a.state:
    for line in (OUT/'boot-inputs.jsonl').open():step(json.loads(line)['buttons'])
   initial=observation(e)
   for f in range(a.frames):
    o=observation(e)
    if o['stage_raw']!=last_scene:
     last_scene=o['stage_raw'];scene_entry[str(last_scene)]={'frame':frames,**o}
     if a.record:(out/f'entry-{frames:07d}-{last_scene:04x}.state').write_bytes(e.save())
    keys=bt.choose(o,f)
    if a.compare_legacy:
     legacy=old_ctrl.choose(o,f)
     if keys!=legacy:equivalent=False;reason='mismatch';history.append({'frame':frames+1,'bt':keys,'legacy':legacy,'observation':o});break
    hits[bt.last_action]+=1;now=step(keys)
    if a.first_death and deaths:reason='first_death';break
    if a.stop_scene is not None and now['stage_raw']==a.stop_scene:reason='scene_passed';break
    if now['lives']==0 or now['lives']>=128:
     if not a.allow_continue:reason='lives_exhausted';break
     continues+=1
     for cf in range(1800):
      now=step(['coin'] if cf in (120,121) else ['start'] if cf>180 and cf%60<2 else ['attack'] if cf%60==20 else [])
      if cf>240 and now['lives'] in (1,2):break
     if now['lives'] not in (1,2):reason='continue_failed';break
    if now['stage_byte']>=a.stop_stage:reason='chapter_passed';break
   if reason=='chapter_passed' and a.stop_stage==8:
    for _ in range(3600):step([])
  fp=e.fingerprint();result={'reason':reason,'frames':frames,'deaths':deaths,'chapter_deaths':dict(chapter_deaths),'damage':damage,'continues':continues,'after':observation(e),'scene_entries':scene_entry,'node_ticks':dict(hits),'events':bt.events,'health_events':health_events,'equivalent':equivalent,'mismatches':history,'fingerprint':fp,'wall_seconds':time.perf_counter()-started}
  (out/'result.json').write_text(json.dumps(result,indent=2));(out/'final.state').write_bytes(e.save());print(json.dumps(result),flush=True)
  if a.trace_window:(out/'health-context.json').write_text(json.dumps(health_context,indent=2))
 finally:
  if stream:stream.close()
  e.close()

def replay(a):
 out=Path(a.output);m=json.loads((out/'manifest.json').read_text());result=json.loads((out/'result.json').read_text());e=Emulator(ROM,deterministic=True,headless=True);deaths=0;chapter_deaths=collections.Counter();old=observe(e.ram_view());started=time.perf_counter()
 try:
  if a.core_render:e.av_enable=3
  assert sha(ROM)==m['rom_sha256'] and sha(e.core_path)==m['core_sha256']
  if m['start']=='checkpoint':e.restore((out/'initial.state').read_bytes());old=observe(e.ram_view())
  for i,line in enumerate((out/'inputs.jsonl').open()):
   if m['stop_stage']==8 and i==result['frames']-3600:e.headless=False;e.av_enable=3
   e.step(json.loads(line)['buttons']);now=observe(e.ram_view())
   if 0<=now['lives']<old['lives']<=2:
    lost=old['lives']-now['lives'];deaths+=lost;chapter_deaths[str(old['stage_byte']+1)]+=lost
   old=now
   if m['stop_stage']==8 and i>=result['frames']-3600 and (i+1)%300==0:e.picture().save(out/f'verified-ending-{i+1:07d}.png')
   if (i+1)%100000==0:print('REPLAY',i+1,flush=True)
  fp=e.fingerprint();eq=all(fp[k]==result['fingerprint'][k] for k in ('state','ram'))
  evidence={'equal':eq,'death_count_equal':deaths==result['deaths'],'deaths':deaths,'chapter_deaths':dict(chapter_deaths),'frames':i+1,'start':m['start'],'restores':m['restores'],'after':now,'fingerprint':fp,'core_render_entire_run':a.core_render,'wall_seconds':time.perf_counter()-started};(out/('replay-render.json' if a.core_render else 'replay.json')).write_text(json.dumps(evidence,indent=2));print(json.dumps(evidence),flush=True)
 finally:e.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--tree',default='arcade/orlegend-bt-baseline.json');p.add_argument('--output',required=True);p.add_argument('--state');p.add_argument('--frames',type=int,default=60000);p.add_argument('--stop-stage',type=int,default=1);p.add_argument('--stop-scene',type=int);p.add_argument('--trace-window',type=int,default=0);p.add_argument('--allow-continue',action='store_true');p.add_argument('--first-death',action='store_true');p.add_argument('--compare-legacy',action='store_true');p.add_argument('--equivalence-inputs');p.add_argument('--record',action='store_true');p.add_argument('--replay',action='store_true');p.add_argument('--core-render',action='store_true',help='Replay with core drawing enabled for every frame');a=p.parse_args();replay(a) if a.replay else run(a)
