"""Read-only native command calibration; no video, no randomness."""
import concurrent.futures,json,time,sys
from pathlib import Path
from emulator import Emulator
from kovsh import ROM,OUT,observe,action
COMMANDS=['hold_attack','tap_attack','normal_combo','dash_strike','back_slash','upper_counter','vertical_sweep','low_sweep','quarter_circle','jump_attack']
def trial(name):
 e=Emulator(ROM,deterministic=True,headless=True);e.restore((OUT/'two-life-001/frame-047400.state').read_bytes())
 before=observe(e.ram_view());previous=before;damage=0;events=[];modes={};t=time.perf_counter();trace=[]
 c=dict(period=4,distance=32,align=8,jump=0,face_period=60,ground_alignment=True,facing_feedback=True)
 special={'dash_strike':'dash','back_slash':'bf','upper_counter':'ud','vertical_sweep':'du','low_sweep':'dd','quarter_circle':'qcf'}.get(name)
 if special:c.update(special=special,special_period=36)
 for f in range(1800):
  o=observe(e.ram_view());keys=action(o,f,c)
  if name=='hold_attack' and o['enemies']:keys=list(set(keys+['attack']))
  elif name=='tap_attack' and o['enemies']:keys=[k for k in keys if k!='attack']+(['attack'] if f%12==0 else [])
  elif name=='jump_attack' and o['enemies']:keys=keys+(['jump'] if f%36<2 else [])
  e.step(keys);trace.append(keys);after=observe(e.ram_view());current={x['slot']:x['hp'] for x in after['enemies']}
  step_damage=sum(max(0,x['hp']-current.get(x['slot'],0)) for x in previous['enemies']);damage+=step_damage
  if step_damage:events.append({'frame':f+1,'damage':step_damage,'hp':after['hp'],'player_state':list(e.ram_view()[0x1146a:0x1146e])})
  signature=bytes(e.ram_view()[0x1146a:0x1146e]).hex();modes[signature]=modes.get(signature,0)+1
  previous=after
  if after['hp']==0 or after['lives']<before['lives']:break
 result={'command':name,'frames':f+1,'seconds':time.perf_counter()-t,'enemy_damage':damage,'after':after,'before':before,'hit_events':events,'action_states':modes,'video_frames_copied':0}
 folder=OUT/'bamboo-command-calibration-001'/name;folder.mkdir(parents=True,exist_ok=False)
 (folder/'result.json').write_text(json.dumps(result,indent=2));(folder/'inputs.jsonl').write_text(''.join(json.dumps({'frame':i+1,'buttons':k})+'\n' for i,k in enumerate(trace)));e.close();return result
if __name__=='__main__':
 start=time.perf_counter()
 with concurrent.futures.ProcessPoolExecutor(max_workers=4,max_tasks_per_child=1) as pool:
  results=list(pool.map(trial,COMMANDS))
 out={'results':results,'seconds':time.perf_counter()-start,'source_state':'two-life-001/frame-047400.state','scope':'command_calibration','no_rendering':True}
 (OUT/'bamboo-command-calibration-001/report.json').write_text(json.dumps(out,indent=2))
 for r in results:print(r['command'],r['frames'],r['enemy_damage'],r['after']['hp'],r['after']['x'],r['after']['score']-r['before']['score'])
 print('seconds',out['seconds'])
