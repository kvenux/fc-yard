"""Join the audited fourth-chapter prefix and ordinary-input boss practice plan."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--boss-plan',required=True);p.add_argument('--output',required=True);a=p.parse_args()
root=Path('arcade/runs/orlegend/bt')
first=json.loads((root/'one-life-ch4-plan-candidate-02.json').read_text())
second=json.loads((root/'one-life-ch4-second-parallel-beam-practice-03/plan.json').read_text())
boss=json.loads(Path(a.boss_plan).read_text());remaining=2728;prefix=[]
for m in second['macros']:
 n=min(remaining,len(m['inputs']))
 if n:prefix.append({'name':m['name'],'inputs':m['inputs'][:n]})
 remaining-=n
 if not remaining:break
assert remaining==0
pickup=json.loads((root/'one-life-ch4-shell-practice-02/None-0-25-inputs.json').read_text())[:101]
plan={'initial':first['initial'],'after':boss['after'],'macros':first['macros']+prefix+[{'name':'shell_pickup','inputs':pickup}]+boss['macros'],
      'scope':'ordinary-input candidate requires cold verification','provenance':{'first':str(root/'one-life-ch4-plan-candidate-02.json'),'second_prefix_frames':2728,'pickup_frames':101,'boss':a.boss_plan}}
Path(a.output).write_text(json.dumps(plan,indent=2));print(sum(len(m['inputs']) for m in plan['macros']))
