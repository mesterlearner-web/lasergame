from ecs.component import Component


class Obstacle(Component):
    __slots__ = ('x1', 'y1', 'x2', 'y2', 'destructible', 'hp')

    def __init__(self, x1, y1, x2, y2, destructible=False, hp=999):
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
        self.destructible = destructible
        self.hp = hp
