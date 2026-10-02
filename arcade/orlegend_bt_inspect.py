"""Replay recorded inputs and save read-only diagnostic observations/screens."""
import argparse,json
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
p=argparse.ArgumentParser();p.add_argument('--folder',required=True);p.add_argument('--frames',required=True);a=p.parse_args()
folder=Path(a.folder);targets=set(map(int,a.frames.split(',')));e=Emulator(ROM,deterministic=True,headless=True)
try:
 for i,line in enumerate((folder/'inputs.jsonl').open(),1):
  if i in targets:e.headless=False;e.av_enable=3
  e.step(json.loads(line)['buttons'])
  if i in targets:
   base=folder/f'diagnostic-{i:07d}';e.picture().save(str(base)+'.png');Path(str(base)+'.state').write_bytes(e.save());Path(str(base)+'.json').write_text(json.dumps(observation(e),indent=2));print(i,observation(e),flush=True);e.headless=True;e.av_enable=2
  if i>=max(targets):break
finally:e.close()
