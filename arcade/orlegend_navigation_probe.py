"""Checkpoint practice for geometry/input calibration, never a clear claim."""
import argparse,itertools,json
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--output',required=True);p.add_argument('--frames',type=int,default=600);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
e=Emulator(ROM,deterministic=True,headless=True);state=Path(a.state).read_bytes();rows=[]
try:
 for direction,jump,attack in itertools.product(['up','down','left','right','down,left','down,right','up,left','up,right'],[0,30],[0,4]):
  e.restore(state);samples=[];initial=observation(e)
  for f in range(a.frames):
   keys=direction.split(',')+(['attack'] if attack and f%attack<2 else [])
   if jump and f%jump<2:keys=[k for k in keys if k not in ('attack','down')]+['jump']
   if f in (0,a.frames-1):e.headless=False;e.av_enable=3
   e.step(keys)
   if f==0:e.headless=True;e.av_enable=2
   if f%60==59:samples.append({'frame':f+1,**observation(e)})
   if observation(e)['lives']<initial['lives']:break
  name=direction.replace(',','-')+f'-j{jump}-a{attack}'
  if e.picture() is not None:e.picture().save(out/(name+'.png'))
  e.headless=True;e.av_enable=2
  rows.append({'name':name,'initial':initial,'after':observation(e),'samples':samples})
  (out/'summary.json').write_text(json.dumps({'scope':'checkpoint practice only','results':rows},indent=2));print(name,observation(e),flush=True)
finally:e.close()
