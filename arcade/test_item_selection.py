"""Menu opening feedback, absolute slot directions, and element reserves."""
from orlegend_bt import Controller
c=Controller({'parameters':{},'tree':{'type':'action','name':'input_plan','params':{'runs':[{'frames':1,'buttons':[]}]}}})
def obs(selected=2,opened=False,fire=3):
 return {'stage_raw':770,'player_state':2,'x':100,'y':100,'enemies':[{'slot':0,'hp':520,'x':120,'y':100}],
         'resources':{'inventory':[{'id':15,'count':fire},{'id':8,'count':1},{'id':19,'count':1}],'selected':selected,'menu_open':opened}}
p={'ids':[15],'radial_select':True,'reserves':{'15':1}}
m={}
assert c.select_item({'o':obs(),'frame':0},m,p).buttons==['c']
assert c.select_item({'o':obs(),'frame':10},m,p).buttons==['c'] # Opening was not registered: retry.
assert c.select_item({'o':obs(opened=True),'frame':20},m,p).buttons==['up']
m={}
assert c.select_item({'o':obs(selected=0,opened=True),'frame':0},m,p).buttons==['attack'] # Selected item still needs the open menu closed.
guard={'scenes':[770],'choose':True,'ids':[15],'reserves':{'15':1},'dx':800,'dy':180}
assert not c.item_ready({'o':obs(fire=1),'frame':20},guard)
assert c.item_ready({'o':obs(fire=2),'frame':20},guard)
guard['known_boss']=True
assert not c.item_ready({'o':obs(fire=2),'frame':20},guard)
c.boss_slots.add(0)
assert c.item_ready({'o':obs(fire=2),'frame':20},guard)
print('Item menu feedback, radial selection, and reserve: PASS')
