"""
utils/particles.py  (فاز ۶)

لایه‌ی Juice -- ذرات، طبق تصمیم فایل مرجع بخش ۵.۷:
«ذرات: AdvancedParticleSystem بخش۵ (__slots__ + utils.pool.ObjectPool)
-- سبک‌ترین و بدون تکرار Entity-per-particle»
و
«_spawn_explosion در TargetManager باید particle_system.spawn_explosion
(...) رو صدا بزنه، نه Entity دستی بسازه.»

هر Particle یک شیء __slots__-دار ساده‌ست، نه یک Entity/Component کامل
ECS -- برای صدها ذره‌ی کوتاه‌عمر در هر انفجار، ثبت یک Entity کامل (با
تمام overhead ایندکس‌های World.entities/component_index که در فاز۱
برای Query سریع اضافه شدن) به‌ازای هرکدوم بیش‌ازحد سنگین بود. دقیقاً
به‌همین‌خاطر `utils/pool.py` (فاز۱) از همون ابتدا عمومی نوشته شده بود
("هم برای LaserBeam ... هم بعداً برای Particle") -- همینجا همون
پیش‌بینی استفاده می‌شه.

مستقل از Kivy -- فقط ریاضیات موقعیت/سرعت/عمر ذره؛ رسم واقعی (Ellipse
های Kivy) در ui/screens/game_screen.py انجام می‌شود (GameWidget هر
فریم get_active_particles() رو می‌خونه و می‌کشه).

اولویت در حلقه‌ی به‌روزرسانی: طبق بخش۵.۱ (اولویت سیستم‌ها، Particle=70)
-- یعنی *بعد* از Raycast/Collision (که مشخص می‌کنن چی منفجر شده) و
*قبل* از Audio/Render. GameWidget._update این ترتیب رو با فراخوانی
صریح particle_system.update(dt) در همون نقطه رعایت می‌کنه.
"""
import math
import random

from utils.pool import ObjectPool

DEFAULT_MAX_PARTICLES = 300
DEFAULT_SPAWN_COUNT = 16
DEFAULT_SPEED_RANGE = (80.0, 220.0)
DEFAULT_LIFE_RANGE = (0.35, 0.7)
DEFAULT_RADIUS_RANGE = (3.0, 7.0)
_DRAG_PER_SECOND = 2.0  # هرچه بزرگ‌تر، ذره سریع‌تر می‌ایسته (نه یک‌خط بی‌نهایت)


class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max_life', 'color', 'radius', 'active')

    def __init__(self):
        self.reset()

    def reset(self):
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.life = 0.0
        self.max_life = 1.0
        self.color = (1.0, 1.0, 1.0, 1.0)
        self.radius = 4.0
        self.active = False

    @property
    def life_fraction(self):
        """۱.۰ تازه‌متولد، ۰.۰ لحظه‌ی مرگ -- برای محو‌شدن تدریجی (alpha)
        در رسم."""
        return max(0.0, min(1.0, self.life / self.max_life)) if self.max_life > 0 else 0.0


def _reset_particle(p):
    p.reset()


class AdvancedParticleSystem:
    def __init__(self, max_particles=DEFAULT_MAX_PARTICLES):
        self.pool = ObjectPool(factory=Particle, reset_func=_reset_particle,
                                initial_size=40, max_size=max_particles)

    def spawn_explosion(self, x, y, color, count=DEFAULT_SPAWN_COUNT,
                         speed_range=DEFAULT_SPEED_RANGE, life_range=DEFAULT_LIFE_RANGE,
                         radius_range=DEFAULT_RADIUS_RANGE):
        """طبق بخش۵.۷ -- نقطه‌ی ورودی که به‌جای ساخت Entity دستی صدا
        زده می‌شه. برمی‌گردونه: لیست ذرات تازه‌ساخته‌شده (اختیاری برای
        فراخوان، خودِ update() مدیریت عمرشون رو انجام می‌ده)."""
        spawned = []
        for _ in range(count):
            p = self.pool.acquire()
            angle = random.uniform(0.0, 2.0 * math.pi)
            speed = random.uniform(*speed_range)
            p.x, p.y = x, y
            p.vx, p.vy = math.cos(angle) * speed, math.sin(angle) * speed
            p.max_life = random.uniform(*life_range)
            p.life = p.max_life
            p.color = color
            p.radius = random.uniform(*radius_range)
            p.active = True
            spawned.append(p)
        return spawned

    def update(self, dt):
        """حرکت + پیرشدن هر ذره‌ی فعال؛ ذره‌ای که عمرش تموم بشه به
        استخر برمی‌گرده (نه garbage collector -- دقیقاً هدف ObjectPool)."""
        for p in list(self.pool.active):
            if not p.active:
                continue
            p.life -= dt
            if p.life <= 0.0:
                p.active = False
                self.pool.release(p)
                continue
            p.x += p.vx * dt
            p.y += p.vy * dt
            drag = max(0.0, 1.0 - _DRAG_PER_SECOND * dt)
            p.vx *= drag
            p.vy *= drag

    def get_active_particles(self):
        return [p for p in self.pool.active if p.active]

    def clear(self):
        self.pool.release_all()
