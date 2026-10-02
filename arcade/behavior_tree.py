"""Small synchronous behavior tree. One tick per game frame, one input owner."""
from dataclasses import dataclass

@dataclass
class Result:
    status: str
    buttons: list
    action: str = ''

class Node:
    def __init__(self, spec, conditions, actions):
        self.spec = spec
        self.kind = spec['type']
        if self.kind not in ('selector', 'sequence', 'condition', 'action'):
            raise ValueError(f'Unknown node type: {self.kind}')
        self.children = [Node(x, conditions, actions) for x in spec.get('children', [])]
        self.conditions, self.actions = conditions, actions
        self.memory = {}
        self.index = 0
        if self.kind == 'condition' and spec['name'] not in conditions:
            raise ValueError(f"Unknown condition: {spec['name']}")
        if self.kind == 'action' and spec['name'] not in actions:
            raise ValueError(f"Unknown action: {spec['name']}")

    def halt(self):
        self.index = 0
        self.memory.clear()
        for child in self.children:
            child.halt()

    def tick(self, context):
        params = self.spec.get('params', {})
        if self.kind == 'condition':
            return Result('SUCCESS' if self.conditions[self.spec['name']](context, params) else 'FAILURE', [])
        if self.kind == 'action':
            result = self.actions[self.spec['name']](context, self.memory, params)
            result.action = self.spec['name']
            if result.status not in ('SUCCESS', 'FAILURE', 'RUNNING'):
                raise ValueError(result.status)
            if result.status != 'RUNNING':
                self.memory.clear()
            return result
        if self.kind == 'selector':
            # Recheck higher priorities every frame; halt abandoned lower tasks.
            for i, child in enumerate(self.children):
                result = child.tick(context)
                if result.status != 'FAILURE':
                    for lower in self.children[i+1:]:
                        lower.halt()
                    return result
            return Result('FAILURE', [])
        # Memory sequence: don't restart a multi-frame action at every tick.
        while self.index < len(self.children):
            result = self.children[self.index].tick(context)
            if result.status == 'RUNNING':
                return result
            if result.status == 'FAILURE':
                self.halt()
                return result
            self.index += 1
        self.index = 0
        return result if self.children else Result('SUCCESS', [])
