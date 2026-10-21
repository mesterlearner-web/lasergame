"""
game_logic/raycast.py

موتور Raycasting -- محاسبه‌ی مسیر کامل پرتو لیزر با بازتاب، تجزیه
(منشور)، انتقال (پورتال)، و جذب/انتشار (سیاه‌چاله).

این نسخه‌ی پایتون خالص است. طبق فایل مرجع (بخش ۳ نقشه‌راه)، در فاز
بعدی یک نسخه‌ی Cython از همین منطق برای کارایی بیشتر نوشته می‌شود --
بدون تغییر در رفتار یا امضای توابع، فقط سرعت.

--- دو باگِ نسخه‌ی اولیه‌ی سند که اینجا از پایه اصلاح شده‌اند ---
۱. حلقه‌ی بی‌نهایت روی برخورد با انواع 'prism'/'portal'/... (چون آن
   نسخه فقط 'mirror'/'semi_mirror'/'obstacle'/'target' را می‌شناخت).
۲. هدف‌ها (و پورتال/منشور/سیاه‌چاله) در واقعیت یک *دایره* هستند
   (x, y, radius)، نه یک پاره‌خط (x1,y1,x2,y2) مثل آینه/مانع؛ نسخه‌ی
   اولیه‌ی سند همه‌ی سطوح را با فرمول پاره‌خط پردازش می‌کرد که برای
   هدف حتی از نظر داده هم بی‌معنی بود (KeyError). این نسخه دو نوع
   هندسه را جدا و صحیح مدیریت می‌کند.

هر عنصر صحنه (surface) یک دیکشنری با کلید 'shape' است:
  - 'segment': نیازمند x1, y1, x2, y2   (آینه، مانع)
  - 'circle' : نیازمند x, y, radius     (هدف، پورتال، منشور، سیاه‌چاله)
و کلید 'type' که نوع برخورد را مشخص می‌کند:
  'mirror' | 'semi_mirror' | 'rotating_mirror' | 'broken_mirror' |
  'obstacle' | 'target' | 'prism' | 'portal' | 'black_hole'
"""

import math
import random

EPSILON = 1e-6
MAX_RAY_LENGTH = 5000.0
DEFAULT_MAX_BOUNCES = 10

# انواع سطحی که پرتو را کاملاً بازتاب می‌دهند (بدون شکافتن به دو پرتو).
# rotating_mirror هم اینجاست چون خودِ raycaster فرقی با mirror عادی
# ندارد -- چرخش را یک System جدا (RotationSystem) با تغییر x1,y1,x2,y2
# قبل از هر فریم اعمال می‌کند.
_FULL_REFLECT_TYPES = ('normal', 'rotating_mirror')

# مقدار پراکندگی زاویه‌ای آینه‌ی شکسته (درجه) -- تفسیر بخش «۰.۷ بازتاب
# + ۰.۳ پراکندگی» فایل مرجع بخش۲: به‌جای بازتاب دقیق، یک خطای زاویه‌ای
# تصادفی به مسیر خروجی اضافه می‌شود.
_BROKEN_MIRROR_SCATTER_DEG = 12.0


class LaserBeam:
    """مسیر کامل یک پرتو (یا یکی از پرتوهای فرزند، مثلاً بعد از منشور)."""

    __slots__ = ('points', 'hit_types', 'hit_ids', 'bounces', 'total_length')

    def __init__(self):
        self.points = []
        self.hit_types = []
        self.hit_ids = []
        self.bounces = 0
        self.total_length = 0.0

    def reset(self):
        """برای استفاده‌ی مجدد در BeamPool."""
        self.points.clear()
        self.hit_types.clear()
        self.hit_ids.clear()
        self.bounces = 0
        self.total_length = 0.0


def _normalize(dx, dy):
    length = math.hypot(dx, dy)
    if length < EPSILON:
        return 0.0, 0.0
    return dx / length, dy / length


def _reflect(dx, dy, nx, ny):
    """R = D - 2(D.N)N -- مستقل از علامت بردار نرمال (به‌صورت عددی
    وریفای شده که با N یا -N جواب یکسان می‌دهد)."""
    dot = dx * nx + dy * ny
    rx = dx - 2 * dot * nx
    ry = dy - 2 * dot * ny
    return _normalize(rx, ry)


def _segment_normal(x1, y1, x2, y2):
    mx, my = x2 - x1, y2 - y1
    length = math.hypot(mx, my)
    if length < EPSILON:
        return 0.0, 1.0
    mx, my = mx / length, my / length
    return -my, mx


def _ray_segment_intersect(rx, ry, rdx, rdy, sx1, sy1, sx2, sy2):
    """فاصله‌ی t تا برخورد پرتو با پاره‌خط، یا None اگر برخوردی نباشد."""
    sdx, sdy = sx2 - sx1, sy2 - sy1
    denom = rdx * sdy - rdy * sdx
    if abs(denom) < EPSILON:
        return None  # موازی
    dx, dy = sx1 - rx, sy1 - ry
    t = (dx * sdy - dy * sdx) / denom
    u = (dx * rdy - dy * rdx) / denom
    if t > EPSILON and 0.0 <= u <= 1.0:
        return t
    return None


def _ray_circle_intersect(rx, ry, rdx, rdy, cx, cy, radius):
    """فاصله‌ی t تا اولین برخورد پرتو با دایره، یا None اگر برخوردی نباشد."""
    lx, ly = cx - rx, cy - ry
    tca = lx * rdx + ly * rdy
    d2 = (lx * lx + ly * ly) - tca * tca
    r2 = radius * radius
    if d2 > r2:
        return None
    thc = math.sqrt(max(0.0, r2 - d2))
    t0, t1 = tca - thc, tca + thc
    if t0 > EPSILON:
        return t0
    if t1 > EPSILON:
        return t1  # پرتو از داخل دایره شروع شده
    return None


def _find_closest_hit(cx, cy, dx, dy, surfaces):
    """نزدیک‌ترین surface که پرتو با آن برخورد می‌کند، یا None."""
    closest_t = float('inf')
    closest = None
    for surface in surfaces:
        shape = surface.get('shape')
        if shape == 'segment':
            t = _ray_segment_intersect(cx, cy, dx, dy,
                                        surface['x1'], surface['y1'],
                                        surface['x2'], surface['y2'])
        elif shape == 'circle':
            t = _ray_circle_intersect(cx, cy, dx, dy,
                                       surface['x'], surface['y'],
                                       surface['radius'])
        else:
            continue
        if t is not None and t < closest_t:
            closest_t = t
            closest = surface
    if closest is None:
        return None
    hx, hy = cx + dx * closest_t, cy + dy * closest_t
    if closest['shape'] == 'segment':
        nx, ny = _segment_normal(closest['x1'], closest['y1'],
                                  closest['x2'], closest['y2'])
    else:
        nx, ny = _normalize(hx - closest['x'], hy - closest['y'])
    return hx, hy, closest, nx, ny


def cast(start_x, start_y, dir_x, dir_y, surfaces,
         max_bounces=DEFAULT_MAX_BOUNCES, shot_effects=None, _budget=None):
    """محاسبه‌ی کامل مسیر پرتو (یا چند پرتو، اگر با منشور تجزیه شود).

    برمی‌گرداند: list[LaserBeam]  -- معمولاً یک عضو، مگر پرتو با
    منشور برخورد کند که آنگاه یک بیم برای بخش قبل از منشور + چند
    بیم فرزند (یکی به ازای هر رنگ) برمی‌گردد.
    """
    shot_effects = shot_effects or []
    pierce_remaining = 3 if 'pierce_obstacles' in shot_effects else 0
    remaining_budget = max_bounces if _budget is None else _budget

    beams = []
    beam = LaserBeam()
    beam.points.append((start_x, start_y))
    beam.hit_types.append('start')

    cx, cy = start_x, start_y
    dx, dy = _normalize(dir_x, dir_y)
    bounce_count = 0

    while bounce_count < remaining_budget:
        result = _find_closest_hit(cx, cy, dx, dy, surfaces)

        if result is None:
            ex, ey = cx + dx * MAX_RAY_LENGTH, cy + dy * MAX_RAY_LENGTH
            beam.points.append((ex, ey))
            beam.hit_types.append('none')
            break

        hx, hy, surf, nx, ny = result
        hit_type = surf.get('type', 'obstacle')

        beam.points.append((hx, hy))
        beam.hit_types.append(hit_type)
        beam.hit_ids.append(surf.get('id'))
        beam.total_length += math.hypot(hx - cx, hy - cy)

        if hit_type == 'target':
            beam.bounces = bounce_count
            beams.append(beam)
            return beams

        elif hit_type == 'obstacle':
            if pierce_remaining > 0:
                pierce_remaining -= 1
                cx, cy = hx, hy
                bounce_count += 1
                continue
            break

        elif hit_type in _FULL_REFLECT_TYPES:
            dx, dy = _reflect(dx, dy, nx, ny)
            cx, cy = hx, hy
            bounce_count += 1
            if 'split_on_bounce' in shot_effects:
                offset = math.radians(15)
                sdx = dx * math.cos(offset) - dy * math.sin(offset)
                sdy = dx * math.sin(offset) + dy * math.cos(offset)
                remaining_surfaces = [s for s in surfaces if s is not surf]
                beams.extend(cast(hx, hy, sdx, sdy, remaining_surfaces, max_bounces,
                                   shot_effects=[],
                                   _budget=remaining_budget - bounce_count))

        elif hit_type == 'broken_mirror':
            # بازتاب با یک خطای زاویه‌ای تصادفی (پراکندگی) به‌جای بازتاب دقیق
            rdx, rdy = _reflect(dx, dy, nx, ny)
            scatter = math.radians(random.uniform(-_BROKEN_MIRROR_SCATTER_DEG,
                                                    _BROKEN_MIRROR_SCATTER_DEG))
            dx = rdx * math.cos(scatter) - rdy * math.sin(scatter)
            dy = rdx * math.sin(scatter) + rdy * math.cos(scatter)
            cx, cy = hx, hy
            bounce_count += 1

        elif hit_type == 'semi_mirror':
            # پرتو به دو پرتوی فرزند تقسیم می‌شود: یکی بازتاب‌یافته، یکی
            # مستقیم عبورکرده (transmit) -- دقیقاً همان چیزی که الگوی
            # طراحی «چند مسیر» سند اصلی (بخش۳، الگوی ۶) توصیف می‌کند.
            beam.bounces = bounce_count
            beams.append(beam)
            remaining_surfaces = [s for s in surfaces if s is not surf]
            budget = remaining_budget - bounce_count - 1

            rdx, rdy = _reflect(dx, dy, nx, ny)
            beams.extend(cast(hx, hy, rdx, rdy, remaining_surfaces, max_bounces,
                               shot_effects, _budget=budget))
            beams.extend(cast(hx, hy, dx, dy, remaining_surfaces, max_bounces,
                               shot_effects, _budget=budget))
            return beams

        elif hit_type == 'prism':
            beam.bounces = bounce_count
            beams.append(beam)
            base_angle = math.atan2(dy, dx)
            colors_count = 6
            spread = math.radians(30)
            # همین منشوری که تازه برخورد کرد را از صحنه‌ی زیرشاخه‌ها حذف کن --
            # وگرنه پرتوهای فرزند که از نزدیکی لبه‌ی همین دایره شروع می‌شوند
            # می‌توانند دوباره با همان دایره برخورد کنند و رشد نمایی بسازند
            # (این باگ با تست واقعی پیدا و اینجا اصلاح شد).
            remaining_surfaces = [s for s in surfaces if s is not surf]
            for i in range(colors_count):
                offset = (i - (colors_count - 1) / 2.0) * (spread / colors_count)
                angle = base_angle + offset
                sub = cast(hx, hy, math.cos(angle), math.sin(angle), remaining_surfaces,
                           max_bounces, shot_effects,
                           _budget=remaining_budget - bounce_count - 1)
                beams.extend(sub)
            return beams

        elif hit_type == 'portal':
            cx, cy = surf.get('exit_x', hx), surf.get('exit_y', hy)
            exit_angle = surf.get('exit_angle', 0.0)
            rad = math.radians(exit_angle)
            dx, dy = math.cos(rad), math.sin(rad)
            bounce_count += 1

        elif hit_type == 'black_hole':
            cx, cy = surf.get('emit_x', hx), surf.get('emit_y', hy)
            rad = random.uniform(0, 2 * math.pi)
            dx, dy = math.cos(rad), math.sin(rad)
            bounce_count += 1

        else:
            # نوع ناشناخته -- به‌جای حلقه‌ی بی‌نهایت، پرتو را متوقف کن
            break

    beam.bounces = bounce_count
    beams.append(beam)
    return beams
