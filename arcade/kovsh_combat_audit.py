"""Replay actual buttons and measure combat delays using read-only RAM."""
import argparse
from collections import Counter
import json
from pathlib import Path
from emulator import Emulator
from kovsh import ROM, observe

def audit(folder):
    folder=Path(folder)
    manifest=json.loads((folder/'manifest.json').read_text())
    e=Emulator(ROM,core=Path(manifest['core_path']),deterministic=True,headless=True)
    e.restore((folder/'initial.state').read_bytes())
    counts=Counter();states=Counter();hit_states=Counter();blocks=[];events=[]
    last_hit=0;longest=0;block=Counter();previous=observe(e.ram_view())
    try:
        for line in (folder/'inputs.jsonl').read_text().splitlines():
            row=json.loads(line);f=row['frame'];keys=row['buttons'];o=previous
            raw=e.ram_view()[0x1146a:0x1146e].hex()
            states[raw]+=1
            near=min(o['enemies'],key=lambda x:abs(x['x']-o['x'])+3*abs(x['ground_y']-o['ground_y'])) if o['enemies'] else None
            category='empty_room' if near is None else 'chasing' if abs(near['x']-o['x'])>80 or abs(near['ground_y']-o['ground_y'])>16 else 'close_airborne_enemy' if near['height']<-8 else 'close_ground_enemy'
            counts[category]+=1;block[category]+=1
            if 'attack' in keys:counts['attack_'+category]+=1;block['attack_'+category]+=1
            e.step(keys);after=observe(e.ram_view());new={x['slot']:x['hp'] for x in after['enemies']}
            damage=sum(x['hp']-new[x['slot']] for x in o['enemies'] if x['slot'] in new and 0<=new[x['slot']]<x['hp'])
            killed=sum(1 for x in o['enemies'] if x['slot'] not in new and int.from_bytes(e.ram_view()[0xcf18+x['slot']*0x1a6+100:0xcf18+x['slot']*0x1a6+102],'little')==0)
            if damage or killed:
                longest=max(longest,f-last_hit);last_hit=f;hit_states[raw]+=1
                counts['hit_frames']+=1;block['hit_frames']+=1
                counts['damage']+=damage;block['damage']+=damage;counts['kills']+=killed;block['kills']+=killed
                events.append(dict(frame=f,damage=damage,kills=killed,actor_raw=raw,x=o['x'],ground_y=o['ground_y'],enemies=o['enemies']))
            if not after['enemies'] and o['enemies']:counts['last_empty_frame']=f
            if f%600==0:blocks.append(dict(frame=f,counts=dict(block),observation=after));block.clear()
            previous=after
        report=dict(frames=f,counts=dict(counts),longest_no_hit_gap=longest,actor_states=dict(states),hit_actor_states=dict(hit_states),blocks=blocks,final=previous,headless=True)
        (folder/'combat-audit.json').write_text(json.dumps(report,indent=2))
        (folder/'combat-hit-events.json').write_text(json.dumps(events,indent=2))
        print(json.dumps(report),flush=True)
    finally:e.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');audit(p.parse_args().folder)
