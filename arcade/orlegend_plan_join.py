"""Join consecutive practice input plans, checking every observable boundary."""
import argparse,gzip,json
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--plans',nargs='+',required=True)
p.add_argument('--output',required=True)
a=p.parse_args()
parts=[]
for name in a.plans:
    raw=Path(name).read_bytes()
    parts.append(json.loads(gzip.decompress(raw) if name.endswith('.gz') else raw))
for before,after in zip(parts,parts[1:]):
    assert before['after']==after['initial'],'Plan boundary observations differ'
plan={'initial':parts[0]['initial'],'after':parts[-1]['after'],
      'macros':[m for part in parts for m in part['macros']],
      'scope':'ordinary-input candidate requires cold verification','provenance':a.plans}
Path(a.output).write_text(json.dumps(plan,indent=2))
print(sum(len(m['inputs']) for m in plan['macros']))
