"""Isolated ordinary-input calibration of actor state semantics and air flags."""
import json
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
out=Path('arcade/runs/orlegend/bt/one-life-state-semantics-01');out.mkdir(parents=True,exist_ok=False);state=Path('arcade/runs/orlegend/moves-charge-safe-01/frame-600.state').read_bytes();e=Emulator(ROM,deterministic=True,headless=True);results=[]
try:
 for name,buttons in [('attack',['attack']),('jump',['jump']),('down_jump',['down','jump']),('down',['down']),('attack_combo',['attack']),('charge',['attack','jump','c'])]:
  e.restore(state);e.step([],90);rows=[]
  for f in range(60):
   keys=buttons if f<2 or name=='attack_combo' and f%4<2 or name=='charge' else []
   e.step(keys);o=observation(e);rows.append({'frame':f+1,'buttons':keys,'state':o['player_state'],'move':o['player_move'],'flags':e.ram_view()[0x1bee2],'air_mask':e.ram_view()[0x1bee2]&0x30,'hp':o['hp']})
  results.append({'input':name,'rows':rows});print(name,rows[:12],flush=True)
 (out/'result.json').write_text(json.dumps({'scope':'checkpoint input calibration only','results':results},indent=2))
finally:e.close()
