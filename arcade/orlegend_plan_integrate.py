"""Embed practice input plans as a scene-scoped behavior-tree leaf."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--base',required=True);p.add_argument('--output',required=True);p.add_argument('--start-frame',type=int);p.add_argument('--scenes');a=p.parse_args()
plan=json.loads(Path(a.plan).read_text());spec=json.loads(Path(a.base).read_text());runs=[]
for macro in plan['macros']:
    for buttons in macro['inputs']:
        if runs and runs[-1]['buttons']==buttons:runs[-1]['frames']+=1
        else:runs.append({'buttons':buttons,'frames':1})
frames=sum(v['frames'] for v in runs)
guard={'scenes':list(map(int,a.scenes.split(','))) if a.scenes else [plan['initial']['stage_raw']],'frames':frames};action={'runs':runs}
if a.start_frame is not None:guard['start_frame']=action['start_frame']=a.start_frame
spec['tree']['children'].insert(0,{'type':'sequence','children':[{'type':'condition','name':'plan_ready','params':guard},{'type':'action','name':'input_plan','params':action}]})
spec['validation']={'scope':'unverified candidate; practice plan requires cold replay','practice_plan':a.plan}
Path(a.output).write_text(json.dumps(spec,indent=2));print(frames)
