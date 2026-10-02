"""Strict promotion gate: chapter passes, fewer deaths, cold replay, repeat, prefix."""
import argparse,json
from pathlib import Path

def promote(a):
 baseline=Path(a.baseline);candidate=Path(a.candidate);repeat=Path(a.repeat)
 read=lambda p,n:json.loads((p/n).read_text())
 b=read(baseline,'result.json');c=read(candidate,'result.json');r=read(repeat,'result.json');v=read(candidate,'replay.json');m=read(candidate,'manifest.json')
 prefix_frames=0
 if a.previous:
  prefix=(Path(a.previous)/'inputs.jsonl').read_text().splitlines();rows=(candidate/'inputs.jsonl').read_text().splitlines();prefix_frames=len(prefix)
  assert rows[:prefix_frames]==prefix,'Earlier accepted chapter inputs changed'
 assert c['reason']=='chapter_passed' and c['after']['stage_byte']>=a.stage
 assert c['deaths']<b['deaths'],'No strict reduction in deaths'
 assert c['fingerprint']==r['fingerprint'] and c['deaths']==r['deaths'],'Cold repeat differs'
 assert v['equal'] and v['death_count_equal'] and v['start']=='poweron' and v['restores']==0
 assert m['start']=='poweron' and m['restores']==0
 inv=lambda x:{i['id']:i['count'] for i in x['after']['resources']['inventory']}
 assert all(inv(c).get(k,0)>=n for k,n in inv(b).items()),'Candidate spends remaining inventory'
 evidence={'accepted':True,'stage':a.stage,'baseline_deaths':b['deaths'],'candidate_deaths':c['deaths'],'cold_repeat_equal':True,'independent_replay_equal':True,'earlier_prefix_frames_equal':prefix_frames,'inventory_not_reduced':True,'candidate':str(candidate),'repeat':str(repeat)}
 tree=read(candidate,'tree.json');tree['name']=f'accepted-through-chapter-{a.stage}';tree['validation']=evidence;Path(a.output).write_text(json.dumps(tree,indent=2))
 ledger=Path(a.ledger);ledger.parent.mkdir(parents=True,exist_ok=True)
 with ledger.open('a') as f:f.write(json.dumps(evidence)+'\n')
 print(json.dumps(evidence))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--stage',type=int,required=True);p.add_argument('--baseline',required=True);p.add_argument('--candidate',required=True);p.add_argument('--repeat',required=True);p.add_argument('--previous');p.add_argument('--output',default='arcade/orlegend-bt-policy.json');p.add_argument('--ledger',default='arcade/runs/orlegend/bt/promotions.jsonl');promote(p.parse_args())
