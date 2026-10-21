"""
ecs/systems/movement_system.py

به‌روزرسانی موقعیت اهداف بر اساس move_pattern -- طبق اصلاح فایل مرجع
(بخش ۵.۴): همه‌ی الگوها واقعاً باید از target.speed استفاده کنند،
نه دامنه/دوره‌ی هاردکد که مستقل از سرعت جدول باشد (باگ اصلی سند اولیه).
"""
import math
import random

from ecs.system import System
from ecs.components.position import Position
from ecs.components.target import Target

AMPLITUDE = 200.0        # دامنه‌ی ثابت برای linear_horizontal/vertical (px)
CIRCULAR_RADIUS = 200.0  # شعاع ثابت مسیر دایره‌ای (px)
ZIGZAG_TRAVEL = 300.0    # طول کل رفت زیگزاگ (px)
RANDOM_CHANGE_INTERVAL = 1.5  # ثانیه -- هر چند وقت جهت تصادفی عوض شود
COMBINED_SWITCH_INTERVAL = 3.0  # ثانیه -- هر چند وقت الگوی ترکیبی سوییچ کند


class MovementSystem(System):
    #: طبق فایل مرجع: Timer=20 -> Physics/Movement=30 -> Raycast=40
    priority = 30
    required_components = (Position, Target)

    def update(self, dt, world):
        crosshair_x = getattr(world, 'crosshair_x', 0.0)
        crosshair_y = getattr(world, 'crosshair_y', 0.0)

        for entity in self.get_entities(world):
            pos = entity.get_component(Position)
            tgt = entity.get_component(Target)
            if not tgt.is_moving or tgt.speed <= 0:
                continue

            tgt.move_phase += dt
            pattern = tgt.move_pattern

            if pattern == 'linear_horizontal':
                self._linear(pos, tgt, axis='x')
            elif pattern == 'linear_vertical':
                self._linear(pos, tgt, axis='y')
            elif pattern == 'circular':
                self._circular(pos, tgt)
            elif pattern == 'zigzag':
                self._zigzag(pos, tgt)
            elif pattern == 'chase_crosshair':
                self._chase(pos, tgt, dt, crosshair_x, crosshair_y)
            elif pattern == 'random':
                self._random_move(pos, tgt, dt)
            elif pattern == 'combined':
                self._combined(pos, tgt)
            # 'static' هرگز به این‌جا نمی‌رسد چون is_moving=False است

    # ---------- الگوهای حرکتی ----------

    def _linear(self, pos, tgt, axis):
        angular_freq = tgt.speed / AMPLITUDE
        offset = AMPLITUDE * math.sin(tgt.move_phase * angular_freq)
        if axis == 'x':
            pos.x = tgt.origin_x + offset
        else:
            pos.y = tgt.origin_y + offset

    def _circular(self, pos, tgt):
        angular_velocity = tgt.speed / CIRCULAR_RADIUS
        angle = tgt.move_phase * angular_velocity
        pos.x = tgt.origin_x + math.cos(angle) * CIRCULAR_RADIUS
        pos.y = tgt.origin_y + math.sin(angle) * CIRCULAR_RADIUS

    def _zigzag(self, pos, tgt):
        period = (ZIGZAG_TRAVEL * 2.0) / tgt.speed
        half = period / 2.0
        t = tgt.move_phase % period
        if t < half:
            pos.x = tgt.origin_x + (t / half) * ZIGZAG_TRAVEL
        else:
            pos.x = tgt.origin_x + ZIGZAG_TRAVEL - ((t - half) / half) * ZIGZAG_TRAVEL

    def _chase(self, pos, tgt, dt, cx, cy):
        dx, dy = cx - pos.x, cy - pos.y
        dist = math.hypot(dx, dy)
        if dist > 1.0:
            pos.x += (dx / dist) * tgt.speed * dt
            pos.y += (dy / dist) * tgt.speed * dt

    def _random_move(self, pos, tgt, dt):
        tgt.random_timer -= dt
        if tgt.random_timer <= 0:
            angle = random.uniform(0, 2 * math.pi)
            tgt.random_dir_x, tgt.random_dir_y = math.cos(angle), math.sin(angle)
            tgt.random_timer = RANDOM_CHANGE_INTERVAL
        pos.x += tgt.random_dir_x * tgt.speed * dt
        pos.y += tgt.random_dir_y * tgt.speed * dt

    def _combined(self, pos, tgt):
        """الگوی ترکیبی -- شعاع مسیر دایره‌ای خودش به‌آرامی نوسان می‌کند
        (شبیه اسپیروگراف)، به‌جای سوییچ ناگهانی بین دو فرمول مجزا که
        باعث جهش موقعیتی می‌شد (این نسخه با تست عددی تنظیم و تأیید شده)."""
        angular_velocity = tgt.speed / CIRCULAR_RADIUS
        angle = tgt.move_phase * angular_velocity
        radius = CIRCULAR_RADIUS * (
            0.7 + 0.3 * math.sin(tgt.move_phase * angular_velocity * 0.12))
        pos.x = tgt.origin_x + math.cos(angle) * radius
        pos.y = tgt.origin_y + math.sin(angle) * radius
