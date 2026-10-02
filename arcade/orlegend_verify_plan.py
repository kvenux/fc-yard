"""Verify a practice plan's endpoint through the recorded cold input prefix."""
import argparse,json
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
p=argparse.ArgumentParser();p.add_argument('--folder',required=True);p.add_argument('--plan',required=True);p.add_argument('--start',type=int,required=True);a=p.parse_args()
folder=Path(a.folder);plan=json.loads(Path(a.plan).read_text());duration=sum(len(m['inputs']) for m in plan['macros']);end=a.start+duration;e=Emulator(ROM,deterministic=True,headless=True)
try:
    for i,line in enumerate((folder/'inputs.jsonl').open(),1):
        e.step(json.loads(line)['buttons'])
        if i==end:break
    assert i==end,'Recorded trajectory ended before the plan endpoint'
    actual=observation(e);expected=plan['after'];evidence={'scope':'cold input prefix endpoint; not a chapter-clear claim','frame':end,'expected':expected,'actual':actual,'observation_equal':actual==expected,'hp_equal':actual['hp']==expected['hp'],'fingerprint':e.fingerprint()}
    (folder/'plan-endpoint.json').write_text(json.dumps(evidence,indent=2));(folder/'plan-endpoint.state').write_bytes(e.save());print(json.dumps(evidence))
finally:e.close()
