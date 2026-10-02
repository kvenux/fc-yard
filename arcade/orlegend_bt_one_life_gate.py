"""Accept zero-death chapter progress; HP improvement may spend real inventory."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--baseline',required=True);p.add_argument('--candidate',required=True);p.add_argument('--repeat',required=True);p.add_argument('--stage',required=True,type=int);p.add_argument('--output',default='arcade/orlegend-bt-one-life.json');p.add_argument('--previous');p.add_argument('--ending-review');a=p.parse_args()
def read(folder,name):return json.loads((Path(folder)/name).read_text())
b=read(a.baseline,'result.json');c=read(a.candidate,'result.json');repeat=read(a.repeat,'result.json');m=read(a.candidate,'manifest.json');r=read(a.candidate,'replay.json')
assert 1<=a.stage<=8
render_path=Path(a.candidate,'replay-render.json');render_verified=False
if render_path.exists():
    rendered=read(a.candidate,'replay-render.json');assert rendered['core_render_entire_run'] and rendered['equal'] and rendered['deaths']==0 and rendered['start']=='poweron' and rendered['restores']==0
    render_verified=True
if a.stage==8:
    assert render_verified and a.ending_review,'Full-game acceptance requires full core-render replay and reviewed ending images'
    review=json.loads(Path(a.ending_review).read_text(encoding='utf-8'));assert review['full_game_clear_verified'] is True and len(review['images'])>=2
    for item in review['images']:
        path=Path(a.candidate,item['file']);assert path.name.startswith('verified-ending-') and path.suffix=='.png' and path.resolve().parent==Path(a.candidate).resolve()
        assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
assert c['reason']=='chapter_passed' and c['after']['stage_byte']>=a.stage
assert c['deaths']==0 and c['continues']==0 and m['start']=='poweron' and m['restores']==0
assert r['equal'] and r['death_count_equal'] and r['deaths']==0 and r['start']=='poweron' and r['restores']==0
assert repeat['deaths']==0 and repeat['continues']==0 and repeat['fingerprint']==c['fingerprint']
assert b['reason']!='chapter_passed' or b['deaths']>0 or c['after']['hp']>b['after']['hp'],'No improvement in zero-death progress or HP'
inputs=Path(a.candidate,'inputs.jsonl').read_text().splitlines();assert len(inputs)==c['frames']
assert not any(set(json.loads(line)['buttons']) & {'coin','start'} for line in inputs[2584:]),'Mid-game coin/start inputs are forbidden'
if a.previous:
    prefix=Path(a.previous,'inputs.jsonl').read_text().splitlines();assert inputs[:len(prefix)]==prefix,'Earlier accepted chapter inputs changed'
spec=read(a.candidate,'tree.json');spec['name']=f'one-life-progress-through-chapter-{a.stage}'
spec['parameters']['allow_continue']=False
spec['validation']={'scope':'full-game one-life clear' if a.stage==8 else 'zero-death chapter progress; not full-game one-life clear','full_game_clear_verified':a.stage==8,'accepted_through_chapter':a.stage,'deaths':0,'continues':0,'start':'poweron','restores':0,'hp':c['after']['hp'],'baseline_hp':b['after']['hp'],'candidate':a.candidate,'repeat':a.repeat,'independent_replay':True,'core_render_replay':render_verified,'ending_review':a.ending_review,'inventory':c['after']['resources']['inventory']}
Path(a.output).write_text(json.dumps(spec,indent=2));Path(a.candidate,'one-life-gate.json').write_text(json.dumps(spec['validation'],indent=2));print(json.dumps(spec['validation']))
