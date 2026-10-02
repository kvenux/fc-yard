"""Global gate is separate from chapter practice: only a verified lower-cost clear."""
import argparse,json
from pathlib import Path

def gate(a):
 baseline=Path(a.baseline);candidate=Path(a.candidate)
 b=json.loads((baseline/'result.json').read_text());c=json.loads((candidate/'result.json').read_text());m=json.loads((candidate/'manifest.json').read_text())
 verdict={'baseline':str(baseline),'candidate':str(candidate),'baseline_deaths':b['deaths'],'candidate_deaths':c['deaths'],'accepted':False,'scope':'full_game'}
 if c['reason']!='chapter_passed' or c['after']['stage_byte']<8:verdict['reason']='no full clear'
 elif c['deaths']>=b['deaths']:verdict['reason']='no strict full-game death reduction'
 else:
  v=json.loads((candidate/'replay.json').read_text())
  assert v['equal'] and v['death_count_equal'] and v['start']=='poweron' and v['restores']==0
  assert m['start']=='poweron' and m['restores']==0 and a.ending_reviewed
  verdict.update(accepted=True,reason='lower full-game deaths with independent replay and ending review',continues=c['continues'],lives_used_including_survivor=c['deaths']+1,visual_ending_verified=True,state_and_ram_replay_equal=True)
  tree=json.loads((candidate/'tree.json').read_text());tree['name']='accepted-full-game';tree['validation']=verdict;Path(a.output).write_text(json.dumps(tree,indent=2))
  c['full_game_clear_verified']=True;(candidate/'result.json').write_text(json.dumps(c,indent=2));m['full_game_clear_verified']=True;(candidate/'manifest.json').write_text(json.dumps(m,indent=2))
 (candidate/'global-gate.json').write_text(json.dumps(verdict,indent=2));print(json.dumps(verdict))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baseline',default='arcade/runs/orlegend/life-saving-cold-01');p.add_argument('--candidate',required=True);p.add_argument('--ending-reviewed',action='store_true');p.add_argument('--output',default='arcade/orlegend-bt-deployed.json');gate(p.parse_args())
