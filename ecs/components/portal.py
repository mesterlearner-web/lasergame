from ecs.component import Component


class Portal(Component):
    __slots__ = ('radius', 'exit_x', 'exit_y', 'exit_angle')

    def __init__(self, radius=35.0, exit_x=0.0, exit_y=0.0, exit_angle=0.0):
        self.radius = radius
        self.exit_x = exit_x
        self.exit_y = exit_y
        self.exit_angle = exit_angle
