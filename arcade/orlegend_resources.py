"""Calibrated inventory reads and bounded, feedback-checked ordinary item inputs."""
def resources(r):
 count=min(8,r[0x1119d])
 return {'inventory':[{'count':r[0x1118a+i*2],'id':r[0x1118b+i*2]} for i in range(count)],'selected':r[0x1119c],'meter':r[0x1bf4d],'menu_open':r[0x11125]==2}

class Items:
 def __init__(self):self.queue=[];self.pending=None;self.cooldown=0;self.events=[]
 def choose(self,o,res,f,c):
  inv=res['inventory']
  if self.pending:
   ident,before,deadline=self.pending;count=sum(x['count'] for x in inv if x['id']==ident)
   if count<before:
    self.events.append({'frame':f,'status':'consumed_confirmed','id':ident,'before':before,'after':count});self.pending=None;self.queue=[];self.cooldown=f+150
   elif f>=deadline:
    self.events.append({'frame':f,'status':'not_consumed','id':ident});self.pending=None;self.queue=[];self.cooldown=f+60
   else:return ['d'] if f%4<2 else []
  if self.queue:return self.queue.pop(0)
  if f<self.cooldown:return None
  if o['stage_raw']<c.get('items_from_scene',3):return None
  near=[e for e in o['enemies'] if abs(e['x']-o['x'])<220 and abs(e['y']-o['y'])<80]
  boss=any(e['hp']>=100 for e in near);crowd=len(near)>=c.get('item_crowd',3)
  if not near or not(boss or crowd):return None
  choices=[(i,x) for i,x in enumerate(inv) if x['count']>0 and (x['id']!=15 or crowd and x['count']>c.get('reserve_element',1))]
  if not choices:return None
  i,item=min(choices,key=lambda z:([9,7,5,6,8,15].index(z[1]['id']) if z[1]['id'] in [9,7,5,6,8,15] else 99))
  ident=item['id'];current=res['selected'];turns=(i-current)%len(inv)
  keys=[['c']]*2+[[]]*6
  for _ in range(turns):keys += [['left']]*2+[[]]*6
  keys += [['attack']]*2+[[]]*12
  self.queue=keys;self.pending_start=(ident,sum(x['count'] for x in inv if x['id']==ident))
  self.events.append({'frame':f,'status':'select','index':i,'id':ident,'selected_before':current})
  return self.queue.pop(0)

 def act(self,o,res,f,c):
  # Complete selection before attempting use; only the inventory decrease confirms use.
  if self.queue:
   keys=self.queue.pop(0)
   if not self.queue:self.pending=(*self.pending_start,f+45)
   return keys
  return self.choose(o,res,f,c)
