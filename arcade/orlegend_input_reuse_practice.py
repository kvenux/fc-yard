"""Replay ordinary plan suffixes from a practice state; never a cold acceptance."""
import sys,json,argparse,gzip
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from emulator import Emulator
from orlegend import ROM,sha
from orlegend_bt_train import observation
p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--plan',required=True);p.add_argument('--output',required=True);p.add_argument('--skip',type=int,default=0);a=p.parse_args()
out=Path(a.output);out.mkdir(exist_ok=False);raw=Path(a.plan).read_bytes();plan=json.loads(gzip.decompress(raw) if a.plan.endswith('.gz') else raw)
e=Emulator(ROM,deterministic=True,headless=True);e.restore(Path(a.state).read_bytes());initial=o=observation(e);inputs=[];trace=[];skipped=0
for m in plan['macros']:
    for k in m['inputs']:
        if skipped<a.skip:skipped+=1;continue
        assert not set(k)&{'coin','start'}
        before=o;e.step(k);inputs.append(k);o=observation(e)
        if o['stage_raw']!=before['stage_raw']:
            (out/f'scene-{o["stage_raw"]:04x}-frame-{len(inputs):06}.state').write_bytes(e.save())
            trace.append({'frame':len(inputs),'event':'scene','o':o})
        if o['hp']<=0 or o['lives']<initial['lives']:break
    trace.append({'frame':len(inputs),'macro':m['name'],'o':o})
    if o['hp']<=0 or o['lives']<initial['lives']:break
row={'scope':'practice ordinary input reuse, requires cold validation','frames':len(inputs),'valid':o['hp']>0 and o['lives']==initial['lives'],'o':o,'clock':e.ram_view()[0xc06f],'trace':trace}
(out/'result.json').write_text(json.dumps(row,indent=2));(out/'manifest.json').write_text(json.dumps({'options':vars(a),'rom_sha256':sha(ROM),'core_sha256':sha(e.core_path),'state_sha256':sha(a.state),'plan_sha256':sha(a.plan)},indent=2))
if row['valid']:
    (out/'final.state').write_bytes(e.save());(out/'plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'reused_ordinary_suffix','inputs':inputs}]}))
print(json.dumps({k:v for k,v in row.items() if k!='trace'}));e.close()
