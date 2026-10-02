"""Scene and frame boundaries must not alter a previously accepted prefix."""
from orlegend_bt import Controller
spec={'parameters':{},'tree':{'type':'selector','children':[
    {'type':'sequence','children':[{'type':'condition','name':'plan_ready','params':{'scenes':[512,513],'frames':3,'start_frame':100}},
     {'type':'action','name':'input_plan','params':{'start_frame':100,'runs':[{'frames':2,'buttons':['right']},{'frames':1,'buttons':['up']}]}}]},
    {'type':'action','name':'input_plan','params':{'runs':[{'frames':100,'buttons':[]}]}}]}}
c=Controller(spec)
def choose(scene,frame):return c.choose({'stage_raw':scene,'enemies':[]},frame)
assert choose(512,99)==[]
assert choose(512,100)==['right']
assert choose(513,101)==['right']
assert choose(513,102)==['up']
assert choose(513,103)==[]
assert choose(514,101)==[]
print('Input-plan frame boundaries and scene transitions: PASS')
