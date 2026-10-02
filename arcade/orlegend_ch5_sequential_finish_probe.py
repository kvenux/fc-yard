"""Test a bounded normal-input finishing move after the elemental hit."""
import sys,json
sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-ch5-sequential-finish-practice-01');out.mkdir(exist_ok=False)
raw=Path('arcade/runs/orlegend/bt/one-life-ch5-active-parallel-beam-practice-01/checkpoints/depth-069.state').read_bytes()
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for mode in ['rush','attack','jump_attack','aimed_sword','air_wave']:
    e.restore(raw);initial=observation(e);inputs=[];events=[];phase='fire';start=0
    for t in range(2000):
        o=observation(e);k=[]
        if phase=='fire':
            if any(v['id']==15 and v['count'] for v in o['resources']['inventory']):k=['d'] if t%4<2 else []
            else:phase='wait'
        if phase=='wait' and o['player_state']==2 and not o['air_mask']:
            phase='finish';start=t;events.append({'frame':t,'event':'ready','o':o})
        age=t-start
        if phase=='finish' and o['enemies']:
            if mode=='rush':k=['left','down','jump'] if age%24<2 else ['left']+(['attack'] if age%4<2 else [])
            elif mode=='attack':k=['left']+(['attack'] if age%4<2 else [])
            elif mode=='jump_attack':k=['left','jump'] if age%30<2 else ['left']+(['attack'] if age%4<2 else [])
            elif mode=='aimed_sword':k=['up'] if o['y']>133 else (['left'] if o['player_facing']!='left' else [])+(['d'] if age%4<2 else [])
            else:
                a=age%60
                k=['left','jump'] if a<2 else [] if a<10 else ['down'] if a<12 else ['down','left'] if a<14 else ['left'] if a<16 else ['attack'] if a<18 else []
        before=o;e.step(k);inputs.append(k);o=observation(e)
        if o['resources']['inventory']!=before['resources']['inventory']:events.append({'frame':t+1,'resources':o['resources']})
        if o['hp']<=0 or o['lives']<2 or o['stage_byte']>=5:break
    row={'mode':mode,'frames':len(inputs),'after':o,'events':events,'clock':e.ram_view()[0xc06f]};rows.append(row)
    (out/f'{mode}.state').write_bytes(e.save());(out/f'{mode}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':f'sequential_finish_{mode}','inputs':inputs}]}));print(json.dumps(row),flush=True)
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
