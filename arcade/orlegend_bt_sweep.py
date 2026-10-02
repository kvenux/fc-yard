"""Cold-start, first-death-stopped parameter sweeps; never continue or restore."""
import argparse, concurrent.futures, copy, itertools, json, subprocess, sys, time
from pathlib import Path

def execute(job):
    path, output, stage, frames = job
    with Path(str(output)+'.log').open('w') as log:
        p=subprocess.run([sys.executable,str(Path(__file__).with_name('orlegend_bt_train.py')),
          '--tree',str(path),'--output',str(output),'--stop-stage',str(stage),
          '--frames',str(frames),'--first-death'],stdout=log,stderr=subprocess.STDOUT)
    if p.returncode: return {'name':output.name,'error':p.returncode}
    r=json.loads((output/'result.json').read_text())
    return {'name':output.name,'reason':r['reason'],'frames':r['frames'],
            'deaths':r['deaths'],'hp':r['after']['hp'],'scene':r['after']['stage_raw'],
            'damage':r['damage'],'wall':r['wall_seconds']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--base',default='arcade/orlegend-bt-deployed.json')
    p.add_argument('--output',required=True);p.add_argument('--mode',choices=['boss1','combat1','opening1','super1','super1refine','item1','bosscombat1','lateboss1','gate2','gaterecover2','gatepoint2','gatedetour2','combat2','bosscombat2','telegraph2','projectile2','velocity2','selectitems2','burstcharge2','carrycharge2','cave2','caveroute','cavefire','cavezigzag','caveadaptive','cavelocal','cavedash','super2','super2boss'],required=True)
    p.add_argument('--workers',type=int,default=6);a=p.parse_args()
    root=Path(a.output);root.mkdir(parents=True,exist_ok=False)
    base=json.loads(Path(a.base).read_text());jobs=[];started=time.perf_counter()
    if a.mode=='boss1':
        grid=itertools.product([48,56,64,72,80,96],[4,8,12,20],[45,90,150])
        for dx,hold,cool in grid:
            s=copy.deepcopy(base);branch=s['tree']['children'][0]['children']
            branch[0]['params']['dx']=dx;branch[1]['params'].update(hold=hold,cooldown=cool)
            name=f'dx{dx}-hold{hold}-cool{cool}';path=root/(name+'.json');path.write_text(json.dumps(s))
            jobs.append((path,root/name,1,35000))
    elif a.mode=='lateboss1':
        for dx,dy,hold in itertools.product([96,160,220],[20,40],[8,16]):
            s=copy.deepcopy(base);branch={'type':'sequence','children':[{'type':'condition','name':'boss_close','params':{'scenes':[3],'min_hp':1,'max_hp':80,'known_boss':True,'dx':dx,'dy':dy}},{'type':'action','name':'evade_vertical','params':{'min_hp':1,'hold':hold,'displacement':24,'cooldown':90,'min_y':90,'max_y':220}}]}
            s['tree']['children'].insert(0,branch);name=f'dx{dx}-dy{dy}-hold{hold}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,1,50000))
    elif a.mode=='bosscombat1':
        for distance,align,jump,rush in itertools.product([40,56,72],[10,14],[0,60,120],[0,30]):
            s=copy.deepcopy(base);branch={'type':'sequence','children':[{'type':'condition','name':'combat_phase','params':{'scenes':[3],'min_hp':1,'known_boss':True,'dx':240}},{'type':'action','name':'combat','params':{'distance':distance,'align':align,'jump':jump,'rush':rush}}]}
            # Keep the validated charge/super/evasion priorities; change only boss combat.
            s['tree']['children'].insert(7,branch)
            name=f'd{distance}-a{align}-j{jump}-r{rush}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,1,50000))
    elif a.mode=='item1':
        for ids,dx,dy in itertools.product([[9],[9,6],[6]],[120,220,320],[20,60]):
            s=copy.deepcopy(base)
            branch={'type':'sequence','children':[{'type':'condition','name':'item_ready','params':{'scenes':[3],'ids':ids,'min_hp':100,'dx':dx,'dy':dy}},{'type':'action','name':'use_item','params':{'timeout':45,'cooldown':180}}]}
            s['tree']['children'].insert(0,branch)
            name=f'ids'+('-'.join(map(str,ids)))+f'-dx{dx}-dy{dy}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,1,50000))
    elif a.mode=='super1refine':
        for meter,boss,fast,dx in itertools.product([0,96],[False,True],[False,True],[220,300]):
            s=copy.deepcopy(base);children=s['tree']['children']
            children[0]['children'][0]['params']['min_meter']=meter
            children[1]['children'][0]['params']['dx']=dx
            children[1]['children'][1]['params'].update(boss_focus=fast,fast_prepare=fast)
            children[2]['children'][0]['params'].update(require_boss=boss,safe_dx=0 if meter==96 else 150)
            name=f'meter{meter}-boss{int(boss)}-fast{int(fast)}-dx{dx}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,1,50000))
    elif a.mode=='super1':
        for index,(clear,dx,dy,hold) in enumerate(itertools.product([False,True],[120,220],[20,60],[2,4])):
            s=copy.deepcopy(base);branches=[]
            if clear:branches.append({'type':'sequence','children':[{'type':'condition','name':'crowd_fire','params':{'scenes':[3],'reserve':2,'range_x':700,'range_y':200,'crowd':3,'allowed_player_states':[2]}},{'type':'action','name':'use_fire','params':{'timeout':45,'cooldown':180}}]})
            branches += [
                {'type':'sequence','children':[{'type':'condition','name':'super_ready','params':{'scenes':[3],'dx':dx,'dy':dy,'min_hp':80}},{'type':'action','name':'super_command','params':{'hold':hold,'cooldown':30}}]},
                {'type':'sequence','children':[{'type':'condition','name':'charge_ready','params':{'scenes':[3],'safe_dx':150 if clear else 0}},{'type':'action','name':'charge_meter','params':{'timeout':600}}]}]
            s['tree']['children']=branches+s['tree']['children']
            name=f'clear{int(clear)}-dx{dx}-dy{dy}-h{hold}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,1,50000))
    elif a.mode=='opening1':
        for distance,align,jump,rush in itertools.product([32,48,56,64,80],[8,14],[0,120],[0,30]):
            s=copy.deepcopy(base)
            for scene in ['0','1']:s['parameters']['scenes'][scene].update(distance=distance,align=align,jump=jump,rush=rush)
            name=f'd{distance}-a{align}-j{jump}-r{rush}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,1,35000))
    elif a.mode=='combat1':
        for distance,align,jump in itertools.product([32,40,48,56,64],[6,10,14,20],[0,60,120]):
            s=copy.deepcopy(base);s['parameters']['scenes']['3'].update(distance=distance,align=align,jump=jump)
            name=f'd{distance}-a{align}-j{jump}';path=root/(name+'.json');path.write_text(json.dumps(s))
            jobs.append((path,root/name,1,35000))
    elif a.mode=='burstcharge2':
        for safe,hold,cooldown,dx in itertools.product([120,180],[40,80],[15,40],[200,300]):
            s=copy.deepcopy(base);s['parameters']['scenes']['257']['reserve_meter']=True
            charge={'type':'sequence','children':[{'type':'condition','name':'charge_ready','params':{'scenes':[257],'min_x':700,'min_y':380,'safe_dx':safe,'safe_dy':60}},{'type':'action','name':'charge_meter','params':{'abort_on_threat':True,'safe_dx':safe,'safe_dy':60,'max_hold':hold,'cooldown':cooldown,'timeout':600}}]}
            index=next(i for i,n in enumerate(s['tree']['children']) if n.get('children',[{}])[0].get('name')=='route');s['tree']['children'].insert(index,charge)
            s['tree']['children'].insert(0,{'type':'sequence','children':[{'type':'condition','name':'super_ready','params':{'scenes':[257],'known_boss':True,'min_hp':1,'dx':dx,'dy':80}},{'type':'action','name':'super_command','params':{'known_boss':True,'hold':2,'fast_prepare':True,'cooldown':30}}]})
            name=f'safe{safe}-hold{hold}-cool{cooldown}-dx{dx}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,2,90000))
    elif a.mode=='selectitems2':
        for ids,dx,dy in itertools.product([[6],[6,9],[6,9,2],[9,6]],[180,300],[24,60]):
            s=copy.deepcopy(base);branch={'type':'sequence','children':[{'type':'condition','name':'item_ready','params':{'scenes':[257],'choose':True,'ids':ids,'min_hp':100,'min_dx':0,'dx':dx,'dy':dy}},{'type':'action','name':'select_item','params':{'ids':ids,'timeout':45,'cooldown':120}}]}
            s['tree']['children'].insert(0,branch);name='ids'+('-'.join(map(str,ids)))+f'-dx{dx}-dy{dy}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,2,90000))
    elif a.mode=='velocity2':
        for speed,dx,hold,cooldown in itertools.product([4,6],[160,240],[16,30],[15,45]):
            s=copy.deepcopy(base);branch={'type':'sequence','children':[{'type':'condition','name':'boss_close','params':{'scenes':[257],'known_boss':True,'min_hp':1,'closing_speed':speed,'channel':'charge','dx':dx,'dy':40}},{'type':'action','name':'evade_vertical','params':{'known_boss':True,'min_hp':1,'channel':'charge','hold':hold,'displacement':64,'cooldown':cooldown,'min_y':370,'max_y':520}}]}
            s['tree']['children'].insert(0,branch);name=f'speed{speed}-dx{dx}-hold{hold}-cool{cooldown}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,2,90000))
    elif a.mode=='bosscombat2':
        for mode,distance,align,focus in itertools.product(['legacy','spacing'],[32,56,80],[8,14],[False,True]):
            s=copy.deepcopy(base);branch={'type':'sequence','children':[{'type':'condition','name':'combat_phase','params':{'scenes':[257],'min_hp':1,'known_boss':True,'dx':400}},{'type':'action','name':'combat','params':{'combat':mode,'distance':distance,'stand_distance':distance,'align':align,'stand_align':align,'rush':0,'jump':0,'focus_known_boss':focus}}]}
            index=next(i for i,n in enumerate(s['tree']['children']) if n.get('children',[{}])[0].get('name')=='route');s['tree']['children'].insert(index,branch)
            name=f'{mode}-d{distance}-a{align}-focus{int(focus)}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,2,90000))
    elif a.mode=='projectile2':
        for dx,dy,hold in itertools.product([480,800],[24,48],[8,16,30]):
            s=copy.deepcopy(base);branch={'type':'sequence','children':[{'type':'condition','name':'boss_close','params':{'scenes':[257],'known_boss':True,'min_hp':1,'enemy_states':[3],'enemy_moves':[4],'channel':'projectile','dx':dx,'dy':dy}},{'type':'action','name':'evade_vertical','params':{'known_boss':True,'min_hp':1,'channel':'projectile','hold':hold,'displacement':64,'cooldown':30,'min_y':370,'max_y':520}}]}
            s['tree']['children'].insert(0,branch);name=f'dx{dx}-dy{dy}-hold{hold}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,2,90000))
    elif a.mode=='carrycharge2':
        for pos,minhp,hold in itertools.product([1400,1700],[1,80],[2,4]):
            s=copy.deepcopy(base);branches=[{'type':'sequence','children':[{'type':'condition','name':'charge_ready','params':{'scenes':[256],'min_x':pos,'safe_dx':10000,'safe_dy':10000}},{'type':'action','name':'charge_meter','params':{'timeout':600}}]},
                {'type':'sequence','children':[{'type':'condition','name':'super_ready','params':{'scenes':[257],'min_hp':minhp,'dx':220,'dy':60}},{'type':'action','name':'super_command','params':{'hold':hold,'cooldown':30,'fast_prepare':True}}]}]
            s['tree']['children']=branches+s['tree']['children'];name=f'x{pos}-minhp{minhp}-hold{hold}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,2,90000))
    elif a.mode=='telegraph2':
        for dx,dy,hold,focus in itertools.product([160,240],[40,80],[16,30],[False,True]):
            s=copy.deepcopy(base);s['parameters']['scenes']['257']['focus_known_boss']=focus
            branch={'type':'sequence','children':[{'type':'condition','name':'boss_close','params':{'scenes':[257],'known_boss':True,'min_hp':1,'enemy_states':[3],'dx':dx,'dy':dy}},{'type':'action','name':'evade_vertical','params':{'known_boss':True,'min_hp':1,'hold':hold,'displacement':64,'cooldown':45,'min_y':370,'max_y':520}}]}
            s['tree']['children'].insert(0,branch);name=f'dx{dx}-dy{dy}-hold{hold}-focus{int(focus)}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,2,90000))
    elif a.mode=='combat2':
        for mode,distance,cycle,focus in itertools.product(['combo','rush','cancel','spacing'],[32,56,80],[24,40],[False,True]):
            s=copy.deepcopy(base);s['parameters']['scenes']['257'].update(combat=mode,stand_distance=distance,stand_align=14,cycle=cycle,boss_focus=focus)
            name=f'{mode}-d{distance}-c{cycle}-focus{int(focus)}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,2,90000))
    elif a.mode=='gatedetour2':
        for end,stall in itertools.product([1700,1800,1900],[10,30,60]):
            s=copy.deepcopy(base);s['parameters']['scenes']['256'].update(gate_detour=True,gate_detour_start=1500,gate_detour_end=end)
            s['parameters']['scenes']['257']={'cave_mode':'adaptive','cave_stall_axis':'xy','cave_stall':stall,'cave_jump':90,'cave_clock':'local'}
            name=f'end{end}-stall{stall}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,2,90000))
    elif a.mode=='gatepoint2':
        for gx,gy in itertools.product([1496,1540,1580,1700,1960],[96,110,125,146]):
            s=copy.deepcopy(base);s['parameters']['scenes']['256'].update(gate_start=1400,gate_x=gx,gate_y=gy)
            s['parameters']['scenes']['257']={'cave_mode':'adaptive','cave_stall_axis':'xy','cave_stall':30,'cave_jump':90,'cave_clock':'local'}
            name=f'x{gx}-y{gy}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,2,90000))
    elif a.mode=='gaterecover2':
        for stall,hold in itertools.product([12,30,60],[15,30,60]):
            s=copy.deepcopy(base);s['parameters']['scenes']['256'].update(nav_y=140,nav_attack=4,nav_recover=True,nav_stall=stall,nav_recover_hold=hold)
            s['parameters']['scenes']['257']={'cave_mode':'adaptive','cave_stall_axis':'xy','cave_stall':30,'cave_jump':90,'cave_clock':'local'}
            name=f'stall{stall}-hold{hold}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,2,90000))
    elif a.mode=='gate2':
        for y,attack in itertools.product([124,140,156,180],[4,8,12]):
            s=copy.deepcopy(base);s['parameters']['scenes']['256'].update(nav_y=y,nav_attack=attack)
            s['parameters']['scenes']['257']={'cave_mode':'adaptive','cave_stall_axis':'xy','cave_stall':60,'cave_jump':90}
            name=f'y{y}-a{attack}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,2,90000))
    elif a.mode in ('super2','super2boss'):
        for safe,dx,dy,item in itertools.product([0,150,300],[180,260],[24,60],[False,True]):
            s=copy.deepcopy(base);s['parameters']['scenes'].setdefault('257',{'cave_mode':'adaptive','cave_stall_axis':'xy','cave_stall':60,'cave_jump':90})
            # New branches apply only to chapter two, keeping accepted chapter one exact.
            branches=[{'type':'sequence','children':[{'type':'condition','name':'super_ready','params':{'scenes':[257],'dx':dx,'dy':dy,'min_hp':80}},{'type':'action','name':'super_command','params':{'hold':2,'cooldown':30,'boss_focus':True,'fast_prepare':True}}]},
                      {'type':'sequence','children':[{'type':'condition','name':'charge_ready','params':{'scenes':[257],'safe_dx':safe,'safe_dy':80,'min_y':380}},{'type':'action','name':'charge_meter','params':{'timeout':600}}]}]
            if item:branches.insert(0,{'type':'sequence','children':[{'type':'condition','name':'item_ready','params':{'scenes':[257],'ids':[9,6],'min_hp':100,'dx':220,'dy':60}},{'type':'action','name':'use_item','params':{'timeout':45,'cooldown':180}}]})
            if a.mode=='super2boss':branches[-1]['children'][0]['params'].update(require_boss=True,safe_dy=16)
            s['tree']['children']=branches+s['tree']['children']
            name=f'safe{safe}-dx{dx}-dy{dy}-item{int(item)}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,2,90000))
    elif a.mode=='cavedash':
        for dash,jump,stall in itertools.product([24,40,60,90],[0,90],[30,60]):
            s=copy.deepcopy(base);s['parameters']['scenes']['257'].update(cave_mode='adaptive',cave_clock='local',cave_stall_axis='xy',cave_stall=stall,cave_jump=jump,cave_dash=dash)
            name=f'dash{dash}-j{jump}-stall{stall}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,2,90000))
    elif a.mode=='cavelocal':
        for axis,stall,jump,attack in itertools.product(['xy','y'],[10,30,60],[30,60,90],[0,4]):
            s=copy.deepcopy(base);s['parameters']['scenes']['257']={'cave_mode':'adaptive','cave_stall_axis':axis,'cave_stall':stall,'cave_jump':jump,'cave_clock':'local','cave_attack':attack}
            name=f'axis{axis}-stall{stall}-j{jump}-a{attack}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,2,90000))
    elif a.mode=='caveadaptive':
        for axis,stall,jump in itertools.product(['xy','y'],[10,30,60],[30,60,90]):
            s=copy.deepcopy(base);s['parameters']['scenes']['257']={'cave_mode':'adaptive','cave_stall_axis':axis,'cave_stall':stall,'cave_jump':jump}
            name=f'axis{axis}-stall{stall}-j{jump}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,2,65000))
    elif a.mode=='cavezigzag':
        for turn,jump,attack in itertools.product([180,210,225,230],[20,30,60,90],[0,4]):
            s=copy.deepcopy(base);s['parameters']['scenes']['257']={'cave_mode':'zigzag','cave_turn_y':turn,'cave_jump':jump,'cave_attack':attack}
            name=f'turn{turn}-j{jump}-a{attack}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,2,65000))
    elif a.mode=='cavefire':
        for index,(mode,reserve,crowd) in enumerate(itertools.product(['legacy','dash','slope','combat','points'],[0,1,2],[1,2])):
            s=copy.deepcopy(base);s['parameters']['scenes']['257']={'cave_mode':mode,'cave_jump':0,'cave_points':[[160,330],[350,430],[750,430]],'cave_axis':'x'}
            branch={'type':'sequence','children':[{'type':'condition','name':'crowd_fire','params':{'scenes':[257],'reserve':reserve,'range_x':700,'range_y':400,'crowd':crowd,'allowed_player_states':[2]}},{'type':'action','name':'use_fire','params':{'timeout':45,'cooldown':180}}]}
            s['tree']['children'].insert(0,branch)
            name=f'{mode}-reserve{reserve}-crowd{crowd}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,2,65000))
    elif a.mode=='caveroute':
        variants=[{'cave_mode':m} for m in ['legacy','combat','right','down']]
        variants += [{'cave_mode':'points','cave_points':[[px,330],[350,430],[750,430]],'cave_axis':axis} for px,axis in itertools.product([80,160,250,350,500],['x','y'])]
        for index,(variant,attack,jump) in enumerate(itertools.product(variants,[0,4],[0,90])):
            s=copy.deepcopy(base);s['parameters']['scenes']['257']={**variant,'cave_attack':attack,'cave_jump':jump}
            name=f'route{index:03d}';path=root/(name+'.json');path.write_text(json.dumps(s));jobs.append((path,root/name,2,65000))
    else:
        for distance,align,rush,focus in itertools.product([32,48,64],[8,16,24],[0,30],[None,3]):
            s=copy.deepcopy(base);s['parameters']['scenes']['257']={'distance':distance,'align':align,'rush':rush}
            if focus is not None:s['parameters'].setdefault('focus_slot',{})['257']=focus
            name=f'd{distance}-a{align}-r{rush}-focus{focus}';path=root/(name+'.json');path.write_text(json.dumps(s))
            jobs.append((path,root/name,2,90000))
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for future in concurrent.futures.as_completed([ex.submit(execute,j) for j in jobs]):
            row=future.result();rows.append(row)
            (root/'summary.json').write_text(json.dumps({'mode':a.mode,'wall':time.perf_counter()-started,'completed':len(rows),'total':len(jobs),'results':rows},indent=2))
            print(json.dumps(row),flush=True)
    winners=sorted([r for r in rows if r.get('reason')=='chapter_passed'],key=lambda r:(-r['hp'],r['frames']))
    print('WINNERS',json.dumps(winners[:10]),flush=True)

if __name__=='__main__':main()
