"""
game_logic/level.py

بارگذاری یک مرحله از دیکشنری (که از JSON خوانده شده) و ساخت Entity
های ECS متناظر با آن. طبق تصمیم فایل مرجع، سیستم مختصات همان مختصات
بومی Kivy است (Y رو به بالا) -- یعنی هدفی که باید «بالاتر» دیده بشود
باید y بزرگ‌تر از اسلحه داشته باشد.
"""
from ecs.components.position import Position
from ecs.components.mirror import Mirror
from ecs.components.obstacle import Obstacle
from ecs.components.target import Target
from ecs.components.portal import Portal
from ecs.components.prism import Prism
from ecs.components.black_hole import BlackHole


class Level:
    def __init__(self, data):
        self.level_id = data.get('level_id', 0)
        self.phase = data.get('phase', 'training')
        self.difficulty = data.get('difficulty', 1.0)
        self.time_limit = data.get('time_limit', 300)

        self.targets = data.get('targets', [])
        self.mirrors = data.get('mirrors', [])
        self.obstacles = data.get('obstacles', [])
        self.portals = data.get('portals', [])
        self.prisms = data.get('prisms', [])
        self.black_holes = data.get('black_holes', [])

        self.laser_start = data.get('laser_start', {'x': 540, 'y': 180, 'angle': 90})
        self.rewards = data.get('rewards', {})
        self.hints = data.get('hints', [])

    @classmethod
    def from_json_file(cls, path):
        import json
        with open(path, 'r', encoding='utf-8') as f:
            return cls(json.load(f))

    def populate_world(self, world):
        """همه‌ی Entity های این مرحله را در world می‌سازد.
        برمی‌گرداند: (gun_x, gun_y) برای موقعیت شروع اسلحه."""

        for t in self.targets:
            e = world.create_entity()
            world.add_component(e, Position, x=t['x'], y=t['y'])
            world.add_component(
                e, Target,
                hp=t.get('hp', 1), max_hp=t.get('hp', 1),
                move_pattern=t.get('move_pattern', 'static'),
                speed=t.get('speed', 0.0),
                origin_x=t['x'], origin_y=t['y'],
                radius=t.get('radius', 40.0),
            )

        for m in self.mirrors:
            e = world.create_entity()
            world.add_component(
                e, Mirror,
                x1=m['x1'], y1=m['y1'], x2=m['x2'], y2=m['y2'],
                mirror_type=m.get('type', 'normal'),
                reflectivity=m.get('reflectivity', 1.0),
                rotation_speed=m.get('rotation_speed', 0.0),
                pivot_x=m.get('pivot_x'), pivot_y=m.get('pivot_y'),
            )

        for o in self.obstacles:
            e = world.create_entity()
            world.add_component(
                e, Obstacle,
                x1=o['x1'], y1=o['y1'], x2=o['x2'], y2=o['y2'],
                destructible=o.get('destructible', False),
                hp=o.get('hp', 999),
            )

        for p in self.portals:
            e = world.create_entity()
            world.add_component(e, Position, x=p['x'], y=p['y'])
            world.add_component(
                e, Portal, radius=p.get('radius', 35.0),
                exit_x=p['exit_x'], exit_y=p['exit_y'],
                exit_angle=p.get('exit_angle', 0.0),
            )

        for pr in self.prisms:
            e = world.create_entity()
            world.add_component(e, Position, x=pr['x'], y=pr['y'])
            world.add_component(e, Prism, radius=pr.get('radius', 30.0))

        for bh in self.black_holes:
            e = world.create_entity()
            world.add_component(e, Position, x=bh['x'], y=bh['y'])
            world.add_component(
                e, BlackHole, radius=bh.get('radius', 50.0),
                emit_x=bh.get('emit_x', bh['x']), emit_y=bh.get('emit_y', bh['y']),
            )

        return self.laser_start['x'], self.laser_start['y']
