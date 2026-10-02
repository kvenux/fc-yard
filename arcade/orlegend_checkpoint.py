import argparse,json
from pathlib import Path
from emulator import Emulator
from orlegend import ROM,observe
p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('frame',type=int);p.add_argument('output');a=p.parse_args();folder=Path(a.run);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
entries=[(int(f.name.split('-')[1]),f) for f in folder.glob('entry-*.state') if int(f.name.split('-')[1])<=a.frame];n,state=max(entries);e=Emulator(ROM,deterministic=True);e.restore(state.read_bytes())
for i,line in enumerate((folder/'inputs.jsonl').read_text().splitlines()):
 if i<n:continue
 if i>=a.frame:break
 e.step(json.loads(line)['buttons'])
(out/'initial.state').write_bytes(e.save());(out/'initial.ram').write_bytes(e.ram());e.picture().save(out/'initial.png');print(observe(e.ram()));e.close()
