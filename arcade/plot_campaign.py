"""Plot actual score and health along one recorded continuous input route."""
import argparse
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from kovsh import OUT, observe

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('chain',type=str)
a=p.parse_args()
from pathlib import Path
chain=json.loads(Path(a.chain).read_text())
rows=[];base=0
for part in chain['parts']:
    directory=OUT/part['directory'];limit=part['frames']
    for ram in sorted(directory.glob('frame-*.ram')):
        frame=int(ram.stem.split('-')[1])
        if frame<=limit:
            o=observe(ram.read_bytes())
            rows.append(dict(frame=base+frame,score=o['score'],hp=o['hp'],chapter=o['chapter']))
    base+=limit
plt.rcParams['font.sans-serif']=['Microsoft YaHei','DejaVu Sans']
fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True,layout='constrained')
x=[r['frame']/59.18/60 for r in rows]
axes[0].plot(x,[r['score'] for r in rows]);axes[0].set(title='风云再起 · 单币连续路线（尚未通关）',ylabel='真实游戏得分')
axes[1].plot(x,[r['hp'] for r in rows]);axes[1].set(xlabel='游戏模拟时间（分钟）',ylabel='当前生命值')
for ax in axes:ax.grid(alpha=.2)
fig.savefig(OUT/'campaign-progress.png',dpi=150)
plt.close(fig)
(OUT/'campaign-progress.json').write_text(json.dumps(dict(chain=chain,samples=rows,full_game_clear_verified=False),indent=2))
