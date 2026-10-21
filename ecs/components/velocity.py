from ecs.component import Component


class Velocity(Component):
    __slots__ = ('vx', 'vy')

    def __init__(self, vx=0.0, vy=0.0):
        self.vx = vx
        self.vy = vy
