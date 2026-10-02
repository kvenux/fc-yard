import sys,json,gzip,collections
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-bull-threat-calibration-02');out.mkdir(exist_ok=False);p=json.loads(gzip.decompress(Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-06/checkpoints/depth-035.json.gz').read_bytes()));e=Emulator(ROM,deterministic=True,headless=True);e.restore(Path('arcade/runs/orlegend/bt/one-life-ch8-final-bull-action-probe-01/item_8.state').read_bytes());o=observation(e);inputs=[];recent=collections.deque(maxlen=180);events=[]
for t,k in enumerate(v for m in p['macros'] for v in m['inputs']):
 recent.append({'frame':t,'o':o,'buttons':k,'state':e.save()});before=o;e.step(k);inputs.append(k);o=observation(e)
 if o['hp']<before['hp']:
  events.append({'frame':t+1,'before':before,'after':o,'context':[{key:val for key,val in v.items() if key!='state'} for v in recent]})
  if len(events)==1:
   for n in [1,10,20,40,80,120,160]:
    v=list(recent)[-n];name=f'prehit-{n}';(out/f'{name}.state').write_bytes(v['state']);(out/f'{name}-plan.json').write_text(json.dumps({'initial':p['initial'],'after':v['o'],'macros':[{'name':'bull_before_first_hit','inputs':inputs[:v['frame']]}]}))
(out/'events.json').write_text(json.dumps(events,indent=2));print(json.dumps([{'frame':v['frame'],'hp':v['after']['hp'],'enemy':v['before']['enemies'],'hero':[v['before']['player_state'],v['before']['player_move']], 'meter':v['before']['resources']['meter']} for v in events]));e.close()

