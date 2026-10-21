from ecs.component import Component


class BlackHole(Component):
    __slots__ = ('radius', 'emit_x', 'emit_y')

    def __init__(self, radius=50.0, emit_x=0.0, emit_y=0.0):
        self.radius = radius
        self.emit_x = emit_x
        self.emit_y = emit_y
