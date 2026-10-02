"""Audited campaign rollouts: normal controls, scene mechanisms, no game writes."""
import argparse, json, subprocess, sys, time
from pathlib import Path
from emulator import Emulator, ROOT
from orlegend import observe, action, sha, ROM, OUT

class Controller:
    def __init__(self, config, combat=None):
        self.config = config
        self.combat = combat or action
        self.scene = None
        self.age = 0
        self.phase = 0
    def choose(self, o, frame):
        scene = o['stage_raw']
        if scene != self.scene:
            self.scene, self.age, self.phase = scene, 0, 0
        self.age += 1
        if scene == 2 and self.config.get('push_statue', True):
            if self.phase == 0:
                if abs(o['x']-200) <= 5:self.phase=1
                else:return ['left' if o['x']>200 else 'right']
            if self.phase == 1:
                if o['y']<=121:self.phase=2
                else:return ['up']
            return ['right']
        c={**self.config, **self.config.get('scenes',{}).get(str(scene),{})}
        if scene==1538 and not o['enemies']:
            return ['left']+(['up'] if o['y']>175 else [])
        if scene==1281 and o.get('tree_hits',16)<16 and o['x']>600:
            tree=o['tree']
            return action({**o,'enemies':[{'slot':-1,'x':tree[0],'y':tree[1]+10,'hp':16-o['tree_hits']}]},frame,{**c,'distance':36,'align':5,'jump':0,'rush':0})
        if scene==1283 and not o['enemies']:
            keys=[]
            if abs(o['x']-256)>3:keys.append('left' if o['x']>256 else 'right')
            if o['y']>116:keys.append('up')
            return keys
        if scene==1028 and c.get('spider_route',True) and len(o['enemies'])==1 and o['enemies'][0]['slot']==0 and o['enemies'][0]['y']<130:
            targetx=c.get('spider_x',1900)
            if o['x']<targetx-5:return ['right']
            if o['y']>125:return ['up']
            return (['left'] if frame%12==0 else [])+(['attack'] if frame%4<2 else [])
        if scene==257 and self.config.get('cave_escape',True) and o['x']<700:
            if o['y']<330:keys=['down','right']
            elif o['x']<350:keys=['right']
            elif o['y']<430:keys=['down','right']
            else:keys=['right']
            if frame%60==2:return []
            if frame%90<2:keys.append('jump')
            return keys
        if scene==514 and not o['enemies']:
            y=220 if o['x']>170 else 90
            keys=['left']
            if abs(o['y']-y)>3:keys.append('up' if o['y']>y else 'down')
            return keys
        if scene==513 and not o['enemies']:
            points=[(900,250),(900,160),(995,115)]
            if o['x']<850:self.phase=0
            x,y=points[min(self.phase,2)]
            if abs(o['x']-x)<8 and abs(o['y']-y)<8 and self.phase<2:self.phase+=1
            keys=[]
            if abs(o['x']-x)>3:keys.append('left' if o['x']>x else 'right')
            if abs(o['y']-y)>3:keys.append('up' if o['y']>y else 'down')
            if self.phase==0 and frame%4<2:keys.append('attack')
            return keys
        if scene == 256 and not o['enemies'] and o['x']>1900:
            targetx=1960 if o.get('door_open') else 1980
            targety=125 if o.get('door_open') else 146
            keys=[]
            if abs(o['x']-targetx)>3:keys.append('left' if o['x']>targetx else 'right')
            if abs(o['y']-targety)>3:keys.append('up' if o['y']>targety else 'down')
            if not o.get('door_open') and abs(o['x']-targetx)<=4:
                if frame%12==0:keys.append('left')
                if self.phase==0 and frame%4<2:keys.append('attack')
            return keys
        if scene==1793 and not o['enemies']:c['nav_y']=c.get('bridge_y',124 if 900<=o['x']<1075 else 155)
        if scene in (772,1537,) and not o['enemies']:c['nav_y']=160
        if not o['enemies'] and 'nav_y' in c:
            keys=['right']
            if abs(o['y']-c['nav_y'])>3:keys.append('up' if o['y']>c['nav_y'] else 'down')
            return keys
        return self.combat(o,frame,c)

def replay(folder):
    meta=json.loads((folder/'manifest.json').read_text())
    emu=Emulator(ROM,deterministic=True)
    try:
        assert sha(ROM)==meta['rom_sha256'] and sha(emu.core_path)==meta['core_sha256']
        if meta['start']=='checkpoint':emu.restore((folder/'initial.state').read_bytes())
        lines=(folder/'inputs.jsonl').read_text().splitlines();started=time.perf_counter()
        for index,line in enumerate(lines):
            emu.step(json.loads(line)['buttons'])
            if (index+1)%20000==0:
                progress={'frame':index+1,'total':len(lines),'wall_seconds':time.perf_counter()-started,**observe(emu.ram())}
                (folder/'replay-progress.json').write_text(json.dumps(progress,indent=2));print('REPLAY_PROGRESS',index+1,progress['stage_raw'],flush=True)
            if index>=len(lines)-3600 and (index+1)%300==0:emu.picture().save(folder/f'verified-ending-{index+1:07d}.png')
        actual=emu.fingerprint()
        expected=json.loads((folder/'result.json').read_text())['expected']
        result={'equal':actual==expected,'actual':actual,'expected':expected,'start':meta['start'],'restores':int(meta['start']=='checkpoint'),'frames':len(lines),'wall_seconds':time.perf_counter()-started}
        (folder/'replay.json').write_text(json.dumps(result,indent=2))
        print('REPLAY',result,flush=True)
    finally:emu.close()

def run(args):
    out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    config=json.loads(args.config) if args.config else {'period':4,'distance':56,'align':14,'jump':120,'push_statue':True}
    (out/'policy.json').write_text(json.dumps(config,indent=2))
    emu=Emulator(ROM,deterministic=True)
    controller=Controller(config);trace=[];samples=[];last_scene=None
    start=time.perf_counter();max_scene=0;stop='frame_budget';continues=0
    meta={'rom_sha256':sha(ROM),'core_sha256':sha(emu.core_path),'frontend_sha256':sha(ROOT/'emulator.py'),
          'source_sha256':sha(__file__),'policy_source_sha256':sha(ROOT/'orlegend.py'),
          'start':'checkpoint' if args.state else 'poweron','fps':emu.fps,'frames_budget':args.frames,
          'deterministic':True,'full_game_clear_verified':False,
          'initial_state_sha256':sha(args.state) if args.state else None,
          'initial_state_path':str(Path(args.state).resolve()) if args.state else None}
    (out/'manifest.json').write_text(json.dumps(meta,indent=2))
    for name in ('orlegend_campaign.py','orlegend.py','emulator.py'):(out/name).write_bytes((ROOT/name).read_bytes())
    stream=(out/'inputs.jsonl').open('w')
    def step(keys):
        emu.step(keys)
        row={'frame':len(trace)+1,'buttons':keys};trace.append(row);stream.write(json.dumps(row)+'\n')
    try:
        if args.state:
            initial=Path(args.state).read_bytes();emu.restore(initial);(out/'initial.state').write_bytes(initial)
        else:
            for line in (OUT/'boot-inputs.jsonl').read_text().splitlines():step(json.loads(line)['buttons'])
        if args.resume_select:
            for sf in range(1200):
                step(['attack'] if sf%30<2 else [])
                if observe(emu.ram())['lives'] in (1,2) and observe(emu.ram())['hp']>0:break
        for f in range(args.frames):
            if f%2000==0 and (out/'STOP').exists():stop='requested_stop';break
            if f%2000==0 and (out/'policy-update.json').exists():
                updated=json.loads((out/'policy-update.json').read_text())
                if updated!=controller.config:
                    controller.config=config=updated
                    with (out/'policy-updates.jsonl').open('a') as changes:
                        changes.write(json.dumps({'frame':len(trace),'config':updated})+'\n')
            o=observe(emu.ram());o['door_open']=bool(emu.ram()[0x1b8b1])
            r=emu.ram();b=0xc266+r[0x11625]*0x98
            o['tree_hits']=r[0x11624];o['tree']=[int.from_bytes(r[b+0x14:b+0x16],'little'),int.from_bytes(r[b+0x16:b+0x18],'little')]
            if o['stage_raw']!=last_scene:
                last_scene=o['stage_raw'];max_scene=max(max_scene,last_scene)
                stem=f"entry-{len(trace):07d}-{last_scene:04x}"
                (out/(stem+'.state')).write_bytes(emu.save());(out/(stem+'.ram')).write_bytes(emu.ram())
                if emu.picture():emu.picture().save(out/(stem+'.png'))
                print('SCENE',len(trace),o,flush=True)
            step(controller.choose(o,f));o=observe(emu.ram())
            if f%2000==1999:
                samples.append({'frame':len(trace),**o});(out/'latest.state.tmp').write_bytes(emu.save());(out/'latest.state.tmp').replace(out/'latest.state');(out/'latest.ram').write_bytes(emu.ram())
                emu.picture().save(out/f"frame-{len(trace):07d}.png")
                (out/'latest.json').write_text(json.dumps({'frame':len(trace),'wall':time.perf_counter()-start,**o},indent=2))
                stream.flush()
            if o['lives']==0 or o['lives']>=128:
                if config.get('allow_continue',False):
                    continues+=1
                    print('CONTINUE',continues,len(trace),o,flush=True)
                    for cf in range(1800):
                        step(['coin'] if cf in (120,121) else ['start'] if cf>180 and cf%60<2 else ['attack'] if cf%60==20 else [])
                        if cf>240 and observe(emu.ram())['lives'] in (1,2):break
                    if observe(emu.ram())['lives'] in (1,2):continue
                stop='lives_exhausted';break
            if o['stage_byte']>=8:
                stop='possible_ending_needs_visual_review'
                for ef in range(3600):
                    step([])
                    if ef%300==299:emu.picture().save(out/f'ending-{ef+1:04d}.png')
                break
        final=observe(emu.ram());expected=emu.fingerprint()
        emu.picture().save(out/'final.png');(out/'final.state').write_bytes(emu.save());(out/'final.ram').write_bytes(emu.ram())
        result={'frames':len(trace),'wall_seconds':time.perf_counter()-start,'after':final,'max_scene_raw':max_scene,
                'continues':continues,'stop_reason':stop,'expected':expected,'full_game_clear_verified':False}
        (out/'result.json').write_text(json.dumps(result,indent=2));(out/'samples.json').write_text(json.dumps(samples,indent=2));print('RESULT',result,flush=True)
    finally:stream.close();emu.close()
    if args.verify:subprocess.run([sys.executable,__file__,'--replay',str(out)],check=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output');p.add_argument('--config');p.add_argument('--state');p.add_argument('--frames',type=int,default=200000);p.add_argument('--verify',action='store_true');p.add_argument('--resume-select',action='store_true');p.add_argument('--replay');args=p.parse_args()
    if args.replay:replay(Path(args.replay))
    else:run(args)
