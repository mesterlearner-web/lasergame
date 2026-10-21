from ecs.component import Component


class Mirror(Component):
    """آینه به‌صورت یک پاره‌خط از (x1,y1) تا (x2,y2) تعریف می‌شود.
    Position جداگانه ندارد چون خودش دو نقطه است، نه یک نقطه.

    برای آینه‌ی چرخان (rotating): rotation_speed و pivot استفاده
    می‌شوند تا RotationSystem هر فریم x1,y1,x2,y2 را حول pivot
    بچرخاند (طبق تصمیم فایل مرجع، بخش ۵.۵)."""
    __slots__ = ('x1', 'y1', 'x2', 'y2', 'mirror_type', 'reflectivity',
                 'rotation_speed', 'pivot_x', 'pivot_y', 'base_angle')

    def __init__(self, x1, y1, x2, y2, mirror_type='normal',
                 reflectivity=1.0, rotation_speed=0.0,
                 pivot_x=None, pivot_y=None):
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
        self.mirror_type = mirror_type
        self.reflectivity = reflectivity
        self.rotation_speed = rotation_speed  # درجه بر ثانیه
        self.pivot_x = pivot_x if pivot_x is not None else (x1 + x2) / 2.0
        self.pivot_y = pivot_y if pivot_y is not None else (y1 + y2) / 2.0
        self.base_angle = 0.0  # زاویه‌ی تجمعی چرخش، برای محاسبه‌ی مجدد هر فریم
