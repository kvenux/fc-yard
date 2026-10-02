"""Read-only actor geometry field calibration."""
import argparse,json
from pathlib import Path
from emulator import Emulator
from orlegend import ROM,observe
p=argparse.ArgumentParser();p.add_argument('state');a=p.parse_args();e=Emulator(ROM,deterministic=True,headless=True)
try:
 e.restore(Path(a.state).read_bytes());r=e.ram_view();o=observe(r)
 for ident,b in [('player',0x1be50)]+[(v['slot'],0x11a40+v['slot']*0x13e) for v in o['enemies']]:
  print(json.dumps({'actor':ident,'address':hex(b),'coordinate_words':[int.from_bytes(r[b+i:b+i+2],'little',signed=True) for i in range(0,32,2)],'state_move':[r[b+0x33],r[b+0x32]],'raw':list(r[b-0x14:b+0x58])}))
finally:e.close()
