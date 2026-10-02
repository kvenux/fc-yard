"""Certify an input path twice from boot when only audio filter state differed."""
import json,sys,time,subprocess,hashlib,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
source=Path(sys.argv[1]);record=json.loads(source.read_text())
audit=json.loads((source.parent/'independent-audit.json').read_text())
assert audit['ramEqual'] and audit['pixelsEqual'] and not audit['stateEqual']
original=(source.parent/'final.state').read_bytes()
audio=original.index(b'FAC2\x08\x00\x00\x00')+8
assert audit['differentBytes']==len(audit['differences'])
assert all(audio<=i<audio+8 for i,a,b in audit['differences']), 'Unexpected non-audio difference'
directory=ROOT/'runs'/('native-'+time.strftime('%Y%m%d-%H%M%S'));directory.mkdir()
manifest=json.loads((source.parent/'manifest.json').read_text())
manifest.update(kind='fresh_boot_recertification',sourceResult=str(source.resolve()),reason='FAC2 audio filter accumulator differs; game RAM and pixels identical. Two fresh-boot executions must match all bytes.')
manifest['sourceHashes']['native-recertify.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
(directory/'native-recertify.py').write_bytes(Path(__file__).read_bytes())
(directory/'manifest.json').write_text(json.dumps(manifest,indent=2))
shutil.copyfile(source.parent/'independent.state',directory/'final.state')
shutil.copyfile(source.parent/'independent.png',directory/'final.png')
record.update(expected=audit['actual'],replayEqual=False,fullGameClearVerified=False,sourceResult=str(source.resolve()),originalPlannerAudit=audit,replayMethod='two_fresh_processes')
result=directory/'result.json';result.write_text(json.dumps(record))
subprocess.run([sys.executable,str(ROOT/'native-replay.py'),str(result)],check=True,capture_output=True)
second=json.loads((directory/'independent-audit.json').read_text())
assert second['actual']==record['expected'],second
clear=bool(record['final']['victory'] and second['observed']['status']==6 and second.get('stageVisits')==list(range(8)))
record.update(actual=second['actual'],replayEqual=True,fullGameClearVerified=clear,oneLifeClearVerified=clear and record['deaths']==0 and second.get('deaths')==0)
result.write_text(json.dumps(record))
status_path=ROOT/'runs/native-status.json'
if status_path.exists():
    status=json.loads(status_path.read_text())
    if status.get('dir')==source.parent.name and status.get('status')=='completed':
        status.update(dir=directory.name,replayEqual=True,oneLifeClearVerified=record['oneLifeClearVerified'],deaths=record['deaths'])
        status_path.write_text(json.dumps(status))
subprocess.run(['node',str(ROOT/'report.cjs')],check=True,capture_output=True)
print(str(result))
