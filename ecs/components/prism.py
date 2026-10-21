from ecs.component import Component


class Prism(Component):
    __slots__ = ('radius',)

    def __init__(self, radius=30.0):
        self.radius = radius
