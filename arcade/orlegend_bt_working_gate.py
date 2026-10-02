"""Freeze a verified intermediate route without claiming the chapter is cleared."""
import json
from pathlib import Path
root=Path('arcade/runs/orlegend/bt');folder=root/'one-life-gate-verified-01';result=json.loads((folder/'result.json').read_text());replay=json.loads((folder/'replay.json').read_text());manifest=json.loads((folder/'manifest.json').read_text())
assert result['reason']=='scene_passed' and result['after']['stage_raw']==257
assert result['deaths']==0 and result['continues']==0 and manifest['start']=='poweron' and manifest['restores']==0
assert replay['equal'] and replay['death_count_equal'] and replay['deaths']==0
previous=(root/'one-life-ch1-hp30-record-01'/'inputs.jsonl').read_text().splitlines();inputs=(folder/'inputs.jsonl').read_text().splitlines();assert inputs[:len(previous)]==previous
assert not any(set(json.loads(line)['buttons'])&{'coin','start'} for line in inputs[2584:])
spec=json.loads((folder/'tree.json').read_text());spec['name']='one-life-working-route';spec['validation']={'scope':'zero-death through chapter one and second-chapter cave entrance; chapter two NOT cleared','accepted_through_chapter':1,'verified_scene':257,'hp_at_cave_entry':32,'deaths':0,'continues':0,'start':'poweron','restores':0,'independent_replay':True,'previous_chapter_prefix_equal':True,'evidence':str(folder)}
Path('arcade/orlegend-bt-working.json').write_text(json.dumps(spec,indent=2));(folder/'route-gate.json').write_text(json.dumps(spec['validation'],indent=2));print(json.dumps(spec['validation']))
