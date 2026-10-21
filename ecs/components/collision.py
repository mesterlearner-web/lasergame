from ecs.component import Component


class Collision(Component):
    __slots__ = ('shape', 'radius', 'layer', 'mask')

    def __init__(self, shape='circle', radius=20.0, layer='default', mask=None):
        self.shape = shape
        self.radius = radius
        self.layer = layer
        self.mask = mask or []
