"""Native FCEUmm model search. Ordinary controller inputs, immutable ROM, full replay audit."""
import sys, json, time, hashlib, argparse, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'arcade'))
from emulator import Emulator
P=argparse.ArgumentParser();P.add_argument('--frames',type=int,default=12000);P.add_argument('--stop-stage',type=int,default=1);P.add_argument('--resume');P.add_argument('--prefix-frames',type=int);P.add_argument('--horizon',type=int,default=80);P.add_argument('--zero-death',action='store_true');P.add_argument('--aggressive',action='store_true')
args=P.parse_args()
rom=ROOT/'roms/contra.nes';core=ROOT/'cores/fceumm_libretro.dll'
sha=lambda b:hashlib.sha256(b).hexdigest()
dir=ROOT/'runs'/('native-'+time.strftime('%Y%m%d-%H%M%S'));dir.mkdir(parents=True)
manifest={'scope':'native_fresh_boot_model_search','objective':'zero_death' if args.zero_death else 'clear','combatStyle':'aggressive' if args.aggressive else 'balanced','romSha256':sha(rom.read_bytes()),'coreSha256':sha(core.read_bytes()),'args':vars(args),'sourceHashes':{}}
for file in [Path(__file__),ROOT.parent/'arcade/emulator.py']:
    data=file.read_bytes();manifest['sourceHashes'][file.name]=sha(data);(dir/file.name).write_bytes(data)
(dir/'manifest.json').write_text(json.dumps(manifest,indent=2))
def make():return Emulator(rom,core,deterministic=True)
def step(e,mask):
    e.mask=(mask&252)|((mask&1)<<8)|((mask&2)>>1);e.core.retro_run();e.frame+=1
def read(e):
    m=e.ram();enemies=[dict(slot=i,type=m[0x528+i],routine=m[0x4b8+i],hp=m[0x578+i],realHP=m[0x5b8+i],var4=m[0x5e8+i],x=m[0x33e+i],y=m[0x324+i],flags=m[0x598+i]) for i in range(16) if m[0x4b8+i]]
    # PLAYER_HIDDEN is the signed high byte of Y: jumping above the screen
    # wraps the low byte to 255, which is not a fall below the platform.
    y=m[0x31a]+(m[0xba] if m[0xba]<128 else m[0xba]-256)*256
    return dict(frame=e.frame,stage=m[0x30],progress=m[0x64]*256+m[0x65],x=m[0x334],y=y,lives=m[0x32],dead=m[0x90]==2,over=m[0x38]==1,state=m[0x90],routine=m[0x2c],location=m[0x40],victory=m[0x18]==6,status=m[0x18],score=m[0x7e2]+256*m[0x7e3],weapon=m[0xaa]&15,jump=m[0xa0]&1,water=m[0xb2],barrier=m[0x37],boss=m[0x3b],enemies=enemies)
def action(name,direction=0,jump=False,**kw):return dict(name=name,direction=direction,jump=jump,**kw)
def mask(a,f):
    direction=a.get('after',0) if 'move' in a and f>=a['move'] else a['direction']
    jumping=f==a.get('phase',0) if a.get('single') else (f+a.get('phase',0))%32<1
    return direction | (2 if a.get('continuous') or f%8<4 else 0) | (1 if a['jump'] and jumping else 0)
def targets(o):return [t for t in o['enemies'] if t['type'] in [10,8,16,28] and 0<t['hp']<240 and (t['type']!=16 or t['realHP']>0)]
def gun_targets(o):
    if o['stage'] in [1,3] or o['stage']>=8:return []
    return [t for t in o['enemies'] if t['type'] in [4,6,7,14] and t['hp']>0 and abs(t['x']-o['x'])<176]

def combat_track(o):
    return [dict(slot=t['slot'],type=t['type'],hp=t['hp'] if t['hp']<240 else (10 if t['type']==14 else 8 if t['type'] in [4,7] else 1),damage=0,killed=False) for t in gun_targets(o)] if args.aggressive else []

def combat_update(track,ram):
    for t in track:
        i=t['slot']
        if t['killed'] or not ram[0x4b8+i] or ram[0x528+i]!=t['type']:continue
        hp=ram[0x578+i]
        if hp<t['hp']:
            t['damage']+=t['hp']-hp;t['hp']=hp;t['killed']=hp==0

def combat_value(track):
    return sum(t['damage']*(110 if t['type'] in [4,7,14] else 30)+(600 if t['type'] in [4,7,14] else 100)*t['killed'] for t in track)
def can_continue(e,lives):
    saved=e.save();frame=e.frame;safe=False
    for d,j in [(0,False),(32,False),(64,False),(128,False),(0,True),(64,True),(128,True),(32,True)]:
        e.restore(saved,frame);safe=True;a=action('safety-tail',d,j)
        for f in range(120 if args.zero_death else 40):
            step(e,mask(a,f));r=e.ram()
            if r[0x90]==2 or r[0x38]==1 or r[0x32]<lives:safe=False;break
        if safe:break
    e.restore(saved,frame);return safe
def climb_route(e,s,saved,frame,horizontal=False):
    frontier=[(0,saved,[],s)];best=None
    aa=[action('climb',d,True,phase=p,continuous=s['weapon']==4) for d in [64,128,0] for p in ([0] if horizontal else [0,16])]
    if horizontal:
        aa += [action('evade',d,continuous=s['weapon']==4) for d in [0,32,64,128]]
        aa += [action('drop',32,True,continuous=s['weapon']==4)]
    for depth in range(20 if horizontal else 4):
        candidates=[]
        for _,state,path,origin in frontier:
            for a in aa:
                e.restore(state,frame+len(path));sequence=[];safe=True
                for f in range(16 if horizontal else 80):
                    m=mask(a,f);step(e,m);sequence.append(m);r=e.ram()
                    if r[0x90]==2 or r[0x38]==1 or r[0x32]<s['lives']:safe=False;break
                if not safe:continue
                o=read(e)
                if horizontal and o['y']>208:continue
                if horizontal and depth==19 and not can_continue(e,o['lives']):continue
                value=(o['progress']-s['progress'])*3+(s['y']-o['y'])*(.15 if horizontal else 2.15)+(o['stage']-s['stage'])*100000
                if horizontal:value+=(o['x']-s['x'])*2
                if horizontal and s['stage']==5 and 1600<o['progress']<1900:value-=max(0,180-o['y'])*5
                row=(value,e.save(),path+sequence,o);candidates.append(row)
                if (horizontal or o['progress']>s['progress']) and (best is None or value>best[0]):best=row
        candidates.sort(key=lambda r:r[0],reverse=True);frontier=[];bins=set()
        if horizontal and candidates:best=candidates[0]
        for row in candidates:
            o=row[3];key=(o['progress']//32,o['x']//32,o['y']//32,o['jump'])
            if key not in bins:frontier.append(row);bins.add(key)
            if len(frontier)==(24 if horizontal and s['stage']==5 else 6):break
        if not frontier:break
    e.restore(saved,frame)
    if horizontal and best and len(best[2])<320:return None
    return best
def boss_route(e,s,saved,frame):
    def health(o):
        return sum(t['var4'] for t in o['enemies'] if t['type']==28)+sum(min(t['hp'],t['realHP']) for t in o['enemies'] if t['type']==8)
    initial=health(s);frontier=[(0,saved,[],s)];best=None
    aa=[action('boss-combo',d,j,continuous=s['weapon']==4) for d,j in [(16,False),(16,True),(32,False),(80,False),(144,False),(64,True),(128,True)]]
    for depth in range(4):
        candidates=[]
        for _,state,path,origin in frontier:
            for a in aa:
                e.restore(state,frame+len(path));sequence=[];safe=True
                for f in range(60):
                    m=mask(a,f);step(e,m);sequence.append(m);r=e.ram()
                    if r[0x90]==2 or r[0x38]==1 or r[0x32]<s['lives']:safe=False;break
                if not safe:continue
                o=read(e);damage=initial-health(o);aim=min(abs(o['x']-104),abs(o['x']-152))
                value=damage*100-aim*.5
                row=(value,e.save(),path+sequence,o);candidates.append(row)
                if damage>0 and (best is None or value>best[0]):best=row
        candidates.sort(key=lambda r:r[0],reverse=True);frontier=[];bins=set()
        for row in candidates:
            o=row[3];key=(o['x']//16,o['y']//32,o['jump'],health(o))
            if key not in bins:frontier.append(row);bins.add(key)
            if len(frontier)==8:break
        if not frontier:break
    e.restore(saved,frame);return best
def choose(e):
    s=read(e);indoor=s['stage'] in [1,3];vertical=s['stage']==2
    tank=next((t for t in s['enemies'] if s['stage']==4 and t['type']==18 and t['hp']>0 and t['routine'] in [2,3,4]),None)
    if tank:
        saved=e.save();frame=e.frame
        for aim in [29,65,97]:
            delta=aim-s['x'];move=abs(delta)
            for pulse in [2,4,8]:
                e.restore(saved,frame);sequence=[];safe=True
                for f in range(960):
                    direction=(64 if delta<0 else 128) if f<move else (128 if f==move else 0)
                    m=direction | (2 if f%pulse==0 else 0);step(e,m);sequence.append(m);r=e.ram()
                    if r[0x90]==2 or r[0x38]==1 or r[0x32]<s['lives']:safe=False;break
                o=read(e);remaining=next((t for t in o['enemies'] if t['type']==18 and t['slot']==tank['slot']),None)
                if safe and (remaining is None or remaining['hp']==0) and can_continue(e,o['lives']):
                    e.restore(saved,frame)
                    return sequence,{'name':'tank-retreat-turn-fire','aim':aim,'pulse':pulse,'commitFrames':len(sequence)}
        e.restore(saved,frame)
    dragon=next((t for t in s['enemies'] if vertical and t['type']==20 and t['realHP']>0),None)
    outdoor_boss=next((t for t in s['enemies'] if t['type'] in {4:[18,20],5:[19],6:[22],7:[16,22]}.get(s['stage'],[]) and 0<t['hp']<240),None)
    horizon=160 if indoor and s['location']!=128 else args.horizon
    if indoor and s['location']==1 and s['weapon']==2:horizon=320
    if s['stage']==3 and s['location']==128:horizon=max(horizon,240)
    if outdoor_boss:horizon=max(horizon,160)
    commit=32 if indoor and s['location']!=128 else 16
    if s['status']!=5 or s['routine'] not in [4,8] or s['state']!=1:return [0]*commit,{'name':'transition'}
    cores=[t for t in s['enemies'] if t['type']==20 and t['hp']>0]
    closed=bool(cores) and all(t['flags']&128 for t in cores) and abs(s['x']-max(16,min(240,128+(cores[0]['x']-128)*2)))<=3
    if indoor and s['location']==1 and (closed or s['barrier']==128):
        a=action('advance-cleared' if s['barrier']==128 else 'wait-core',16 if s['barrier']==128 else 32,continuous=s['weapon']==4)
        saved=e.save();frame=e.frame;safe=True
        for f in range(80):
            step(e,mask(a,f));o=read(e)
            if o['dead'] or o['over'] or o['lives']<s['lives']:safe=False;break
        e.restore(saved,frame)
        if safe:return [mask(a,f) for f in range(commit)],{'name':a['name'],'safeFrames':80}
    aa=[action('right',128),action('right-jump',128,True),action('hold'),action('hold-jump',0,True),action('right-up',144),action('left-jump',64,True)]
    if indoor:
        aa=[action('hold'),action('left',64),action('right',128),action('duck',32),action('jump',0,True)]
        for item in s['enemies']:
            if item['type']==0 and abs(item['y']-s['y'])<48:
                delta=item['x']-s['x']
                if delta:aa.append(action('collect-item',64 if delta<0 else 128,move=abs(delta),after=0))
        if s['barrier']==128 or s['location']==128:aa.append(action('up',16))
        cores=[t for t in s['enemies'] if t['type']==20 and t['hp']>0]
        if cores:
            for core_target in cores:
                for offset in ([-8,0,8] if s['weapon']==2 else [0]):
                    aim=max(16,min(240,128+(core_target['x']-128)*2+offset));delta=aim-s['x']
                    if delta:
                        for after in [0,32]:aa.append(action('align-core',64 if delta<0 else 128,move=abs(delta),after=after))
        for frames in [16,32]:aa.append(action('shoot-duck',move=frames,after=32))
        if s['location']==128:
            ts=sorted(targets(s),key=lambda t:abs(t['x']-s['x']))
            if ts:
                delta=ts[0]['x']-s['x']
                if delta:aa.append(action('align-boss',64 if delta<0 else 128,move=min(64,abs(delta)),after=16))
            if s['stage']==3:
                for aim in [104,128,152]:
                    delta=aim-s['x']
                    if delta:aa.append(action('align-merge-point',64 if delta<0 else 128,move=abs(delta),after=16))
            aa += [action('jump-up',16,True),action('up-left',80),action('up-right',144)]
            for direction in [64,128,80,144]:
                for phase in [0,16]:aa.append(action('moving-jump',direction,True,phase=phase))
    else:
        if args.aggressive:
            for t in sorted(gun_targets(s),key=lambda t:abs(t['x']-s['x']))[:3]:
                facing=64 if t['x']<s['x'] else 128
                for jump in [False,True]:
                    for aim in [0,32,16|facing]:aa.append(action('targeted-fire',facing,jump,move=1,after=aim,targetSlot=t['slot'],targetType=t['type']))
                if t['y']<s['y']-24:
                    for offset in [-8,8]:
                        delta=t['x']+offset-s['x']
                        if delta:aa.append(action('align-gun',64 if delta<0 else 128,move=min(96,abs(delta)),after=16,targetSlot=t['slot'],targetType=t['type']))
        for phase in [8,16,24]:aa.append(action('right-jump-phase',128,True,phase=phase))
        if s['stage']>=4:
            aa += [action('up',16),action('jump-up',16,True),action('duck',32),action('drop',32,True),action('left',64),action('up-left',80)]
            for phase in [0,16,32,64,96,128]:aa.append(action('single-right-jump',128,True,single=True,phase=phase))
            if outdoor_boss:
                for direction in [64,128]:
                    for jump in [False,True]:
                        for after in [0,32]:aa.append(action('turn-fire',direction,jump,move=1,after=after))
            boss_types={4:[18,20],5:[19],6:[22],7:[16,21,22]}[s['stage']]
            for t in s['enemies']:
                if t['type'] in boss_types and 0<t['hp']<240 and t['y']<s['y']-24:
                    delta=t['x']-s['x']
                    if delta:aa.append(action('align-outdoor-boss',64 if delta<0 else 128,move=min(80,abs(delta)),after=16))
        if vertical:
            aa += [action('up',16),action('left',64)]
            for phase in [8,16,24]:aa.append(action('left-jump-phase',64,True,phase=phase))
            for direction in [64,128]:
                for move in [32,64]:
                    for phase in [0,16]:aa.append(action('steer-jump',direction,True,move=move,phase=phase))
            dragon=next((t for t in s['enemies'] if t['type']==20 and t['realHP']>0),None)
            if dragon:
                delta=dragon['x']-s['x']
                if delta:aa.append(action('align-dragon',64 if delta<0 else 128,move=min(64,abs(delta)),after=16))
                aa += [action('jump-up',16,True),action('up-left',80),action('up-right',144),action('duck',32)]
    if s['weapon']==4:
        for a in aa:a['continuous']=True
    saved=e.save();frame=e.frame;rows=[]
    for a in aa:
        e.restore(saved,frame);prev_dead=s['dead'];deaths=0;o=s;combat=combat_track(s)
        for f in range(horizon):
            step(e,mask(a,f));r=e.ram();dead=r[0x90]==2
            if dead and not prev_dead:deaths+=1
            prev_dead=dead
            if combat:combat_update(combat,r)
            if r[0x38]==1 or r[0x18]==6 or r[0x30]>s['stage']:break
        o=read(e)
        dead_end=(s['stage'] in [5,6,7] or args.zero_death) and deaths==0 and not o['over'] and not o['victory'] and not can_continue(e,o['lives'])
        value=(o['stage']-s['stage'])*100000 if o['stage']<8 and not o['over'] else 0
        value+=(o['progress']-s['progress'])*3+(0 if indoor or vertical or outdoor_boss else (o['x']-s['x'])*2)-deaths*20000-(100000 if o['over'] else 0)
        if outdoor_boss:value+=(abs(s['x']-outdoor_boss['x'])-abs(o['x']-outdoor_boss['x']))*1.5
        value+=(0 if indoor else (s['y']-o['y'])*.15)+(o['score']-s['score'])*3
        value+=combat_value(combat)
        if s['stage']==5 and 1600<o['progress']<1900:value-=max(0,180-o['y'])*5
        if o['y']>220:value-=200
        if o['water']:value-=40
        types=[17] if s['stage']==0 else ([20,10,8,19] if indoor else {4:[18,20],5:[19],6:[22],7:[16,21,22]}.get(s['stage'],[]))
        for t in s['enemies']:
            if t['type'] in types and 0<t['hp']<240:
                after=next((x for x in o['enemies'] if x['slot']==t['slot'] and x['type']==t['type']),None)
                value+=(t['hp']-(after['hp'] if after else 0))*40
        if indoor:
            core_target=next((t for t in s['enemies'] if t['type']==20 and t['hp']>0),None)
            if core_target:
                aim=max(16,min(240,128+(core_target['x']-128)*2));value+=(abs(s['x']-aim)-abs(o['x']-aim))*1.5
            if o['barrier']==128 and s['barrier']!=128:value+=500
            if s['stage']==1 and s['location']==128:
                for t in s['enemies']:
                    if t['type']==16 and t['realHP']>0:
                        after=next((x for x in o['enemies'] if x['slot']==t['slot'] and x['type']==t['type']),None)
                        value+=(t['realHP']-(after['realHP'] if after else 0))*80
            if s['stage']==3 and s['location']==128:
                for t in s['enemies']:
                    if t['type']==28 and t['var4']>0:
                        after=next((x for x in o['enemies'] if x['slot']==t['slot'] and x['type']==t['type']),None)
                        value+=(t['var4']-(after['var4'] if after else 0))*80
            if s['location']==128 and targets(s):value+=(min(abs(s['x']-t['x']) for t in targets(s))-min(abs(o['x']-t['x']) for t in targets(s)))*1.5
        if vertical and not dragon:value+=(s['y']-o['y'])*2
        if vertical:
            for t in s['enemies']:
                if t['type']==20 and t['realHP']>0:
                    after=next((x for x in o['enemies'] if x['slot']==t['slot'] and x['type']==t['type']),None)
                    before_hp=min(t['hp'],t['realHP'])
                    after_hp=min(after['hp'],after['realHP']) if after else 0
                    value+=(before_hp-after_hp)*80+abs(s['x']-t['x'])-abs(o['x']-t['x'])
                if dragon and t['type']==21 and 0<t['hp']<240:
                    after=next((x for x in o['enemies'] if x['slot']==t['slot'] and x['type']==t['type']),None)
                    value+=(t['hp']-(after['hp'] if after else 0))*40
        if o['boss'] and not s['boss']:value+=10000
        if o['weapon']==3 and s['weapon']!=3:value+=200
        if dead_end:value-=20000
        rows.append((value,a,o,deaths,f+1,dead_end,combat_value(combat)))
    e.restore(saved,frame);rows.sort(key=lambda r:((r[3]==0 and not r[5]) if args.zero_death else True,r[0]),reverse=True)
    best=rows[0]
    safe=best[3]==0 and not best[5]
    if s['stage']>=4 and (not safe or (not outdoor_boss and best[2]['progress']<=s['progress'] and best[6]==0)):
        route=climb_route(e,s,saved,frame,horizontal=True)
        if route and (not safe or route[3]['progress']>s['progress']):
            return route[2],{'name':'safe-escape-route','value':route[0],'commitFrames':len(route[2]),'predicted':{k:route[3][k] for k in ['progress','x','y','lives']}}
    if s['stage']==3 and s['location']==128 and best[0]<80:
        route=boss_route(e,s,saved,frame)
        if route:
            return route[2],{'name':'boss-attack-dodge','value':route[0],'commitFrames':len(route[2]),'predicted':{k:route[3][k] for k in ['progress','x','y','lives']}}
    if vertical and best[2]['progress']<=s['progress'] and not any(t['type']==20 and t['realHP']>0 for t in s['enemies']):
        route=climb_route(e,s,saved,frame)
        if route:
            return route[2],{'name':'multi-platform-route','value':route[0],'commitFrames':len(route[2]),'predicted':{k:route[3][k] for k in ['progress','x','y','lives']}}
    # Execute the already simulated safe climbing macro. Replanning every 16
    # frames can indefinitely defer its later jump or reverse before landing.
    if vertical and safe and not best[2]['over'] and best[2]['lives']>=s['lives'] and best[2]['progress']>s['progress']:
        commit=best[4]
    if dragon and safe and best[0]>70 and not best[2]['over'] and best[2]['lives']>=s['lives']:
        commit=best[4]
    if indoor and s['location']==128 and safe and best[0]>80 and not best[2]['over'] and best[2]['lives']>=s['lives']:
        commit=best[4]
    if indoor and s['location']==1 and safe and best[0]>80 and not best[2]['over'] and best[2]['lives']>=s['lives']:
        commit=best[4]
    if s['stage']>=4 and safe and best[2]['progress']>s['progress'] and not best[2]['over'] and best[2]['lives']>=s['lives']:
        commit=best[4]
    if outdoor_boss and safe and best[0]>80 and not best[2]['over'] and best[2]['lives']>=s['lives']:
        commit=best[4]
    if args.aggressive and safe and best[6]>100:commit=best[4]
    return [mask(best[1],f) for f in range(commit)],{'name':best[1]['name'],'action':best[1],'value':best[0],'combatValue':best[6],'commitFrames':commit,'predicted':{k:best[2][k] for k in ['progress','x','y','lives']}}
e=make();actions=[];samples=[];visits=[0];deaths=0;previous=None
def submit(m):
    global previous,deaths
    step(e,m)
    if actions and actions[-1][0]==m:actions[-1][1]+=1
    else:actions.append([m,1])
    o=read(e)
    if o['status']==5 and o['stage']<8 and o['stage']!=visits[-1]:visits.append(o['stage'])
    if previous and o['dead'] and not previous['dead']:deaths+=1
    previous=o
start=time.perf_counter()
try:
    if args.resume:
        prefix=json.loads(Path(args.resume).read_text())
        assert prefix['replayEqual'] and prefix['coreSha256']==manifest['coreSha256'] and prefix['romSha256']==manifest['romSha256']
        for m,n in prefix['actions']:
            for _ in range(n):
                if args.prefix_frames and e.frame>=args.prefix_frames:break
                submit(m)
            if args.prefix_frames and e.frame>=args.prefix_frames:break
    else:
        for m,n in [(0,120),(8,1),(0,29),(8,1),(0,629)]:
            for _ in range(n):submit(m)
        o=read(e);assert o['stage']==0 and o['status']==5 and o['lives']==2,o
    (dir/'initial.state').write_bytes(e.save());plans=0
    o=read(e);e.picture().save(dir/'latest.png')
    (ROOT/'runs/native-status.json').write_text(json.dumps({'status':'running','dir':dir.name,'objective':manifest['objective'],'deaths':deaths,**{k:o[k] for k in ['frame','stage','progress','x','y','lives']}}))
    while e.frame<args.frames:
        o=read(e)
        if o['over'] or o['victory'] or o['stage']>=args.stop_stage or (args.zero_death and deaths>0) or (dir/'stop.request').exists():break
        sequence,decision=choose(e);plans+=1
        for m in sequence:
            submit(m);o=read(e)
            if o['over'] or o['victory'] or o['stage']>=args.stop_stage or (args.zero_death and deaths>0):break
        if plans%1==0:
            row={**read(e),'decision':decision};samples.append(row)
            with (dir/'trace.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
            status={'status':'running','dir':dir.name,'objective':manifest['objective'],'deaths':deaths,**{k:row[k] for k in ['frame','stage','progress','x','y','lives']}}
            (ROOT/'runs/native-status.json').write_text(json.dumps(status));print(json.dumps(status),flush=True)
            e.picture().save(dir/'latest.png');(dir/'latest.state').write_bytes(e.save())
    final=read(e);expected=e.fingerprint();(dir/'final.state').write_bytes(e.save());e.picture().save(dir/'final.png');e.close()
    result={'scope':manifest['scope'],'objective':manifest['objective'],'combatStyle':manifest['combatStyle'],'romSha256':manifest['romSha256'],'coreSha256':manifest['coreSha256'],'frames':e.frame,'final':final,'deaths':deaths,'stageVisits':visits,'replayEqual':False,'expected':expected,'fullGameClearVerified':False,'actions':actions,'samples':samples}
    (dir/'result.json').write_text(json.dumps(result))
    subprocess.run([sys.executable,str(ROOT/'native-replay.py'),str(dir/'result.json')],check=True,capture_output=True,text=True)
    audit=json.loads((dir/'independent-audit.json').read_text());actual=audit['actual'];equal=actual==expected
    verifier=(ROOT/'native-replay.py').read_bytes();(dir/'native-replay.py').write_bytes(verifier)
    result.update(actual=actual,replayEqual=equal,replayMethod='fresh_process',verifierSha256=sha(verifier),fullGameClearVerified=final['victory'] and equal and visits[:8]==list(range(8)),wallSeconds=time.perf_counter()-start)
    result['oneLifeClearVerified']=result['fullGameClearVerified'] and deaths==0 and audit.get('deaths')==0 and audit.get('stageVisits')==list(range(8))
    (dir/'result.json').write_text(json.dumps(result));(ROOT/'runs/native-status.json').write_text(json.dumps({'status':'completed','dir':dir.name,'objective':manifest['objective'],'deaths':deaths,'oneLifeClearVerified':result['oneLifeClearVerified'],'frame':e.frame,'stage':final['stage'],'replayEqual':equal}))
    subprocess.run(['node',str(ROOT/'report.cjs')],check=True,capture_output=True)
    print(json.dumps({k:v for k,v in result.items() if k not in ['actions','samples','expected','actual']}),flush=True);print('RESULTS '+str(dir),flush=True)
finally:e.close()
