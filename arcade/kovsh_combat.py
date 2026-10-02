"""Stateful real-button combat rules; observations are read-only."""
class Combat:
    def __init__(self,mode):
        self.mode=mode;self.slot=None;self.last_attack=-100;self.switch_at=0

    def tick(self,o,f):
        enemies=o['enemies']
        if not enemies or o['hp']==0:return []
        gy=o.get('ground_y',o['y'])
        def distance(x):return abs(x['x']-o['x'])+3*abs(x.get('ground_y',x['y'])-gy)
        target=next((x for x in enemies if x['slot']==self.slot),None)
        if target is None or (f-self.switch_at>=120 and distance(target)>160):
            viable=[x for x in enemies if x.get('height',0)>=-8] if self.mode=='ground_finisher' else enemies
            target=min(viable or enemies,key=distance)
            self.slot=target['slot'];self.switch_at=f
        dx=target['x']-o['x'];dy=target.get('ground_y',target['y'])-gy
        face='right' if dx>=0 else 'left'
        attacking=o.get('actor_code',0) in (1,2)
        if attacking and self.mode in ('locked_combo','edge_combo','ground_finisher'):
            # Preserve strike direction during these empirically observed codes.
            # Exact animation names have not been decoded.
            if self.mode=='edge_combo':return []
            return ['attack'] if f%4<2 else []
        keys=[]
        if abs(dy)>6:keys.append('down' if dy>0 else 'up')
        if abs(dx)>40 or o.get('facing')!=face:keys.append(face)
        ready=abs(dx)<=65 and abs(dy)<=10 and (target.get('height',0)>=-8 or self.mode!='ground_finisher')
        if ready:
            if self.mode=='hold_attack':keys.append('attack')
            elif self.mode=='edge_combo':
                if f-self.last_attack>=4:
                    keys.append('attack');self.last_attack=f
            elif f%4<2:keys.append('attack')
        return keys

MODES=('aligned_pulse','locked_combo','edge_combo','hold_attack','ground_finisher')
