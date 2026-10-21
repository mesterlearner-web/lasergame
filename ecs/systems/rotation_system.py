"""
ecs/systems/rotation_system.py

به‌روزرسانی موقعیت آینه‌های چرخان -- طبق تصمیم فایل مرجع (بخش ۵.۵):
خودِ موتور Raycasting فرقی بین 'rotating_mirror' و 'normal' نمی‌گذارد؛
این سیستم مسئول چرخاندن واقعی x1,y1,x2,y2 حول pivot است، قبل از اینکه
scene_builder آن را به raycast.cast() بدهد.
"""
import math

from ecs.system import System
from ecs.components.mirror import Mirror


class RotationSystem(System):
    #: قبل از Movement(30) نباید باشد چون به هندسه‌ی نهایی این فریم نیاز
    #: نداریم که با movement تداخل کند؛ قبل از Raycast(40) کافی است
    priority = 35
    required_components = (Mirror,)

    def update(self, dt, world):
        for entity in self.get_entities(world):
            m = entity.get_component(Mirror)
            if m.mirror_type != 'rotating_mirror' or m.rotation_speed == 0.0:
                continue

            m.base_angle = (m.base_angle + m.rotation_speed * dt) % 360.0
            rad = math.radians(m.base_angle)

            # طول اصلی آینه از فاصله‌ی نقطه‌ی شروع تا pivot محاسبه می‌شود
            # (فرض: pivot وسط آینه است، طول ثابت می‌ماند، فقط می‌چرخد)
            half_len = math.hypot(m.x2 - m.x1, m.y2 - m.y1) / 2.0
            dx, dy = math.cos(rad) * half_len, math.sin(rad) * half_len

            m.x1, m.y1 = m.pivot_x - dx, m.pivot_y - dy
            m.x2, m.y2 = m.pivot_x + dx, m.pivot_y + dy
