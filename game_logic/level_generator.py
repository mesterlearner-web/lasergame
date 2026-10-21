"""
game_logic/level_generator.py  (فاز ۹)

مولد رویه‌ای مراحل -- پایه‌ی مراحل ۶ تا ۱۰۰ کمپین، حالت بی‌نهایت و چالش روزانه.
طبق فایل مرجع بخش ۵.۹: «_is_solvable باید واقعاً از RaycastEngine استفاده کند ... حداکثر ۲۰ بار
تلاش، بعدش کمی سختی را کم کن تا مرحله‌ی حل‌پذیر تضمین شود.»

طراحی: *سازنده* (constructive)، نه «بچین و امیدوار باش»
------------------------------------------------------
برای هر هدف اول یک «مسیر حل» واقعی ساخته می‌شود -- اسلحه -> آینه‌ی ۱ -> ... -> هدف -- جهت هر
آینه از قانون بازتاب محاسبه می‌شود (n ∥ d_out − d_in). بعد آینه‌ها/موانع انحرافی اضافه می‌شوند
(دور از مسیرهای حل) و در پایان خودِ موتور Raycasting واقعی *همان راه‌حل را بازپخش* می‌کند و باید
واقعاً به هدف بخورد، با حاشیه‌ی زاویه‌ی کافی (بازیکن با انگشت هدف می‌گیرد). این هم تضمین
حل‌پذیری می‌دهد و هم ارزان است (به‌جای جاروی ۳۶۰ درجه‌ای برای هر تلاش)، که برای تولید روی
گوشی مهم است.

اثبات «قطعی»: سیاه‌چاله و آینه‌ی شکسته از random سراسری استفاده می‌کنند، پس فقط *تزئینی/مانع*اند و
در اثبات مثل مانع حساب می‌شوند (راه‌حل هرگز از آن‌ها رد نمی‌شود)؛ الگوهای حرکت `random` و
`chase_crosshair` (وابسته به لمس بازیکن) در مراحل تولیدی استفاده نمی‌شوند.

تکرارپذیری (برای چالش روزانه که روی هر گوشی جداگانه تولید می‌شود): فقط random.Random(seed).random()
استفاده می‌شود -- تنها بخشی از ماژول random که پایتون پایداری‌اش را بین نسخه‌ها تضمین می‌کند
(randint/choice/shuffle تضمین ندارند). مختصات به یک رقم اعشار گرد می‌شوند.
"""
import math
import random

from ecs.components.position import Position
from ecs.components.target import Target
from ecs.systems.movement_system import MovementSystem
from ecs.systems.rotation_system import RotationSystem
from ecs.world import World
from game_logic.difficulty_manager import MECHANIC_UNLOCK_LEVEL, TOTAL_LEVELS, DifficultyManager
from game_logic.level import Level
from game_logic.level_validator import _aim_hits_target, deterministic_surfaces
from game_logic.scene_builder import entities_to_surfaces

# ------------------------------------------------------------------ ثابت‌ها
GUN_X, GUN_Y = 540.0, 180.0
X_MIN, X_MAX = 110.0, 970.0
Y_MIN, Y_MAX = 430.0, 1620.0          # زیر ۴۳۰: ناحیه‌ی اسلحه؛ بالای ۱۶۲۰: زیر HUD
TARGET_RADIUS = 40.0
CLEAR = 20.0                          # حداقل فاصله‌ی اجسام از مسیر حل و از هم (داور نهایی: پنجره‌ی ±δ در verify_solutions)
LEG_MIN, LEG_MAX = 250.0, 560.0       # طول هر پاره‌ی مسیر حل
MAX_ATTEMPTS = 20                     # طبق فایل مرجع ۵.۹
MAX_REDUCTIONS = 3                    # بعد از ۲۰ شکست، سختی کم می‌شود (۳ بار)
#: ⚠️ نام نوع آینه‌ی ساده در موتور 'normal' است (raycast._FULL_REFLECT_TYPES)، نه 'mirror'. نسخه‌ی اول
#: مولد 'mirror' می‌نوشت؛ موتور برای نوع ناشناخته پرتو را متوقف می‌کند، پس هر پرتو در اولین آینه
#: می‌مرد و تقریباً هیچ نامزدی تأیید نمی‌شد (که اشتباهاً «میدان شلوغ است» تعبیر شد).
PLAIN_MIRROR = 'normal'
FIRE_TIME = 1.0                       # زمان واقع‌بینانه‌ی شلیک (ثانیه) -- نه «لحظه‌ی صفر»
PATTERN_SPEED = {'linear_horizontal': 100.0, 'linear_vertical': 100.0,
                 'circular': 150.0, 'zigzag': 120.0, 'combined': 200.0}   # جدول بخش ۵.۴
ROTATION_SPEEDS = (15.0, 20.0, 25.0)  # درجه بر ثانیه
MIN_TIME_WINDOW = 0.06                # نیم‌پنجره‌ی زمانیِ شلیک برای آینه‌ی چرخان (ثانیه)
SIM_STEP = 1.0 / 30.0


#: فقط برای عیب‌یابی/تست: دلیل رد شدن هر تلاش (کم‌هزینه). با info['fail_reasons'] هم برمی‌گردد.
FAIL_COUNTS = {}


def _fail(reason):
    FAIL_COUNTS[reason] = FAIL_COUNTS.get(reason, 0) + 1
    return None


class SeededRng:
    """فقط از random() استفاده می‌کند (تنها تابع تضمین‌شده‌ی پایدار بین نسخه‌های پایتون)."""

    def __init__(self, seed):
        self._r = random.Random(int(seed))

    def random(self):
        return self._r.random()

    def uniform(self, a, b):
        return a + (b - a) * self.random()

    def randint(self, a, b):
        return a + int(self.random() * (b - a + 1))

    def chance(self, p):
        return self.random() < p

    def choice(self, seq):
        return seq[int(self.random() * len(seq))]

    def sign(self):
        return 1.0 if self.random() < 0.5 else -1.0


# ------------------------------------------------------------------ هندسه
def _dist_pt_seg(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    length2 = dx * dx + dy * dy
    if length2 == 0.0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def _ccw(ax, ay, bx, by, cx, cy):
    return (cy - ay) * (bx - ax) - (by - ay) * (cx - ax)


def _segments_intersect(a, b):
    d1 = _ccw(*a[:2], *a[2:], *b[:2])
    d2 = _ccw(*a[:2], *a[2:], *b[2:])
    d3 = _ccw(*b[:2], *b[2:], *a[:2])
    d4 = _ccw(*b[:2], *b[2:], *a[2:])
    return d1 * d2 < 0 and d3 * d4 < 0


def _dist_seg_seg(a, b):
    if _segments_intersect(a, b):
        return 0.0
    return min(_dist_pt_seg(a[0], a[1], *b), _dist_pt_seg(a[2], a[3], *b),
               _dist_pt_seg(b[0], b[1], *a), _dist_pt_seg(b[2], b[3], *a))


def _inside(x, y, margin=0.0):
    return X_MIN + margin <= x <= X_MAX - margin and Y_MIN + margin <= y <= Y_MAX - margin


def _rotate(dx, dy, degrees):
    r = math.radians(degrees)
    return dx * math.cos(r) - dy * math.sin(r), dx * math.sin(r) + dy * math.cos(r)


class _Geo:
    """جای اجسام هنگام ساخت: solid=آینه/مانع (پاره‌خط)، disc=دایره، leg=پاره‌ی مسیر حل."""

    def __init__(self):
        self.solids, self.discs, self.legs, self.sweeps = [], [], [], []
        self._next = 0

    def copy(self):
        g = _Geo()
        g.solids, g.discs = list(self.solids), list(self.discs)
        g.legs, g.sweeps = list(self.legs), list(self.sweeps)
        g._next = self._next
        return g

    def add_sweep(self, points, path):
        """مسیر واقعی حرکت یک هدف متحرک (چندخط) -- نه یک دیسک پُر: هدف خطی فقط یک نوار باریک و
        هدف دایره‌ای فقط یک حلقه را می‌پیماید. مدل دیسکی ۲۱ تا ۴۰ درصد کل میدان را برای هر
        هدف متحرک ممنوع می‌کرد و مراحل خبره/استاد همه به fallback می‌رسیدند."""
        segs = [(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])
                for i in range(len(points) - 1)]
        self.sweeps.append({'segs': segs, 'path': path})

    def new_id(self):
        self._next += 1
        return self._next

    def add_solid(self, seg, kind, path=None):
        oid = self.new_id()
        self.solids.append({'oid': oid, 'seg': seg, 'kind': kind, 'path': path})
        return oid

    def add_disc(self, x, y, r, kind, blocks_legs=True, path=None, owner=None):
        oid = self.new_id()
        self.discs.append({'oid': oid, 'x': x, 'y': y, 'r': r, 'kind': kind,
                           'blocks_legs': blocks_legs, 'path': path, 'owner': owner})
        return oid

    def add_leg(self, seg, skip):
        self.legs.append({'seg': seg, 'skip': set(skip)})

    def mark(self):
        """نشانه‌ی «تا اینجا سازگار بود»: ok(mark) فقط جفت‌هایی را بررسی می‌کند که حداقل یک جسم
        *جدید* دارند. بررسی کامل هر قدم (O(N²)) مراحل استاد را ≈۰.۹ ثانیه می‌کرد."""
        return len(self.solids), len(self.discs), len(self.legs), len(self.sweeps)

    def ok(self, since=(0, 0, 0, 0)):
        ns, nd, nl, nw = since
        solids, discs, legs, sweeps = self.solids, self.discs, self.legs, self.sweeps
        for li, leg in enumerate(legs):
            new_leg = li >= nl
            skip = leg['skip']
            for si, s in enumerate(solids):
                if (new_leg or si >= ns) and s['oid'] not in skip \
                        and _dist_seg_seg(leg['seg'], s['seg']) < CLEAR:
                    return False
            for di, d in enumerate(discs):
                if (new_leg or di >= nd) and d['blocks_legs'] and d['oid'] not in skip \
                        and _dist_pt_seg(d['x'], d['y'], *leg['seg']) < d['r'] + CLEAR:
                    return False
        for i in range(ns, len(solids)):
            a = solids[i]
            for j in range(i):
                if _dist_seg_seg(a['seg'], solids[j]['seg']) < CLEAR:
                    return False
        for i, a in enumerate(solids):
            for j, d in enumerate(discs):
                if i < ns and j < nd:
                    continue
                if d['kind'] == 'origin' and d['path'] is not None and d['path'] == a['path']:
                    continue
                if d['owner'] != a['oid'] and _dist_pt_seg(d['x'], d['y'], *a['seg']) < d['r'] + CLEAR:
                    return False
        margin = TARGET_RADIUS + 10.0
        for wi, sweep in enumerate(sweeps):
            new_sweep = wi >= nw
            for si, s in enumerate(solids):
                if (new_sweep or si >= ns) and s['path'] != sweep['path'] and any(
                        _dist_seg_seg(seg, s['seg']) < margin for seg in sweep['segs']):
                    return False
            for di, d in enumerate(discs):
                if (new_sweep or di >= nd) and d['path'] != sweep['path'] and any(
                        _dist_pt_seg(d['x'], d['y'], *seg) < d['r'] + margin for seg in sweep['segs']):
                    return False
        for j in range(nd, len(discs)):
            b = discs[j]
            for i in range(j):
                a = discs[i]
                if math.hypot(a['x'] - b['x'], a['y'] - b['y']) < a['r'] + b['r'] + CLEAR:
                    return False
        return True


# ------------------------------------------------------------------ دنیا / الگوهای حرکت
def _advance(world, seconds):
    """زمان را با گام‌های کوچک جلو می‌برد (مثل حلقه‌ی واقعی بازی، نه یک جهش بزرگ)."""
    if seconds <= 0:
        return
    steps = max(1, int(round(seconds / SIM_STEP)))
    dt = seconds / steps
    for _ in range(steps):
        world.update(dt)


_pattern_cache = {}


def _pattern_info(pattern, speed):
    """(offset در FIRE_TIME، پوشش حرکت (minx,maxx,miny,maxy)) -- عددی، از MovementSystem واقعی."""
    key = (pattern, speed)
    if key not in _pattern_cache:
        world = World()
        world.add_system(MovementSystem())
        entity = world.create_entity()
        world.add_component(entity, Position, x=0.0, y=0.0)
        world.add_component(entity, Target, hp=1, max_hp=1, move_pattern=pattern, speed=speed,
                            origin_x=0.0, origin_y=0.0, radius=TARGET_RADIUS)
        pos = entity.get_component(Position)
        xs, ys = [0.0], [0.0]
        fire_offset = (0.0, 0.0)
        polyline = [(0.0, 0.0)]
        elapsed = 0.0
        while elapsed < 40.0:
            _advance(world, 0.5)
            elapsed += 0.5
            xs.append(pos.x)
            ys.append(pos.y)
            if math.hypot(pos.x - polyline[-1][0], pos.y - polyline[-1][1]) >= 12.0:
                polyline.append((pos.x, pos.y))
            if abs(elapsed - FIRE_TIME) < 1e-9:
                fire_offset = (pos.x, pos.y)
        _pattern_cache[key] = (fire_offset, (min(xs), max(xs), min(ys), max(ys)), polyline)
    return _pattern_cache[key]


def _make_world(level, seconds=0.0):
    world = World()
    world.add_system(MovementSystem())
    world.add_system(RotationSystem())
    gun_x, gun_y = level.populate_world(world)
    _advance(world, seconds)
    targets = sorted(world.get_entities_with(Position, Target), key=lambda e: e.id)
    return world, gun_x, gun_y, targets


def _window_deg(surfaces, gun_x, gun_y, angle, target_id, limit=4.0, step=0.1):
    """پهنای کل (درجه) بازه‌ی زاویه‌ی اطراف راه‌حل که هنوز به هدف می‌خورد؛ -1 اگر خودِ راه‌حل نخورد."""
    if not _aim_hits_target(gun_x, gun_y, surfaces, angle, target_id):
        return -1.0
    half, d = 0.0, step
    while d <= limit:
        if (_aim_hits_target(gun_x, gun_y, surfaces, angle + d, target_id)
                and _aim_hits_target(gun_x, gun_y, surfaces, angle - d, target_id)):
            half, d = d, d + step
        else:
            break
    return 2.0 * half


def _time_half_window(level, index, angle, t_star):
    """نیم‌پنجره‌ی زمانی (ثانیه) که شلیک با همان زاویه هنوز به هدف می‌خورد (برای آینه‌ی چرخان)."""
    half, dt = 0.0, 0.02
    while dt <= 0.4:
        ok = True
        for t in (t_star - dt, t_star + dt):
            world, gx, gy, targets = _make_world(level, max(t, 0.0))
            surfaces = deterministic_surfaces(entities_to_surfaces(world))
            if not _aim_hits_target(gx, gy, surfaces, angle, targets[index].id):
                ok = False
                break
        if not ok:
            break
        half, dt = dt, dt + 0.02
    return half


def verify_solutions(data, solutions, min_window_deg):
    """بازپخش راه‌حل‌های ساخته‌شده با موتور Raycasting واقعی. برمی‌گرداند (موفق؟، پنجره‌ها)."""
    level = Level(data)
    windows = []
    for index, angle, t_star in solutions:
        world, gx, gy, targets = _make_world(level, t_star)
        surfaces = deterministic_surfaces(entities_to_surfaces(world))
        window = _window_deg(surfaces, gx, gy, angle, targets[index].id)
        if window < min_window_deg:
            return False, windows
        windows.append(window)
    return True, windows


# ------------------------------------------------------------------ ساخت مسیر
def _align_time(phi_deg, speed):
    """کوچک‌ترین t ≥ FIRE_TIME+0.2 که جهت آینه‌ی چرخان (s·t mod 360) با φ (mod 180) یکی می‌شود.
    RotationSystem از ۰° *مطلق* شروع می‌کند، نه از جهت اولیه‌ی JSON."""
    period = 180.0 / abs(speed)
    t = ((phi_deg % 180.0) / speed) % period
    while t < FIRE_TIME + 0.2:
        t += period
    return t


def _box_range(cx, cy, dx, dy, x0, x1, y0, y1):
    """بازه‌ی پارامتر t (طول) که پرتو (c + t·d) داخل جعبه است، یا None."""
    t0, t1 = 0.0, float('inf')
    for c, d, lo, hi in ((cx, dx, x0, x1), (cy, dy, y0, y1)):
        if abs(d) < 1e-9:
            if c < lo or c > hi:
                return None
            continue
        ta, tb = (lo - c) / d, (hi - c) / d
        if ta > tb:
            ta, tb = tb, ta
        t0, t1 = max(t0, ta), min(t1, tb)
    return (t0, t1) if t1 > t0 else None


WAYPOINT_BOX = (X_MIN + 60.0, X_MAX - 60.0, Y_MIN + 60.0, Y_MAX - 60.0)
FINAL_MIN = 200.0           # کوتاه‌ترین پاره‌ی آخر (آینه‌ی آخر -> هدف)
MIRROR_MIN_HALF = 60.0
STEER_TRIES = 14
PATH_TRIES = 90            # تلاش برای هر مسیر؛ هر ۳۰ شکست یک کمانه‌ی ساده کم می‌شود


def _target_box(spec):
    """جعبه‌ی مجاز برای نقطه‌ی T (جایی که هدف در FIRE_TIME هست) تا کل حرکت هدف داخل میدان بماند.
    (جعبه، offset در FIRE_TIME) یا None."""
    m = TARGET_RADIUS + 20.0
    if spec['pattern'] == 'static':
        return (X_MIN + m, X_MAX - m, Y_MIN + m, Y_MAX - m), (0.0, 0.0)
    (fx, fy), (minx, maxx, miny, maxy), _poly = _pattern_info(spec['pattern'], spec['speed'])
    box = (X_MIN + m - minx + fx, X_MAX - m - maxx + fx, Y_MIN + m - miny + fy, Y_MAX - m - maxy + fy)
    if box[0] > box[1] or box[2] > box[3]:
        return None
    return box, (fx, fy)


def _pick_length(rng, cx, cy, dx, dy, box, lo_min, hi_max):
    room = _box_range(cx, cy, dx, dy, *box)
    if room is None:
        return None
    lo, hi = max(lo_min, room[0]), min(hi_max, room[1])
    return rng.uniform(lo, hi) if lo <= hi else None


def _build_path(rng, geo, pid, elements, theta, target_spec, scale):
    """یک مسیر حل: اسلحه -> عناصر -> هدف. (geo_جدید، رکورد) یا None.

    *هدایت‌شده* می‌سازد، نه «بپران و رد کن»: طول هر پاره فقط از بازه‌ای انتخاب می‌شود که پرتو
    هنوز داخل جعبه است، و جهت بازتاب طوری که برای قدم بعد جا بماند (lookahead). نسخه‌ی اول
    (رد کردن نقطه‌های بیرون‌افتاده) روی مراحل ۳۳ به بالا ۸۰ تا ۹۰ درصد تلاش‌ها را هدر می‌داد و
    ۵۰ مرحله به fallback می‌رسید."""
    tbox = _target_box(target_spec)
    if tbox is None:
        return _fail('envelope_out')
    target_box, (fire_dx, fire_dy) = tbox

    g = geo.copy()
    cx, cy = GUN_X, GUN_Y
    dx, dy = math.cos(math.radians(theta)), math.sin(math.radians(theta))
    prev_skip = set()
    mirrors, portals = [], []
    t_star = FIRE_TIME
    half_range = (110.0 - 40.0 * scale, 150.0 - 50.0 * scale)

    for index, element in enumerate(elements):
        last = index == len(elements) - 1
        next_box = target_box if last else WAYPOINT_BOX
        next_min = FINAL_MIN if last else LEG_MIN
        placed = False
        for _ in range(STEER_TRIES):
            snapshot = g.copy()        # عقب‌گرد محلی: فقط همین قدم دوباره امتحان می‌شود
            mark = g.mark()
            length = _pick_length(rng, cx, cy, dx, dy, WAYPOINT_BOX, LEG_MIN, LEG_MAX)
            if length is None:
                return _fail('no_room')
            px, py = cx + dx * length, cy + dy * length

            if element in ('mirror', 'rotating'):
                delta = rng.uniform(40.0, 140.0) * rng.sign()
                ndx, ndy = _rotate(dx, dy, delta)
                room = _box_range(px, py, ndx, ndy, *next_box)
                if room is None or room[1] < next_min:
                    _fail('step_lookahead' + ('_final' if last else ''))
                    continue
                nx, ny = ndx - dx, ndy - dy
                norm = math.hypot(nx, ny)
                nx, ny = nx / norm, ny / norm
                tx, ty = -ny, nx
                reach_a = _box_range(px, py, tx, ty, X_MIN, X_MAX, Y_MIN, Y_MAX)
                reach_b = _box_range(px, py, -tx, -ty, X_MIN, X_MAX, Y_MIN, Y_MAX)
                if reach_a is None or reach_b is None:
                    _fail('step_reach')
                    continue
                h = min(rng.uniform(*half_range), reach_a[1], reach_b[1])
                if h < MIRROR_MIN_HALF:
                    _fail('step_half_len')
                    continue
                seg = (px - tx * h, py - ty * h, px + tx * h, py + ty * h)
                entry = {'x1': seg[0], 'y1': seg[1], 'x2': seg[2], 'y2': seg[3], 'type': PLAIN_MIRROR,
                         'reflectivity': 1.0, 'rotation_speed': 0.0}
                oid = g.add_solid(seg, 'mirror', path=pid)
                skip = {oid}
                if element == 'rotating':
                    speed = rng.choice(ROTATION_SPEEDS) * rng.sign()
                    entry.update({'type': 'rotating_mirror', 'rotation_speed': speed,
                                  'pivot_x': px, 'pivot_y': py})
                    t_star = _align_time(math.degrees(math.atan2(ty, tx)), speed)
                    skip.add(g.add_disc(px, py, h + CLEAR * 0.5, 'swept', True, pid, owner=oid))
                g.add_leg((cx, cy, px, py), prev_skip | skip)
                if not g.ok(mark):
                    _fail('step_geo')
                    g = snapshot
                    continue
                mirrors.append(entry)
                prev_skip, cx, cy, dx, dy = skip, px, py, ndx, ndy
                placed = True
                break

            # --- portal ---
            exit_found = None
            for _ in range(12):
                ex, ey = rng.uniform(X_MIN + 60, X_MAX - 60), rng.uniform(Y_MIN + 60, Y_MAX - 60)
                if math.hypot(ex - px, ey - py) < 260.0 or math.hypot(ex - GUN_X, ey - GUN_Y) < 300.0:
                    continue
                angle = rng.uniform(25.0, 155.0)
                edx, edy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
                room = _box_range(ex, ey, edx, edy, *next_box)
                if room is not None and room[1] >= next_min:
                    exit_found = (ex, ey, angle, edx, edy)
                    break
            if exit_found is None:
                continue
            ex, ey, angle, edx, edy = exit_found
            entry_id = g.add_disc(px, py, 35.0, 'portal', True, pid)
            exit_id = g.add_disc(ex, ey, 22.0, 'portal_exit', True, pid)
            g.add_leg((cx, cy, px, py), prev_skip | {entry_id})
            if not g.ok(mark):
                g = snapshot
                continue
            portals.append({'x': px, 'y': py, 'radius': 35.0, 'exit_x': ex, 'exit_y': ey,
                            'exit_angle': angle})
            prev_skip, cx, cy, dx, dy = {exit_id}, ex, ey, edx, edy
            placed = True
            break
        if not placed:
            return _fail('steer_fail')

    pattern = target_spec['pattern']
    committed = False
    for _ in range(STEER_TRIES):
        length = _pick_length(rng, cx, cy, dx, dy, target_box, FINAL_MIN, LEG_MAX)
        if length is None:
            return _fail('final_no_room')
        tx_, ty_ = cx + dx * length, cy + dy * length
        snapshot = g.copy()
        mark = g.mark()
        if pattern == 'static':
            ox, oy = tx_, ty_
            tid = g.add_disc(ox, oy, TARGET_RADIUS, 'target', True, pid)
            g.add_leg((cx, cy, tx_, ty_), prev_skip | {tid})
        else:
            ox, oy = tx_ - fire_dx, ty_ - fire_dy
            _o, _bbox, polyline = _pattern_info(pattern, target_spec['speed'])
            g.add_sweep([(ox + px_, oy + py_) for px_, py_ in polyline], pid)
            # موتور هدف متحرک را در شروع مرحله روی «مبدأ» می‌گذارد؛ دو مبدأ نزدیک = دو هدف روی هم
            # برای یک فریم (تست فایل‌های واقعی، مراحل ۹۱ و ۹۲). مسیر شلیک را نمی‌بندد.
            g.add_disc(ox, oy, TARGET_RADIUS, 'origin', False, pid)
            g.add_leg((cx, cy, tx_, ty_), prev_skip)
        if g.ok(mark):
            committed = True
            break
        g = snapshot
    if not committed:
        return _fail('geo_conflict')
    return g, {'mirrors': mirrors, 'portals': portals, 'target': (ox, oy, pattern, target_spec['speed']),
               'solution': (theta, t_star), 'rotating': any(e == 'rotating' for e in elements)}


# ------------------------------------------------------------------ ساخت مرحله
def campaign_seed(level_id):
    return 7919 * int(level_id) + 104729


def campaign_rewards(level_id):
    """از مرحله‌ی ۵ (۲۲ سکه) با شیب ملایم ادامه می‌یابد؛ هر ۱۰ مرحله ۱ جواهر.
    ⚠️ AVG_COINS_PER_LEVEL=17 در EconomyBalance برای ۵ مرحله‌ی دستی است (میانگین دقیقاً ۱۷)؛ پاداش
    مراحل بعدی ۲۲ تا ۴۶ است -- بازتوازن اقتصاد کامل کار فاز۱۰ (پولیش) است."""
    return {'coins': int(round(22 + 0.25 * (level_id - 5))), 'gems': 1 if level_id % 10 == 0 else 0,
            'xp': 12 + (level_id - 5) // 2}


_HINTS = {
    'semi_mirror': 'آینه‌ی نیمه‌شفاف پرتو را دو شاخه می‌کند: بخشی بازتاب می‌شود و بخشی عبور می‌کند.',
    'rotating_mirror': 'آینه‌ی چرخان: صبر کن زاویه‌اش درست شود، بعد شلیک کن.',
    'prism': 'منشور پرتو را به چند شاخه‌ی رنگی تقسیم می‌کند.',
    'portal': 'پورتال: پرتو از یک نقطه وارد می‌شود و از نقطه‌ی دیگر با زاویه‌ی ثابت بیرون می‌آید.',
    'black_hole': 'سیاه‌چاله پرتو را می‌بلعد و از جای دیگر با زاویه‌ی تصادفی بیرون می‌دهد؛ از آن دوری کن.',
    'broken_mirror': 'آینه‌ی شکسته بازتاب را کمی پراکنده می‌کند؛ روی آن حساب نکن.',
}


def _plan_features(rng, level_id, unlocked, scale, intro_forced):
    base = {'semi_mirror': 0.30 + 0.30 * scale, 'rotating_mirror': 0.20 + 0.25 * scale,
            'prism': 0.25 + 0.25 * scale, 'portal': 0.20 + 0.25 * scale,
            'black_hole': 0.25 + 0.35 * scale, 'broken_mirror': 0.25 + 0.35 * scale}
    plan = {}
    for mechanic in ('semi_mirror', 'rotating_mirror', 'prism', 'portal', 'black_hole', 'broken_mirror'):
        draw = rng.random()          # همیشه می‌کشیم تا توالی RNG به فهرست باز وابسته نباشد
        plan[mechanic] = mechanic in unlocked and (mechanic == intro_forced or draw < base[mechanic])
    return plan


def _build_candidate(rng, level_id, params, scale, intro_forced):
    unlocked = set(params['unlocked_mechanics'])
    low, high = params['target_count_range']
    n_targets = rng.randint(low, high)
    plan = _plan_features(rng, level_id, unlocked, scale, intro_forced)

    k_max = 2 + int(round(2.5 * scale))
    moving_prob = 0.25 + 0.55 * scale
    patterns = ['linear_horizontal', 'linear_vertical']
    if scale >= 0.12:
        patterns += ['circular', 'zigzag']
    if scale >= 0.45:
        patterns += ['combined']

    specs = []
    for _ in range(n_targets):
        ks = rng.randint(max(0, k_max - 2), k_max)
        moving = rng.chance(moving_prob)
        pattern = rng.choice(patterns) if moving else 'static'
        specs.append({'k': ks, 'pattern': pattern, 'speed': PATTERN_SPEED.get(pattern, 0.0)})

    # حداقل پیچیدگی: بدون این، k=0 باعث می‌شد مرحله‌ی میانی (مثلاً ۲۵) فقط شلیک‌های مستقیم باشد.
    # (در رندر دیده شد.) از مرحله‌ی ۱۰ به بعد، مجموع کمانه‌ها باید با سختی بالا برود.
    if level_id >= 10:
        total_needed = int(round(n_targets * (0.4 + 1.3 * scale)))
        guard = 0
        while sum(s['k'] for s in specs) < total_needed and guard < 40:
            guard += 1
            spec = specs[rng.randint(0, n_targets - 1)]
            if spec['k'] < k_max:
                spec['k'] += 1

    rot_path = port_path = None
    if plan['rotating_mirror']:
        cands = [i for i, s in enumerate(specs) if s['k'] >= 1]
        if not cands:
            if intro_forced == 'rotating_mirror':
                return _fail('rot_none')
            plan['rotating_mirror'] = False
        else:
            rot_path = rng.choice(cands)
            specs[rot_path]['pattern'], specs[rot_path]['speed'] = 'static', 0.0
    if plan['portal']:
        port_path = rng.randint(0, n_targets - 1)

    geo, records, used_theta = _Geo(), [], []
    for i, spec in enumerate(specs):
        elements = ['mirror'] * spec['k']
        if i == rot_path:
            elements[rng.randint(0, len(elements) - 1)] = 'rotating'
        if i == port_path:
            elements.insert(rng.randint(0, len(elements)), 'portal')
        built = None
        for attempt in range(PATH_TRIES):
            # میدان شلوغ است؟ هر ۳۰ شکست، یک کمانه‌ی ساده کم می‌شود (هدف و مکانیک‌های ویژه می‌مانند)
            if attempt and attempt % 30 == 0 and elements.count('mirror') > 1:
                elements.remove('mirror')
            theta = rng.uniform(38.0, 142.0)
            if any(abs(theta - u) < 14.0 for u in used_theta):
                continue
            built = _build_path(rng, geo, i, elements, theta, spec, scale)
            if built is not None:
                used_theta.append(theta)
                break
        if built is None:
            return _fail('path_fail')
        geo, record = built
        records.append(record)

    mirrors = [dict(m) for r in records for m in r['mirrors']]
    portals = [dict(p) for r in records for p in r['portals']]
    if plan['semi_mirror']:
        plain = [m for m in mirrors if m['type'] == PLAIN_MIRROR]
        if not plain:
            if intro_forced == 'semi_mirror':
                return _fail('semi_none')
        else:
            chosen = rng.choice(plain)
            chosen['type'], chosen['reflectivity'] = 'semi_mirror', 0.5
    if intro_forced == 'portal' and not portals:
        return _fail('portal_none')

    obstacles, prisms, black_holes = [], [], []

    def place_segment(kind, length_range, tries=40):
        for _ in range(tries):
            ang = rng.uniform(0.0, 180.0)
            length = rng.uniform(*length_range)
            mx, my = rng.uniform(X_MIN + 80, X_MAX - 80), rng.uniform(Y_MIN + 80, Y_MAX - 80)
            hx, hy = math.cos(math.radians(ang)) * length / 2, math.sin(math.radians(ang)) * length / 2
            seg = (mx - hx, my - hy, mx + hx, my + hy)
            if not (_inside(seg[0], seg[1]) and _inside(seg[2], seg[3])):
                continue
            trial = geo.copy()
            mark = trial.mark()
            trial.add_solid(seg, kind)
            if trial.ok(mark):
                geo.solids, geo._next = trial.solids, trial._next
                return seg
        return None

    def place_disc(kind, radius, tries=40):
        for _ in range(tries):
            x, y = rng.uniform(X_MIN + 80, X_MAX - 80), rng.uniform(Y_MIN + 80, Y_MAX - 80)
            trial = geo.copy()
            mark = trial.mark()
            trial.add_disc(x, y, radius, kind)
            if trial.ok(mark):
                geo.discs, geo._next = trial.discs, trial._next
                return x, y
        return None

    for _ in range(int(round(scale * 3.5 + rng.random() * 1.5))):
        seg = place_segment('mirror', (90.0, 200.0))
        if seg:
            mirrors.append({'x1': seg[0], 'y1': seg[1], 'x2': seg[2], 'y2': seg[3], 'type': PLAIN_MIRROR,
                            'reflectivity': 1.0, 'rotation_speed': 0.0})
    if level_id >= 10:
        for _ in range(int(round(scale * 3.0 + rng.random()))):
            seg = place_segment('obstacle', (110.0, 280.0))
            if seg:
                obstacles.append({'x1': seg[0], 'y1': seg[1], 'x2': seg[2], 'y2': seg[3],
                                  'destructible': False, 'hp': 999})
    if plan['prism']:
        for _ in range(1 + int(scale > 0.6)):
            spot = place_disc('prism', 30.0)
            if spot:
                prisms.append({'x': spot[0], 'y': spot[1], 'radius': 30.0})
        if intro_forced == 'prism' and not prisms:
            return _fail('prism_none')
    if plan['black_hole']:
        for _ in range(1 + int(scale > 0.7)):
            spot = place_disc('black_hole', 50.0)
            if spot:
                black_holes.append({'x': spot[0], 'y': spot[1], 'radius': 50.0,
                                    'emit_x': rng.uniform(X_MIN + 80, X_MAX - 80),
                                    'emit_y': rng.uniform(Y_MIN + 80, Y_MAX - 80)})
        if intro_forced == 'black_hole' and not black_holes:
            return _fail('black_hole_none')
    if plan['broken_mirror']:
        placed = 0
        for _ in range(1 + int(scale > 0.5)):
            seg = place_segment('broken_mirror', (100.0, 190.0))
            if seg:
                mirrors.append({'x1': seg[0], 'y1': seg[1], 'x2': seg[2], 'y2': seg[3],
                                'type': 'broken_mirror', 'reflectivity': 1.0, 'rotation_speed': 0.0})
                placed += 1
        if intro_forced == 'broken_mirror' and not placed:
            return _fail('broken_none')

    targets = [{'x': r['target'][0], 'y': r['target'][1], 'hp': 1, 'move_pattern': r['target'][2],
                'speed': r['target'][3], 'radius': TARGET_RADIUS} for r in records]
    solutions = [(i, r['solution'][0], r['solution'][1]) for i, r in enumerate(records)]
    return {'targets': targets, 'mirrors': mirrors, 'obstacles': obstacles, 'portals': portals,
            'prisms': prisms, 'black_holes': black_holes, 'solutions': solutions,
            'rot_index': rot_path}


def _round(v):
    return round(float(v), 1)


def _assemble(label_id, params, cand, rewards):
    def seg_entry(prefix, i, m, extra):
        entry = {'id': f'{prefix}_{i}', 'x1': _round(m['x1']), 'y1': _round(m['y1']),
                 'x2': _round(m['x2']), 'y2': _round(m['y2'])}
        entry.update(extra)
        return entry

    mirrors = []
    for i, m in enumerate(cand['mirrors'], 1):
        extra = {'type': m['type'], 'reflectivity': m['reflectivity'],
                 'rotation_speed': m['rotation_speed']}
        if m['type'] == 'rotating_mirror':
            extra.update({'pivot_x': _round(m['pivot_x']), 'pivot_y': _round(m['pivot_y'])})
        mirrors.append(seg_entry('mirror', i, m, extra))
    mechanics = {m['type'] for m in cand['mirrors']}
    mechanics |= {'portal'} if cand['portals'] else set()
    mechanics |= {'prism'} if cand['prisms'] else set()
    mechanics |= {'black_hole'} if cand['black_holes'] else set()
    hint_key = next((k for k in ('portal', 'black_hole', 'broken_mirror', 'rotating_mirror', 'prism',
                                  'semi_mirror') if k in mechanics), None)
    n = len(cand['targets'])
    return {
        'level_id': label_id, 'phase': params['phase_key'],
        'difficulty': params['difficulty_value'], 'time_limit': params['time_limit_seconds'],
        'laser_start': {'x': GUN_X, 'y': GUN_Y, 'angle': 90},
        'targets': [{'id': f'target_{i}', 'x': _round(t['x']), 'y': _round(t['y']), 'hp': 1,
                     'move_pattern': t['move_pattern'], 'speed': t['speed'], 'radius': TARGET_RADIUS}
                    for i, t in enumerate(cand['targets'], 1)],
        'mirrors': mirrors,
        'obstacles': [seg_entry('obstacle', i, o, {'destructible': False, 'hp': 999})
                      for i, o in enumerate(cand['obstacles'], 1)],
        'portals': [{'id': f'portal_{i}', 'x': _round(p['x']), 'y': _round(p['y']), 'radius': 35.0,
                     'exit_x': _round(p['exit_x']), 'exit_y': _round(p['exit_y']),
                     'exit_angle': _round(p['exit_angle'])} for i, p in enumerate(cand['portals'], 1)],
        'prisms': [{'id': f'prism_{i}', 'x': _round(p['x']), 'y': _round(p['y']), 'radius': 30.0}
                   for i, p in enumerate(cand['prisms'], 1)],
        'black_holes': [{'id': f'blackhole_{i}', 'x': _round(b['x']), 'y': _round(b['y']), 'radius': 50.0,
                         'emit_x': _round(b['emit_x']), 'emit_y': _round(b['emit_y'])}
                        for i, b in enumerate(cand['black_holes'], 1)],
        'rewards': dict(rewards),
        'hints': [_HINTS.get(hint_key, f'{n} هدف داری؛ برای هر کدام یک مسیر کمانه بساز.')],
    }


def _fallback(label_id, params, rewards):
    """آخرین چاره (فقط بعد از شکست همه‌ی تلاش‌ها): یک هدف ساکن، شلیک مستقیم -- حل‌پذیر قطعی."""
    cand = {'targets': [{'x': 540.0, 'y': 1000.0, 'hp': 1, 'move_pattern': 'static', 'speed': 0.0}],
            'mirrors': [], 'obstacles': [], 'portals': [], 'prisms': [], 'black_holes': []}
    return _assemble(label_id, params, cand, rewards)


def generate_level(level_id, seed=None, equivalent_level=None, rewards=None, with_info=False):
    """مرحله‌ی حل‌پذیر-اثبات‌شده را به‌صورت dict (همان ساختار JSON مراحل) تولید می‌کند.

    level_id: برچسبی که در JSON می‌نشیند. equivalent_level: اگر داده شود، پارامترهای سختی از آن
    مرحله‌ی کمپین گرفته می‌شود (حالت بی‌نهایت/چالش روزانه)؛ در این حالت «معرفی اجباری مکانیک»
    خاموش است. with_info: (data، info) با تعداد تلاش/کاهش سختی/استفاده از fallback."""
    manager = DifficultyManager()
    campaign = equivalent_level is None
    eq = min(max(int(level_id if campaign else equivalent_level), 1), TOTAL_LEVELS)
    params = manager.get_recommended_params(eq)
    scale = (params['difficulty_value'] - 1.0) / 9.0
    seed = campaign_seed(level_id) if seed is None else int(seed)
    rewards = campaign_rewards(level_id) if rewards is None else rewards
    intro = None
    if campaign:
        intro = next((m for m, lv in MECHANIC_UNLOCK_LEVEL.items() if lv == level_id and m != 'normal'), None)

    attempts = 0
    for reduction in range(MAX_REDUCTIONS + 1):
        eff = scale * (0.8 ** reduction)
        min_window = 2.2 - 1.4 * eff
        for attempt in range(MAX_ATTEMPTS):
            attempts += 1
            rng = SeededRng(seed * 1000003 + reduction * 1009 + attempt)
            cand = _build_candidate(rng, level_id, params, eff, intro)
            if cand is None:
                continue
            data = _assemble(level_id, params, cand, rewards)
            ok, windows = verify_solutions(data, cand['solutions'], min_window)
            if not ok:
                _fail('window')
                continue
            if cand['rot_index'] is not None:
                index = cand['rot_index']
                _i, angle, t_star = cand['solutions'][index]
                if _time_half_window(Level(data), index, angle, t_star) < MIN_TIME_WINDOW:
                    _fail('time_window')
                    continue
            info = {'attempts': attempts, 'reductions': reduction, 'fallback': False,
                    'solutions': list(cand['solutions']), 'windows': windows}
            return (data, info) if with_info else data
    data = _fallback(level_id, params, rewards)
    info = {'attempts': attempts, 'reductions': MAX_REDUCTIONS, 'fallback': True,
            'solutions': [(0, 90.0, FIRE_TIME)], 'windows': []}
    return (data, info) if with_info else data


# ------------------------------------------------------------------ قالب‌بندی فایل JSON
_LIST_KEYS = ('targets', 'mirrors', 'obstacles', 'portals', 'prisms', 'black_holes')


def format_level_json(data):
    """همان قالب فشرده‌ی فایل‌های دستی: کلیدهای سطح بالا هر کدام یک خط، هر عنصر لیست یک خط.
    (دیف و بازبینی مراحل تولیدی با مراحل دستی یکدست می‌شود.)"""
    import json

    def inline(value):
        return json.dumps(value, ensure_ascii=False)

    lines = ['{']
    keys = list(data)
    for index, key in enumerate(keys):
        comma = ',' if index < len(keys) - 1 else ''
        value = data[key]
        if key in _LIST_KEYS and value:
            lines.append(f'  "{key}": [')
            for j, item in enumerate(value):
                lines.append(f'    {inline(item)}' + (',' if j < len(value) - 1 else ''))
            lines.append(f'  ]{comma}')
        else:
            lines.append(f'  "{key}": {inline(value)}{comma}')
    lines.append('}')
    return '\n'.join(lines) + '\n'
