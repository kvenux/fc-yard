"""Practice calibration of actual damage and HP cost using normal input only."""
import itertools,json
from pathlib import Path
from emulator import Emulator
from orlegend import ROM,action
from orlegend_bt_train import observation
from orlegend_bt import Controller
base=Path('arcade/runs/orlegend/bt');out=base/'one-life-ch4-boss-dps-practice-06';out.mkdir(exist_ok=False)
plan=json.loads((base/'one-life-ch4-second-parallel-beam-practice-03/plan.json').read_text());e=Emulator(ROM,deterministic=True,headless=True);e.restore((base/'one-life-ch4-plan-cold-02/plan-endpoint.state').read_bytes());found=False;frame=0
for macro in plan['macros']:
    for buttons in macro['inputs']:
        e.step(buttons);frame+=1;o=observation(e)
        if o['player_state']==2 and not o['air_mask'] and any(v['hp']>=400 and abs(v['x']-o['x'])<140 and abs(v['y']-o['y'])<90 for v in o['enemies']):found=True;break
    if found:break
assert found,'No boss checkpoint before the deadline'
state=e.save();initial=observation(e);(out/'initial.state').write_bytes(state);rows=[]
spec=json.loads(Path('arcade/orlegend-bt-ch4-search-policy.json').read_text())
variants=[('item',p) for p in [15,8,19]]+[('aimed_item',p) for p in [15,8,19]]
try:
    for mode,period in variants:
        e.restore(state);old=observation(e);slots={v['slot'] for v in old['enemies'] if v['hp']>=100};damage=lost=0;ctrl=Controller(spec);inputs=[]
        if mode in ('item','aimed_item'):
            import copy
            item_spec=copy.deepcopy(spec);item_spec['tree']['children'].insert(0,{'type':'sequence','children':[{'type':'condition','name':'item_ready','params':{'scenes':[770],'choose':True,'ids':[period],'min_hp':100,'dx':800,'dy':500}},{'type':'action','name':'aimed_item' if mode=='aimed_item' else 'select_item','params':{'ids':[period],'min_hp':100,'aim_y':14,'radial_select':True,'timeout':45,'cooldown':180}}]});ctrl=Controller(item_spec)
        for t in range(600):
            targets=[v for v in old['enemies'] if v['slot'] in slots] or old['enemies']
            enemy=min(targets,key=lambda v:abs(v['x']-old['x'])) if targets else None
            o={**old,'enemies':targets};c={'distance':40,'align':8,'period':period or 4,'jump':0,'rush':0}
            if mode in ('super','item','aimed_item'):buttons=ctrl.choose(o,t)
            else:
                buttons=[];face='right' if enemy and enemy['x']>=o['x'] else 'left'
                if enemy:
                    if abs(enemy['x']-o['x'])>40 or t%60==0:buttons.append(face)
                    if abs(enemy['y']-o['y'])>8:buttons.append('up' if enemy['y']<o['y'] else 'down')
                phase=t%period
                if mode=='attack' and phase<max(1,period//2):buttons.append('attack')
                if mode=='combo':
                    if phase in (0,1,4,5):buttons.append('attack')
                    elif phase in (8,9):buttons=[face,'down','jump']
                if mode=='rush' and phase<2:buttons=[face,'down','jump']
                if mode=='jumpattack':
                    if phase<2:buttons=[v for v in buttons if v!='down']+['jump']
                    elif 6<=phase<8:buttons.append('attack')
            e.step(buttons);now=observation(e);inputs.append(buttons);prev={v['slot']:v['hp'] for v in old['enemies']}
            damage+=sum(max(0,prev.get(v['slot'],v['hp'])-v['hp']) for v in now['enemies'] if v['slot'] in slots)
            lost+=max(0,old['hp']-now['hp']) if 0<=now['hp']<old['hp']<=72 else 0;old=now
            if old['lives']<initial['lives'] or old['hp']==0:break
        name=f'{mode}-{period}';row={'name':name,'frames':t+1,'boss_damage':damage,'hp_lost':lost,'after':old};rows.append(row);(out/(name+'-inputs.json')).write_text(json.dumps(inputs));(out/(name+'.state')).write_bytes(e.save());(out/'result.json').write_text(json.dumps({'scope':'checkpoint practice only','local_checkpoint_frame':frame,'initial':initial,'results':rows},indent=2));print(json.dumps(row),flush=True)
finally:e.close()


