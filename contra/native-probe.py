"""Benchmark a native core with the existing verified input prefix; do not mix core evidence."""
import sys, json, time, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'arcade'))
from emulator import Emulator
prefix=json.loads((ROOT/'runs/mpc-2026-10-01T08-07-55-820Z/result.json').read_text())
e=Emulator(ROOT/'roms/contra.nes',ROOT/'cores/fceumm_libretro.dll',deterministic=True)
try:
    start=time.perf_counter()
    for mask,frames in prefix['actions']:
        e.mask=(mask&0xfc)|((mask&1)<<8)|((mask&2)>>1)
        for _ in range(frames): e.core.retro_run(); e.frame+=1
    elapsed=time.perf_counter()-start
    ram=e.ram()
    result={'frames':e.frame,'seconds':elapsed,'fps':e.frame/elapsed,'ramSize':len(ram),'stateSize':len(e.save()),
            'observed':{k:ram[a] for k,a in {'stage':0x30,'x':0x334,'y':0x31a,'lives':0x32,'status':0x18,'gameOver':0x38}.items()},
            'coreSHA256':hashlib.sha256((ROOT/'cores/fceumm_libretro.dll').read_bytes()).hexdigest(),
            'source':'https://buildbot.libretro.com/nightly/windows/x86_64/latest/fceumm_libretro.dll.zip'}
    e.picture().save(ROOT/'runs/native-probe.png')
    saved=e.save(); frame=e.frame
    results=[]
    for repeat in range(2):
        e.restore(saved,frame);e.mask=257
        for _ in range(80):e.core.retro_run();e.frame+=1
        results.append(e.fingerprint())
    result['branchRepeatEqual']=results[0]==results[1]
    (ROOT/'runs/native-probe.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
finally:e.close()
