"""Publish evidence-backed one-life training progress, separate from old clears."""
import json
from pathlib import Path
root=Path('arcade/runs/orlegend/bt');iterations=[]
for folder in sorted(root.glob('one-life-*')):
    path=folder/'summary.json'
    if not path.exists():continue
    s=json.loads(path.read_text());rows=[r for r in s.get('results',[]) if r.get('reason') in ('chapter_passed','first_death','budget')]
    if not rows:continue
    iterations.append({'folder':str(folder),'completed':len(rows),'total':s.get('total',len(rows)),'chapter_passed':sum(r['reason']=='chapter_passed' for r in rows),'wall_seconds':s.get('wall')})
policy=json.loads(Path('arcade/orlegend-bt-one-life.json').read_text());v=policy['validation']
progress={'goal':'power-on, zero restore, zero death, zero mid-game coin/start, full-game clear and independent replay','complete':v.get('full_game_clear_verified',False) and v['accepted_through_chapter']==8,'accepted_through_chapter':v['accepted_through_chapter'],'accepted_hp':v['hp'],'accepted_deaths':v['deaths'],'independent_replay':v['independent_replay'],'core_render_replay':v.get('core_render_replay',False),'evidence':v['candidate'],'cold_sweep_trials_completed':sum(i['completed'] for i in iterations),'count_scope':'Cold sweep trials only; excludes checkpoint command calibration, manual runs, and independent replay','iterations':iterations,'historical_verified_full_clear_deaths':123,'historical_full_clear_is_one_life':False}
searches=[]
for path in root.glob('one-life-*beam-practice-*/progress.json'):
    try:s=json.loads(path.read_text())
    except json.JSONDecodeError:continue
    searches.append({'folder':str(path.parent),'simulated_frames':s['simulated_frames'],'depth':s['depth'],'wall':s['wall'],'goals':s['goals']})
progress['checkpoint_search']={'scope':'Practice branching only; every accepted plan must pass a cold zero-restore replay','simulated_frames':sum(s['simulated_frames'] for s in searches),'searches':searches}
(root/'one-life-progress.json').write_text(json.dumps(progress,indent=2));print(json.dumps({k:v for k,v in progress.items() if k!='iterations'}))
