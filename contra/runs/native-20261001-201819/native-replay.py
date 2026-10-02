"""Replay native ordinary inputs in a fresh process and retain exact audit bytes."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'arcade'))
from emulator import Emulator
path=Path(sys.argv[1]);record=json.loads(path.read_text());core=ROOT/'cores/fceumm_libretro.dll';rom=ROOT/'roms/contra.nes'
assert hashlib.sha256(core.read_bytes()).hexdigest()==record['coreSha256']
assert hashlib.sha256(rom.read_bytes()).hexdigest()==record['romSha256']
e=Emulator(rom,core,deterministic=True)
deaths=0;previous_dead=False;stage_visits=[]
try:
    for mask,count in record['actions']:
        e.mask=(mask&252)|((mask&1)<<8)|((mask&2)>>1)
        for _ in range(count):
            e.core.retro_run();e.frame+=1;m=e.ram();dead=m[0x90]==2
            if dead and not previous_dead:deaths+=1
            previous_dead=dead
            if m[0x18]==5 and m[0x30]<8 and (not stage_visits or stage_visits[-1]!=m[0x30]):stage_visits.append(m[0x30])
    state=e.save();ram=e.ram();(path.parent/'independent.state').write_bytes(state);e.picture().save(path.parent/'independent.png')
    actual=e.fingerprint();expected=record['expected'];original=(path.parent/'final.state').read_bytes()
    differences=[(i,a,b) for i,(a,b) in enumerate(zip(original,state)) if a!=b]
    result={'frame':e.frame,'actual':actual,'expected':expected,'deaths':deaths,'stageVisits':stage_visits,'deathCountEqual':deaths==record['deaths'],'ramEqual':actual['ram']==expected['ram'],'pixelsEqual':actual['video']==expected['video'],'stateEqual':actual['state']==expected['state'],
            'differentBytes':len(differences),'differences':differences[:100],'observed':{k:ram[a] for k,a in {'stage':0x30,'lives':0x32,'status':0x18,'x':0x334,'y':0x31a,'over':0x38}.items()}}
    (path.parent/'independent-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
finally:e.close()
