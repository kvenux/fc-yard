"""Calibrate skill commands after recovery, using raw action state and HP."""
import concurrent.futures,json,time
from emulator import Emulator
from kovsh import OUT,ROM,observe
COMMANDS=['normal','qcf','du','ud','dd','bf','dash','panic']
def test(name):
 e=Emulator(ROM,deterministic=True,headless=True);e.restore((OUT/'two-life-roof-001/frame-017400.state').read_bytes());before=observe(e.ram_view());rows=[];trace=[]
 for f in range(480):
  o=observe(e.ram_view());target=next((x for x in o['enemies'] if x['slot']==1),None);keys=[]
  if target:
   dx=target['x']-o['x'];dy=target['ground_y']-o['ground_y'];face='right' if dx>=0 else 'left';back='left' if dx>=0 else 'right'
   t=f%120
   if t<40:
    if abs(dy)>8:keys.append('down' if dy>0 else 'up')
    if abs(dx)>45 or o['facing']!=face:keys.append(face)
   elif t<75:keys=[]
   elif t<84:
    seq={'normal':[[face],[],['attack']],'qcf':[['down'],['down',face],[face,'attack']],'du':[['down'],['up'],['attack']],'ud':[['up'],['down'],['attack']],'dd':[['down'],[],['down','attack']],'bf':[[back],[face],['attack']],'dash':[[face],[],[face,'attack']],'panic':[['attack','jump']]*3}
    keys=seq[name][(t-75)//3]
  e.step(keys);trace.append(keys);r=e.ram_view();after=observe(r)
  rows.append({'frame':f+1,'state':list(r[0x1146a:0x1146e]),'hp':after['hp'],'enemies':[(x['slot'],x['hp']) for x in after['enemies']]})
  if after['hp']==0:break
 result={'command':name,'before':before,'after':after,'frames':len(rows),'raw_states':sorted(set(tuple(x['state']) for x in rows)),'trace':rows,'video_frames_copied':0}
 p=OUT/'skill-recovery-calibration-001';p.mkdir(exist_ok=True)
 (p/f'{name}.json').write_text(json.dumps(result));e.close();return result
if __name__=='__main__':
 t=time.perf_counter()
 with concurrent.futures.ProcessPoolExecutor(max_workers=4,max_tasks_per_child=1) as p:r=list(p.map(test,COMMANDS))
 for x in r:print(x['command'],'hp',x['after']['hp'],'boss',[(a['slot'],a['hp']) for a in x['after']['enemies'] if a['slot']==1],'states',x['raw_states'])
 print('seconds',time.perf_counter()-t)
