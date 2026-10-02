import json,sys,time,hashlib
from pathlib import Path
from emulator import Emulator
from kovsh import ROM,OUT,observe
mode=sys.argv[1];p=OUT/'two-life-001';e=Emulator(ROM,deterministic=True,headless=True);e.restore((p/'frame-047400.state').read_bytes());rows=[json.loads(x)['buttons'] for x in (p/'inputs.jsonl').read_text().splitlines()[47400:52400]]
t=time.perf_counter()
for keys in rows:
 e.step(keys);observe(e.ram_view() if mode=='view' else e.ram())
result={'mode':mode,'frames':len(rows),'seconds':time.perf_counter()-t,'ram_sha256':hashlib.sha256(e.ram()).hexdigest(),'video_bytes_allocated':e.video_bytes is not None};print(json.dumps(result));(OUT/f'ram-benchmark-{mode}.json').write_text(json.dumps(result,indent=2));e.close()
