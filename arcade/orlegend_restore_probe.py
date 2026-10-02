"""Verify practice plan reproducibility across checkpoint restores."""
import json,hashlib
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
root=Path('arcade/runs/orlegend/bt');plan=json.loads((root/'one-life-cave-beam-practice-02/plan.json').read_text());state=(root/'one-life-gate-verified-01/final.state').read_bytes();e=Emulator(ROM,deterministic=True,headless=True);results=[]
try:
    for trial in range(4):
        e.step([[],['attack'],['jump'],['c']][trial],30)
        e.restore(state);before=hashlib.sha256(e.ram()).hexdigest()
        for macro in plan['macros']:
            for buttons in macro['inputs']:e.step(buttons)
        results.append({'trial':trial,'before_ram':before,'after':observation(e),'fingerprint':e.fingerprint()})
finally:e.close()
(root/'one-life-restore-probe.json').write_text(json.dumps(results,indent=2));print(json.dumps(results))
