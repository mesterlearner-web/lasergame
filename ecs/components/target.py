from ecs.component import Component


class Target(Component):
    __slots__ = ('hp', 'max_hp', 'move_pattern', 'speed', 'is_moving',
                 'move_phase', 'origin_x', 'origin_y', 'radius',
                 'random_dir_x', 'random_dir_y', 'random_timer')

    def __init__(self, hp=1, max_hp=1, move_pattern='static', speed=0.0,
                 origin_x=0.0, origin_y=0.0, radius=40.0):
        self.hp = hp
        self.max_hp = max_hp
        self.move_pattern = move_pattern
        self.speed = speed
        self.is_moving = (move_pattern != 'static')
        self.move_phase = 0.0
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.radius = radius
        # برای الگوی 'random' -- طبق تصمیم فایل مرجع بخش ۵.۴
        self.random_dir_x = 1.0
        self.random_dir_y = 0.0
        self.random_timer = 0.0
