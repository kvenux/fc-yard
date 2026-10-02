"""Compare ordinary grounded quarter-circle projectiles on the fixed spider boss."""
import sys,json
sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch8-dragon-ground-wave-clear-probe-01');out.mkdir(exist_ok=False)
raw=Path('arcade/runs/orlegend/bt/one-life-ch8-parallel-beam-practice-04/checkpoints/depth-027.state').read_bytes()
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for menu in [True]:
    for hold in [1,2,3]:
        e.restore(raw);initial=observation(e);inputs=[];recipe=[];events=[];confirmed=0;maximum=0
        for t in range(4600):
            o=observation(e);targets=[v for v in o['enemies'] if v['slot']==0 and v['state']!=1];k=[]
            if recipe:k=recipe.pop(0)
            elif o['player_state']==2 and not o['air_mask'] and targets:
                if o['resources']['meter']<96:k=['attack','jump','c']
                else:
                    face='left' if targets[0]['x']<o['x'] else 'right'
                    recipe=[[face]]*6+[[]]*6+([['c']]*2+[[]]*8 if menu else [])
                    for bits in [['down'],['down',face],[face],['attack']]:recipe += [bits]*hold
                    k=recipe.pop(0);events.append({'frame':t,'event':'command','meter':o['resources']['meter']})
            before=o;e.step(k);inputs.append(k);o=observation(e)
            if o['player_state']==6 and o['player_move']==29 and not o['air_mask']:confirmed+=1
            if o['player_state']==6 and o['player_move']==35:maximum+=1
            if o['hp']<=0 or o['lives']<2 or not o['enemies'] or o['stage_raw']!=1793:break
        name=f'{menu}-{hold}';row={'menu':menu,'hold':hold,'frames':len(inputs),'after':o,'ground_wave_frames':confirmed,'max_special_frames':maximum,'events':events};rows.append(row)
        (out/f'{name}.state').write_bytes(e.save());(out/f'{name}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':f'ground_wave_{name}','inputs':inputs}]}));print(json.dumps(row),flush=True)
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()

