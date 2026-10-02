"""One-life experiments: first lost life ends evaluation; no credits or game writes."""
import argparse,json,time
from pathlib import Path
from emulator import Emulator
from orlegend import ROM,OUT,observe,sha,action
from orlegend_campaign import Controller
from orlegend_resources import Items,resources

class Combat:
 def __init__(self):self.target=None;self.face=None
 def __call__(self,o,f,c):
  if c.get('combat','legacy')=='legacy':return action(o,f,c)
  enemies=[e for e in o['enemies'] if -1000<e['x']<10000 and 0<e['y']<1000]
  if not enemies:return ['right']+(['attack'] if f%4<2 else [])
  candidates=[e for e in enemies if e['slot']==self.target and abs(e['x']-o['x'])<300]
  enemy=min(candidates or enemies,key=lambda e:abs(e['x']-o['x'])+3*abs(e['y']-o['y']))
  self.target=enemy['slot'];dx=enemy['x']-o['x'];dy=enemy['y']+c.get('offset',0)-o['y'];face='right' if dx>=0 else 'left'
  keys=[];distance=c.get('stand_distance',56)
  if abs(dy)>c.get('stand_align',8):keys.append('down' if dy>0 else 'up')
  if abs(dx)>distance or face!=self.face or f%60==0:keys.append(face);self.face=face
  mode=c['combat'];cycle=c.get('cycle',32);phase=f%cycle
  if mode=='combo':
   if phase in (0,1,4,5):keys.append('attack')
   elif phase in (8,9) and abs(dx)<120 and abs(dy)<24:return [face,'down','jump']
   return keys
  if mode=='rush' and abs(dx)<140 and abs(dy)<24 and phase<2:return [face,'down','jump']
  if mode=='cancel':
   if phase<2:keys.append('c')
   elif 4<=phase<6:keys.append('attack')
  elif f%4<2:keys.append('attack')
  if c.get('combat_jump') and f%c['combat_jump']<2:keys=[k for k in keys if k!='attack']+['jump']
  return keys

def run(a):
 out=Path(a.output);out.mkdir(parents=True,exist_ok=False);cfg=json.loads(a.config)
 compact=getattr(a,'compact',False);headless=getattr(a,'headless',False);total=0
 e=Emulator(ROM,deterministic=True,headless=headless);ctrl=Controller(cfg,Combat());items=Items();trace=[];events=[];samples=[];damage=0;reason='budget';started=time.perf_counter();item_until=-1;item_events=[];last_inventory=None
 meta={'start':'checkpoint' if a.state else 'poweron','rom_sha256':sha(ROM),'core_sha256':sha(e.core_path),'source_sha256':sha(__file__),'controller_sha256':sha(Path(__file__).with_name('orlegend_campaign.py')),'initial_state_sha256':sha(a.state) if a.state else None,'first_death_ends':True,'continue_allowed':False,'config':cfg,'headless':headless,'compact':compact,'frontend_sha256':sha(Path(__file__).with_name('emulator.py'))}
 (out/'manifest.json').write_text(json.dumps(meta,indent=2));(out/'source.py').write_bytes(Path(__file__).read_bytes())
 def step(keys):
  assert 'coin' not in keys and 'start' not in keys
  nonlocal total
  e.step(keys);total+=1
  if not compact:trace.append({'frame':total,'buttons':keys})
 try:
  if a.state:e.restore(Path(a.state).read_bytes());(out/'initial.state').write_bytes(Path(a.state).read_bytes())
  else:
   for line in (OUT/'boot-inputs.jsonl').read_text().splitlines():
    row=json.loads(line);e.step(row['buttons']);total+=1
    if not compact:trace.append(row)
  initial=old=observe(e.ram_view());first_lives=initial['lives'];max_stage=initial['stage_byte']
  for f in range(a.frames):
   r=e.ram_view();o=observe(r);o['door_open']=bool(r[0x1b8b1]);b=0xc266+r[0x11625]*0x98
   o['tree_hits']=r[0x11624];o['tree']=[int.from_bytes(r[b+0x14:b+0x16],'little'),int.from_bytes(r[b+0x16:b+0x18],'little')]
   res=resources(r);inventory=res['inventory']
   if not compact and last_inventory is not None and inventory!=last_inventory:item_events.append({'frame':total,'before':last_inventory,'after':inventory})
   last_inventory=inventory
   danger=[x for x in o['enemies'] if abs(x['x']-o['x'])<220 and abs(x['y']-o['y'])<80]
   if cfg.get('direct_boss_items') and o['stage_raw']==3 and inventory and any(x['hp']>=cfg.get('boss_item_min_hp',40) for x in danger) and f%cfg.get('boss_item_cycle',120)<2:
    keys=['d']
   elif cfg.get('items_v2'):
    item_keys=items.act(o,res,f,cfg);keys=item_keys if item_keys is not None else ctrl.choose(o,f)
   elif cfg.get('items') and f>=item_until and sum(x['count'] for x in inventory)>0 and danger and (o['hp']<=cfg.get('item_hp',40) or cfg.get('item_boss') and any(x['hp']>=100 for x in danger)):
    item_until=f+cfg.get('item_wait',210);keys=['d'];item_events.append({'frame':total+1,'attempt':'D','inventory':inventory,'hp':o['hp']})
   elif f<item_until:keys=[]
   else:keys=ctrl.choose(o,f)
   step(keys);now=observe(e.ram_view())
   lost=max(0,old['hp']-now['hp']) if 0<=now['hp']<old['hp']<=72 else 0
   if lost:
    damage+=lost
    if not compact:events.append({'frame':total,'damage':lost,'before':old,'after':now,'buttons':keys})
   old=now;max_stage=max(max_stage,now['stage_byte'])
   if not compact and f%600==599:samples.append({'frame':total,**now})
   if now['lives']<first_lives:reason='first_death';break
   if now['stage_byte']>=a.stop_stage:reason='stage_goal';break
  result={'frames':total,'policy_frames':f+1,'initial':initial,'after':now,'max_stage':max_stage,'damage':damage,'deaths':int(now['lives']<first_lives),'reason':reason,'wall_seconds':time.perf_counter()-started,'expected':e.fingerprint()}
  result['simulated_fps']=total/result['wall_seconds'];result['realtime_multiplier']=result['simulated_fps']/e.fps
  (out/'result.json').write_text(json.dumps(result,indent=2))
  if not compact:
   for name,data in [('item-controller-events',items.events),('item-events',item_events),('samples',samples),('events',events)]:
    (out/(name+'.json')).write_text(json.dumps(data,indent=2))
   (out/'inputs.jsonl').write_text('\n'.join(map(json.dumps,trace))+'\n');(out/'final.state').write_bytes(e.save())
  if not headless:e.picture().save(out/'final.png')
  print(json.dumps(result),flush=True)
 finally:e.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--config',required=True);p.add_argument('--state');p.add_argument('--frames',type=int,default=45000);p.add_argument('--stop-stage',type=int,default=1);p.add_argument('--headless',action='store_true');p.add_argument('--compact',action='store_true');run(p.parse_args())
