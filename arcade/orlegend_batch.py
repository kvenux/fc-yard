"""Parallel isolated headless evaluations, stop on first death. No RAM writes."""
import argparse, concurrent.futures, json, random, subprocess, sys, time
from pathlib import Path

def main(a):
 out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
 base=json.loads(Path(__file__).with_name('orlegend-policy.json').read_text());base['allow_continue']=False
 rng=random.Random(a.seed);configs=[base]
 for n in range(a.episodes-1):
  c=json.loads(json.dumps(base));c.update(combat='combo' if n%2==0 else 'rush',stand_distance=rng.choice([32,48,64,80,96]),stand_align=rng.choice([4,8,14,24]),offset=rng.choice([-24,-16,0,16,24]),cycle=rng.choice([16,24,32,48,64]))
  if a.boss_only:
   for scene in ('0','1','2'):c['scenes'][scene]['combat']='legacy'
   c.update(direct_boss_items=n%3!=0,boss_item_cycle=rng.choice([45,90,150,210]),boss_item_min_hp=rng.choice([20,40,100]))
  configs.append(c)
 (out/'configs.json').write_text(json.dumps(configs,indent=2));started=time.perf_counter();results=[]
 def job(pair):
  n,c=pair;folder=out/f'candidate-{n:03d}'
  cmd=[sys.executable,str(Path(__file__).with_name('orlegend_survival.py')),'--output',str(folder),'--config',json.dumps(c),'--headless','--compact','--frames',str(a.frames),'--stop-stage',str(a.stop_stage)]
  if a.state:cmd+=['--state',a.state]
  proc=subprocess.run(cmd,capture_output=True,text=True)
  if proc.returncode:raise RuntimeError(f'{n}: {proc.stderr}')
  r=json.loads((folder/'result.json').read_text());return {'candidate':n,'config':c,**r}
 with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
  for future in concurrent.futures.as_completed([pool.submit(job,pair) for pair in enumerate(configs)]):
   results.append(future.result());elapsed=time.perf_counter()-started
   progress={'completed':len(results),'episodes':a.episodes,'seconds':elapsed,'frames':sum(r['frames'] for r in results),'stage_goal':sum(r['reason']=='stage_goal' for r in results)}
   (out/'progress.json').write_text(json.dumps(progress));print(json.dumps(progress),flush=True)
 # For the calibrated first chapter, rank progress and boss damage ahead of
 # survival duration: standing still longer is not an improved strategy.
 if a.stop_stage==1 and not a.state:
  results.sort(key=lambda r:(r['max_stage'],r['reason']=='stage_goal',r['after']['scene_byte'],r['after']['hp'] if r['reason']=='stage_goal' else -sum(e['hp'] for e in r['after']['enemies']),-r['damage']),reverse=True)
 else:
  results.sort(key=lambda r:(r['max_stage'],r['reason']=='stage_goal',r['after']['hp'] if r['reason']=='stage_goal' else -999,-r['damage'],r['frames']),reverse=True)
 elapsed=time.perf_counter()-started;frames=sum(r['frames'] for r in results)
 summary={'episodes':len(results),'workers':a.workers,'scope':'checkpoint_practice' if a.state else 'cold_start_first_life','wall_seconds':elapsed,'total_frames':frames,'aggregate_fps':frames/elapsed,'episodes_per_minute':len(results)*60/elapsed,'stage_goal_count':sum(r['reason']=='stage_goal' for r in results),'best':results[0]}
 (out/'results.json').write_text(json.dumps(results,indent=2));(out/'summary.json').write_text(json.dumps(summary,indent=2));print('BATCH_DONE',json.dumps(summary),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--episodes',type=int,default=64);p.add_argument('--workers',type=int,default=6);p.add_argument('--frames',type=int,default=45000);p.add_argument('--stop-stage',type=int,default=1);p.add_argument('--state');p.add_argument('--seed',type=int,default=20261002);p.add_argument('--boss-only',action='store_true');main(p.parse_args())
