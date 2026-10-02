"""Practice-only save-state beam search. Export ordinary inputs for cold validation."""
import argparse,json,time,hashlib
from pathlib import Path
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
from orlegend_bt import Controller

def keys(name,o,t):
    if name=='loot':
        from orlegend import action
        target=o.get('tree',[-1,-1])
        if not(0<=target[0]<10000 and 60<=target[1]<=600):return []
        return action({**o,'enemies':[{'slot':-1,'x':target[0],'y':target[1],'hp':1}]},t,{'distance':12,'align':5,'jump':0,'rush':0,'period':4})
    if name=='rush':
        if not o['enemies']:return ['right']
        enemy=min(o['enemies'],key=lambda e:abs(e['x']-o['x'])+3*abs(e['y']-o['y']))
        dx,dy=enemy['x']-o['x'],enemy['y']-o['y'];face='right' if dx>=0 else 'left';movement=[]
        if abs(dx)>56 or t%24==0:movement.append(face)
        if abs(dy)>12:movement.append('down' if dy>0 else 'up')
        if abs(dx)<120 and abs(dy)<24 and t%24<2:return [face,'down','jump']
        return movement+(['attack'] if t%24>=8 and t%4<2 else [])
    if name=='combat':
        from orlegend import action
        return action(o,t,{'distance':56,'align':14,'jump':0,'rush':0,'period':4})
    if name=='charge':return ['attack','jump','c']
    bits=name.split('+');movement=[k for k in bits if k in ('up','down','left','right')]
    if 'jump' in bits and t%30<2:return [k for k in movement if k!='down']+['jump']
    if 'attack' in bits and t%4<2:return movement+['attack']
    return movement

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--state',required=True);ap.add_argument('--output',required=True);ap.add_argument('--width',type=int,default=12);ap.add_argument('--depth',type=int,default=45);ap.add_argument('--hold',type=int,default=60);ap.add_argument('--goal',choices=['cave','combat'],default='cave');ap.add_argument('--policy');a=ap.parse_args()
    out=Path(a.output);out.mkdir(exist_ok=False);e=Emulator(ROM,deterministic=True,headless=True);e.restore(Path(a.state).read_bytes());initial=observation(e);start=time.perf_counter();simulated=0
    assert initial['hp']>0
    target_chapter=initial['stage_byte']+1
    actions=['down+right','down+left','right','left','down','up','down+right+jump','down+left+jump','right+jump','left+jump','down+attack','right+attack','combat']
    if a.goal=='combat':actions=['combat','left+attack','right+attack','up+attack','down+attack','up','down','left+jump','right+jump','policy','charge']
    policy=json.loads(Path(a.policy).read_text()) if a.policy else None
    beam=[{'state':e.save(),'o':initial,'plan':[],'elapsed':0,'damage_done':0}];goals=[]
    try:
        for depth in range(a.depth):
            candidates=[]
            for parent in beam:
                for name in actions:
                    e.restore(parent['state']);old=parent['o'];done=parent['damage_done'];inputs=[];valid=True;passed=False
                    ctrl=Controller(policy) if name=='policy' else None
                    policy_length=10 if not old['enemies'] else 4
                    for t in range(a.hold*(policy_length if name=='policy' else 2 if name=='charge' else 1)):
                        k=ctrl.choose(old,parent['elapsed']+t) if ctrl else keys(name,old,t);e.step(k);simulated+=1;now=observation(e);inputs.append(k)
                        if now['lives']<initial['lives'] or now['hp']<=0:valid=False;break
                        if now['stage_byte']>=target_chapter:old=now;passed=True;break
                        if now['stage_raw']!=initial['stage_raw'] and a.goal=='cave':valid=False;break
                        prev={v['slot']:v for v in old['enemies']}
                        done+=sum(max(0,prev[v['slot']]['hp']-v['hp']) for v in now['enemies'] if v['slot'] in prev)
                        old=now
                    if not valid:continue
                    # First solve the narrow cave with maximum remaining HP.
                    progress=min(old['y'],430)*.16+min(old['x'],700)*.06
                    score=old['hp']*20+progress+min(done,100)*.04
                    if a.goal=='combat':
                        progress=min(old['x'],1500)*.04
                        # Chapter-three final exit is to the left; avoid rewarding a dead end.
                        if old['stage_raw']==514:progress=-abs(old['x']-170)*.08-abs(old['y']-90)*.04
                        elif old['stage_raw']==513 and not old['enemies']:progress=-abs(old['x']-995)*.08-abs(old['y']-115)*.04
                        score=old['hp']*20+done*.8+progress+old['resources']['meter']*.2+(100000 if passed else 0)
                    node={'state':e.save(),'o':old,'plan':parent['plan']+[{'name':name,'inputs':inputs}],'elapsed':parent['elapsed']+len(inputs),'damage_done':done,'score':score}
                    if passed or (a.goal=='cave' and old['x']>=700 and old['y']>=380):goals.append(node)
                    else:candidates.append(node)
            candidates.sort(key=lambda n:n['score'],reverse=True);beam=[];seen=set()
            for n in candidates:
                o=n['o'];signature=(o['x']//25,o['y']//15,o['hp'],o['player_state'],o['resources']['meter']//16,tuple((v['slot'],v['hp']//5,v['x']//100,v['y']//40) for v in o['enemies']))
                if signature in seen:continue
                seen.add(signature);beam.append(n)
                if len(beam)>=a.width:break
            best=max(goals or beam,key=lambda n:(n['o']['hp'],n['score'])) if goals or beam else None
            summary={'scope':'checkpoint practice only; not a cold clear','depth':depth+1,'simulated_frames':simulated,'wall':time.perf_counter()-start,'goals':len(goals),'best':{k:best[k] for k in ('o','elapsed','damage_done','score')} if best else None}
            (out/'progress.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
            if best:
                (out/'best.state').write_bytes(best['state']);(out/'plan.json').write_text(json.dumps({'initial':initial,'after':best['o'],'macros':best['plan']},indent=2))
            if not beam or (goals and max(n['o']['hp'] for n in goals)==initial['hp']):break
    finally:e.close()

if __name__=='__main__':main()
