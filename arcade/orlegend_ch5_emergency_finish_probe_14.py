"""Test a last elemental item as a legitimate timed finish, without preserving it."""
import sys,json
sys.path.insert(0,'arcade')
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
from orlegend_bt import Controller
from orlegend_beam import keys
out=Path('arcade/runs/orlegend/bt/one-life-ch5-emergency-finish-practice-02');out.mkdir(exist_ok=False)
raw=Path('arcade/runs/orlegend/bt/one-life-ch5-active-parallel-beam-practice-01/checkpoints/depth-074.state').read_bytes()
e=Emulator(ROM,deterministic=True,headless=True);rows=[]
for ident in [15,2]:
    e.restore(raw);initial=observation(e);spec=json.loads(Path('arcade/orlegend-bt-ch5-active-search-policy.json').read_text());c=Controller(spec);memory={};used=False;inputs=[]
    for t in range(1800):
        o=observation(e)
        if not used:
            r=c.select_item({'o':o,'frame':t},memory,{'ids':[ident],'reserves':{},'radial_select':True,'timeout':100,'cooldown':180});k=r.buttons;used=r.status!='RUNNING'
        else:k=c.choose(o,t)
        e.step(k);inputs.append(k);o=observation(e)
        if o['hp']<=0 or o['lives']<2 or o['stage_byte']>=5:break
    row={'item':ident,'frames':len(inputs),'after':o,'events':c.events,'clock':e.ram_view()[0xc06f]};rows.append(row)
    (out/f'{ident}.state').write_bytes(e.save());(out/f'{ident}-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':f'emergency_finish_{ident}','inputs':inputs}]}));print(json.dumps(row),flush=True)
(out/'result.json').write_text(json.dumps(rows,indent=2));e.close()
