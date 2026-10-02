"""Execution semantics: interrupted tasks restart; RUNNING tasks retain progress."""
from behavior_tree import Node,Result

def test():
    calls=[]
    def task(ctx,m,p):
        m['step']=m.get('step',0)+1;calls.append(m['step'])
        return Result('RUNNING',['attack'])
    spec={'type':'selector','children':[
        {'type':'sequence','children':[{'type':'condition','name':'danger'},{'type':'action','name':'avoid'}]},
        {'type':'action','name':'task'}]}
    tree=Node(spec,{'danger':lambda c,p:c['danger']},{'avoid':lambda c,m,p:Result('SUCCESS',['up']),'task':task})
    assert tree.tick({'danger':False}).buttons==['attack']
    assert tree.tick({'danger':False}).buttons==['attack']
    assert calls==[1,2]
    assert tree.tick({'danger':True}).buttons==['up']
    assert tree.tick({'danger':False}).buttons==['attack']
    assert calls==[1,2,1], 'Interrupted task must not retain obsolete progress'
    tree.halt();tree.tick({'danger':False});assert calls[-1]==1
    try:Node({'type':'action','name':'unknown'},{},{})
    except ValueError:pass
    else:raise AssertionError('Unknown action accepted')
    print('Behavior tree interruption, memory, halt and node validation: PASS')

if __name__=='__main__':test()
