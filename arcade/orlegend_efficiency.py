"""Life-cost evaluations using normal inputs, headless core, isolated process."""
import argparse,json,time,sys,subprocess,concurrent.futures
from pathlib import Path
from emulator import Emulator
from orlegend import ROM,OUT,observe,sha
from orlegend_campaign import Controller

def rollout(a):
 out=Path(a.output);out.mkdir(parents=True,exist_ok=False);cfg=json.loads(a.config);e=Emulator(ROM,deterministic=True,headless=True);ctrl=Controller(cfg)
 start=time.perf_counter();deaths=0;continues=0;frame=0;scene_deaths={};trace=(out/'inputs.jsonl').open('w') if a.record else None
 old=observe(e.ram_view());initial=None
 def step(keys):
  nonlocal frame,deaths,old
  e.step(keys);frame+=1;now=observe(e.ram_view())
  if 0<=now['lives']<old['lives']<=2:
   lost=old['lives']-now['lives'];deaths+=lost;s=str(old['stage_raw']);scene_deaths[s]=scene_deaths.get(s,0)+lost
  old=now
  if trace:trace.write(json.dumps({'frame':frame,'buttons':keys})+'\n')
  return now
 try:
  if a.state:e.restore(Path(a.state).read_bytes());old=observe(e.ram_view())
  else:
   source=Path(a.prefix) if a.prefix else OUT/'boot-inputs.jsonl'
   for i,line in enumerate(source.open()):
    if a.prefix and i>=a.prefix_frames:break
    row=json.loads(line);step(row['buttons']);continues+=int('coin' in row['buttons'] and i>2584 and (i==0 or not prior_coin));prior_coin='coin' in row['buttons']
  initial=observe(e.ram_view());initial_scene=initial['stage_raw'];policy_start=frame;reason='budget'
  for f in range(a.frames):
   r=e.ram_view();o=observe(r);o['door_open']=bool(r[0x1b8b1]);b=0xc266+r[0x11625]*0x98;o['tree_hits']=r[0x11624];o['tree']=[int.from_bytes(r[b+0x14:b+0x16],'little'),int.from_bytes(r[b+0x16:b+0x18],'little')]
   now=step(ctrl.choose(o,f))
   if now['lives']==0 or now['lives']>=128:
    continues+=1
    for cf in range(1800):
     now=step(['coin'] if cf in (120,121) else ['start'] if cf>180 and cf%60<2 else ['attack'] if cf%60==20 else [])
     if cf>240 and now['lives'] in (1,2):break
    if now['lives'] not in (1,2):reason='continue_failed';break
   if a.segment and now['stage_raw']!=initial_scene:reason='scene_passed';break
   if now['stage_byte']>=8:
    reason='ending_candidate'
    for _ in range(3600):step([])
    break
  result={'scope':'checkpoint_practice' if a.state else 'cold_start','initial':initial,'after':observe(e.ram_view()),'frames':frame,'policy_frames':frame-policy_start,'deaths':deaths,'continues':continues,'scene_deaths':scene_deaths,'reason':reason,'wall_seconds':time.perf_counter()-start,'fingerprint':e.fingerprint(),'config':cfg}
  (out/'result.json').write_text(json.dumps(result,indent=2));(out/'manifest.json').write_text(json.dumps({'rom':sha(ROM),'core':sha(e.core_path),'source':sha(__file__),'frontend':sha(Path(__file__).with_name('emulator.py')),'policy':sha(Path(__file__).with_name('orlegend_campaign.py')),'state':sha(a.state) if a.state else None,'prefix':sha(a.prefix) if a.prefix else None,'prefix_frames':a.prefix_frames},indent=2));(out/'final.state').write_bytes(e.save());print(json.dumps(result),flush=True)
 finally:
  if trace:trace.close()
  e.close()

def batch(a):
 out=Path(a.output);out.mkdir(parents=True,exist_ok=False);base=json.loads((OUT/'full-policy-cold-05/policy.json').read_text());configs=[base]
 for offset in (16,32,48):
  for distance in (32,64):
   for jump in (0,90):
    c=json.loads(json.dumps(base));c['scenes']['1793']={'enemy_y_offset':offset,'distance':distance,'align':10,'jump':jump,'rush':0};configs.append(c)
 (out/'configs.json').write_text(json.dumps(configs,indent=2));results=[];start=time.perf_counter()
 def job(pair):
  n,c=pair;p=out/f'candidate-{n:03d}';cmd=[sys.executable,__file__,'--output',str(p),'--config',json.dumps(c),'--state',a.state,'--frames',str(a.frames),'--segment'];proc=subprocess.run(cmd,capture_output=True,text=True)
  if proc.returncode:raise RuntimeError(proc.stderr)
  return {'candidate':n,**json.loads((p/'result.json').read_text())}
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
  for fut in concurrent.futures.as_completed([pool.submit(job,p) for p in enumerate(configs)]):
   results.append(fut.result());(out/'progress.json').write_text(json.dumps({'completed':len(results),'total':len(configs),'wall_seconds':time.perf_counter()-start}));print('DONE',len(results),flush=True)
 results.sort(key=lambda r:(r['reason']!='scene_passed',r['deaths'],r['policy_frames']));(out/'results.json').write_text(json.dumps(results,indent=2));(out/'best-policy.json').write_text(json.dumps(results[0]['config'],indent=2));print('BEST',json.dumps(results[0]),flush=True)

def replay(a):
 folder=Path(a.output);expected=json.loads((folder/'result.json').read_text());e=Emulator(ROM,deterministic=True,headless=True);deaths=0;old=observe(e.ram_view());start=time.perf_counter();total=expected['frames']
 try:
  for i,line in enumerate((folder/'inputs.jsonl').open()):
   # Only render the final ending window for visual acceptance.
   if i==total-3600:e.headless=False;e.av_enable=3
   e.step(json.loads(line)['buttons']);now=observe(e.ram_view())
   if 0<=now['lives']<old['lives']<=2:deaths+=old['lives']-now['lives']
   old=now
   if i>=total-3600 and (i+1)%300==0:e.picture().save(folder/f'verified-ending-{i+1:07d}.png')
   if (i+1)%100000==0:print('REPLAY',i+1,flush=True)
  actual=e.fingerprint();equal=all(actual[k]==expected['fingerprint'][k] for k in ['state','ram'])
  result={'equal':equal,'actual':actual,'expected':expected['fingerprint'],'deaths':deaths,'death_count_equal':deaths==expected['deaths'],'start':'poweron','restores':0,'after':old,'wall_seconds':time.perf_counter()-start};(folder/'replay.json').write_text(json.dumps(result,indent=2));e.picture().save(folder/'verified-final.png');print(json.dumps(result),flush=True)
 finally:e.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--config');p.add_argument('--state');p.add_argument('--prefix');p.add_argument('--prefix-frames',type=int,default=0);p.add_argument('--frames',type=int,default=120000);p.add_argument('--segment',action='store_true');p.add_argument('--record',action='store_true');p.add_argument('--batch',action='store_true');p.add_argument('--replay',action='store_true');a=p.parse_args();replay(a) if a.replay else batch(a) if a.batch else rollout(a)
