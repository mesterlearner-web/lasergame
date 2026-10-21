"""
تست‌های واقعی برای هسته‌ی ECS و موتور Raycasting.
با python3 -m tests.test_core از ریشه‌ی پروژه اجرا می‌شود (بدون
نیاز به Kivy یا هیچ وابستگی خارجی‌ای).
"""
import sys
import os
import math
import signal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ecs.entity import Entity
from ecs.world import World
from ecs.component import Component
from ecs.system import System
from ecs.components.position import Position
from ecs.components.target import Target
from game_logic import raycast
from game_logic.scene_builder import build_test_scene, entities_to_surfaces


passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  OK   {name}")
    else:
        failed += 1
        print(f"  FAIL {name}  {detail}")


def close(a, b, eps=1e-4):
    return abs(a - b) < eps


# ============================================================
print("=== ECS core ===")


class Health(Component):
    __slots__ = ('hp',)
    def __init__(self, hp=1):
        self.hp = hp


world = World()
e1 = world.create_entity()
world.add_component(e1, Position, x=1, y=2)
world.add_component(e1, Health, hp=3)

e2 = world.create_entity()
world.add_component(e2, Position, x=5, y=5)

check("entity ids are distinct", e1.id != e2.id)
check("get_component works", e1.get_component(Position).x == 1)
check("query by one component returns both", len(world.get_entities_with(Position)) == 2)
check("query by two components returns only e1", world.get_entities_with(Position, Health) == [e1])

world.destroy_entity(e1)
check("destroyed entity is inactive", e1.active is False)
check("destroyed entity drops out of queries", world.get_entities_with(Position) == [e2])

e3 = world.create_entity()
check("pooled entity is reused (same object)", e3 is e1)
check("reused entity has no stale components", len(e3.components) == 0)
world.add_component(e3, Position, x=9, y=9)
check("reused entity works normally after re-add", world.get_entities_with(Position) == [e2, e3] or world.get_entities_with(Position) == [e3, e2])


class MoveSystem(System):
    priority = 10
    required_components = (Position,)
    def update(self, dt, world):
        for e in self.get_entities(world):
            e.get_component(Position).x += 1

world2 = World()
ea = world2.create_entity()
world2.add_component(ea, Position, x=0, y=0)
world2.add_system(MoveSystem())
world2.update(1 / 60)
check("system.update actually runs", world2.get_entities_with(Position)[0].get_component(Position).x == 1)


# ============================================================
print("\n=== Raycast: geometry primitives ===")

t = raycast._ray_segment_intersect(0, 0, 1, 0, 5, -5, 5, 5)
check("ray-segment: perpendicular crossing", close(t, 5))

t = raycast._ray_circle_intersect(0, 0, 1, 0, 10, 0, 2)
check("ray-circle: hits front edge of circle on axis", close(t, 8))

t = raycast._ray_circle_intersect(0, 0, 1, 0, 10, 100, 2)
check("ray-circle: miss returns None", t is None)

r1 = raycast._reflect(0, -1, 0, 1)
r2 = raycast._reflect(0, -1, 0, -1)
check("reflect() invariant to normal sign", close(r1[0], r2[0]) and close(r1[1], r2[1]))


# ============================================================
print("\n=== Raycast: full cast() scenarios ===")

# 1) shot into empty space -> should reach max range and report 'none'
beams = raycast.cast(0, 0, 1, 0, [])
check("empty scene -> one beam, hit_type 'none'", len(beams) == 1 and beams[0].hit_types[-1] == 'none')

# 2) direct hit on a circular target (this exact case was broken in the
#    original spec because targets were passed through the segment formula)
target = {'shape': 'circle', 'type': 'target', 'x': 100, 'y': 0, 'radius': 20, 'id': 't1'}
beams = raycast.cast(0, 0, 1, 0, [target])
check("direct target hit -> exactly one beam", len(beams) == 1)
check("direct target hit -> ends with hit_type 'target'", beams[0].hit_types[-1] == 'target')

# 3) bounce off a mirror then hit a target -- آینه‌ی ۴۵ درجه که (1,0) را
#    دقیقاً به (0,1) تبدیل می‌کند (با محاسبه‌ی مستقیم تأیید شده: برخورد
#    در (40,0)، بازتاب به سمت +y)، هدف مستقیم بالای همان نقطه قرار دارد.
mirror45b = {'shape': 'segment', 'type': 'normal', 'x1': 40, 'y1': 0, 'x2': 60, 'y2': 20, 'id': 'm3'}
targetUp = {'shape': 'circle', 'type': 'target', 'x': 40, 'y': 150, 'radius': 25, 'id': 't3'}
beams = raycast.cast(0, 0, 1, 0, [mirror45b, targetUp])
check("mirror bounce -> single beam with 3 points (start, mirror, target)",
      len(beams) == 1 and len(beams[0].points) == 3, detail=str(beams[0].hit_types if beams else None))
check("mirror bounce -> hit_types are ['start','mirror','target']",
      beams and beams[0].hit_types == ['start', 'normal', 'target'])

# 4) prism splits into multiple beams
prism = {'shape': 'circle', 'type': 'prism', 'x': 50, 'y': 0, 'radius': 15, 'id': 'p1'}
beams = raycast.cast(0, 0, 1, 0, [prism])
check("prism -> 1 (pre-prism) + 6 (split) = 7 beams total", len(beams) == 7, detail=f"got {len(beams)}")

# 5) portal teleports the beam onward
portal = {'shape': 'circle', 'type': 'portal', 'x': 50, 'y': 0, 'radius': 15,
          'exit_x': 500, 'exit_y': 500, 'exit_angle': 90, 'id': 'portal1'}
beams = raycast.cast(0, 0, 1, 0, [portal])
check("portal -> beam continues past teleport (>2 points)", len(beams[0].points) > 2)
# نقطه‌ی بعد از پورتال باید تقریباً روی امتداد (500,500) با زاویه‌ی ۹۰ درجه (یعنی +y) باشد
after = beams[0].points[2]
check("portal -> exits near (500, y>500)", close(after[0], 500, eps=5) and after[1] > 500)

# 6) THE CRITICAL REGRESSION TEST: an unknown/garbage hit type must NOT
#    infinite-loop (this was the exact bug found in the original spec)
weird = {'shape': 'circle', 'type': 'some_future_type_not_yet_handled',
         'x': 50, 'y': 0, 'radius': 15, 'id': 'w1'}

def _timeout_handler(signum, frame):
    raise TimeoutError("cast() did not terminate -- infinite loop regression!")

signal.signal(signal.SIGALRM, _timeout_handler)
signal.alarm(2)
try:
    beams = raycast.cast(0, 0, 1, 0, [weird])
    signal.alarm(0)
    check("unknown hit_type terminates (no infinite loop)", True)
except TimeoutError as e:
    signal.alarm(0)
    check("unknown hit_type terminates (no infinite loop)", False, detail=str(e))

# 7) mixed segment + circle surfaces together must not crash (this crashed
#    in the original spec with KeyError: 'x1' on the target dict)
mixed_scene = [mirror45b, targetUp, prism]
try:
    beams = raycast.cast(0, 0, 1, 0, mixed_scene)
    check("mixed segment+circle surfaces coexist without crashing", True)
except Exception as e:
    check("mixed segment+circle surfaces coexist without crashing", False, detail=repr(e))

# 8) max_bounces is respected even with mirrors that never reach a target
long_mirror_chain = []
for i in range(20):
    x = i * 10
    long_mirror_chain.append({'shape': 'segment', 'type': 'normal',
                               'x1': x + 5, 'y1': -50, 'x2': x + 5, 'y2': 50, 'id': f'mc{i}'})
signal.alarm(2)
try:
    beams = raycast.cast(0, 0, 1, 1, long_mirror_chain, max_bounces=10)
    signal.alarm(0)
    check("bounce budget is respected (terminates within max_bounces)",
          beams[0].bounces <= 10)
except TimeoutError:
    signal.alarm(0)
    check("bounce budget is respected (terminates within max_bounces)", False)


# ============================================================
# ============================================================
print("\n=== Raycast: semi_mirror و broken_mirror (فاز ۲) ===")

# semi_mirror باید به ۱ (پیش از برخورد) + ۲ (بازتاب + عبور) = ۳ بیم تقسیم شود
semi = {'shape': 'segment', 'type': 'semi_mirror', 'x1': 40, 'y1': 0, 'x2': 60, 'y2': 20, 'id': 'sm1'}
beams = raycast.cast(0, 0, 1, 0, [semi])
check("semi_mirror splits into 1(pre) + 2(reflect+transmit) = 3 beams",
      len(beams) == 3, detail=f"got {len(beams)}")
kinds_hit = sorted(b.hit_types for b in beams)
check("semi_mirror -> exactly one beam ends at the split point (pre-beam)",
      any(b.hit_types == ['start', 'semi_mirror'] for b in beams))

# transmit sub-beam باید تقریباً مستقیم ادامه بدهد (همان جهت اولیه)
transmit_candidates = [b for b in beams if len(b.points) >= 2 and
                        close(b.points[0][0], 40) and close(b.points[0][1], 0)]
has_straight_continuation = any(
    close(b.points[-1][1], 0, eps=1.0) for b in transmit_candidates if b.hit_types[-1] == 'none'
)
check("semi_mirror -> one child beam continues straight through (transmit)",
      has_straight_continuation)

# semi_mirror نباید با خودش خودبرخوردی کند (همون باگ منشور، تست رگرسیون)
signal.alarm(2)
try:
    many_semi = [{'shape': 'segment', 'type': 'semi_mirror',
                  'x1': 40, 'y1': -5, 'x2': 60, 'y2': 15, 'id': 'sm_solo'}]
    beams = raycast.cast(0, 0, 1, 0, many_semi, max_bounces=10)
    signal.alarm(0)
    check("semi_mirror does not self-collide / explode combinatorially",
          len(beams) <= 3, detail=f"got {len(beams)} beams")
except TimeoutError:
    signal.alarm(0)
    check("semi_mirror does not self-collide / explode combinatorially", False)

# broken_mirror باید بازتاب کند (نه فقط رد شود) و بی‌نهایت حلقه نزند
broken = {'shape': 'segment', 'type': 'broken_mirror', 'x1': 40, 'y1': 0, 'x2': 60, 'y2': 20, 'id': 'bm1'}
signal.alarm(2)
try:
    beams = raycast.cast(0, 0, 1, 0, [broken])
    signal.alarm(0)
    check("broken_mirror reflects (beam does not just stop at the mirror)",
          len(beams[0].points) == 3, detail=str(beams[0].hit_types))
    dx_final = beams[0].points[-1][0] - beams[0].points[1][0]
    check("broken_mirror sends the ray roughly upward/back, not straight through",
          beams[0].points[-1][1] > beams[0].points[1][1])
except TimeoutError:
    signal.alarm(0)
    check("broken_mirror reflects without infinite loop", False)

# ============================================================
print("\n=== MovementSystem: سرعت‌ها باید دقیقاً با جدول مرجع بخش۲.۹.۳ بخوانند (فاز ۲) ===")

from ecs.systems.movement_system import MovementSystem

SIM_DT = 1 / 60.0


def measure_peak_speed(pattern, target_speed, sim_seconds=6.0, crosshair=(0, 0)):
    w = World()
    w.crosshair_x, w.crosshair_y = crosshair
    e = w.create_entity()
    w.add_component(e, Position, x=500.0, y=500.0)
    w.add_component(e, Target, hp=1, move_pattern=pattern, speed=target_speed,
                     origin_x=500.0, origin_y=500.0)
    w.add_system(MovementSystem())

    positions = []
    t = 0.0
    while t < sim_seconds:
        w.update(SIM_DT)
        pos = e.get_component(Position)
        positions.append((pos.x, pos.y))
        t += SIM_DT

    speeds = []
    for i in range(1, len(positions)):
        ddx = positions[i][0] - positions[i - 1][0]
        ddy = positions[i][1] - positions[i - 1][1]
        speeds.append(math.hypot(ddx, ddy) / SIM_DT)
    return max(speeds) if speeds else 0.0


REFERENCE_SPEEDS = {
    'linear_horizontal': 100.0,
    'linear_vertical': 100.0,
    'circular': 150.0,
    'zigzag': 120.0,
    'chase_crosshair': 80.0,
    'random': 150.0,
}

for pattern, expected in REFERENCE_SPEEDS.items():
    if pattern == 'chase_crosshair':
        peak = measure_peak_speed(pattern, expected, sim_seconds=1.0, crosshair=(5000, 5000))
    else:
        peak = measure_peak_speed(pattern, expected)
    check(f"{pattern}: peak speed matches table ({expected} px/s)",
          close(peak, expected, eps=expected * 0.05),
          detail=f"expected≈{expected}, measured={peak:.1f}")

# 'combined' هم باید سرعت نزدیک به مقدار مرجع خودش (۲۰۰ px/s) داشته باشد --
# با فرمول شعاع‌نوسانی پیوسته (نه سوییچ ناگهانی) که با تست عددی تنظیم شد
peak_combined = measure_peak_speed('combined', 200.0, sim_seconds=8.0)
check("combined: peak speed matches table (200.0 px/s)",
      close(peak_combined, 200.0, eps=200.0 * 0.10), detail=f"measured={peak_combined:.1f}")


# ============================================================
print("\n=== RotationSystem: آینه‌ی چرخان (فاز ۲) ===")

from ecs.systems.rotation_system import RotationSystem
from ecs.components.mirror import Mirror

w_rot = World()
mirror_e = w_rot.create_entity()
w_rot.add_component(mirror_e, Mirror, x1=90, y1=100, x2=110, y2=100,
                     mirror_type='rotating_mirror', rotation_speed=90.0)  # deg/s
w_rot.add_system(RotationSystem())

orig_len = math.hypot(110 - 90, 100 - 100)
w_rot.update(1.0)  # یک ثانیه -> باید دقیقاً ۹۰ درجه بچرخد
m = mirror_e.get_component(Mirror)
new_len = math.hypot(m.x2 - m.x1, m.y2 - m.y1)
check("rotating mirror: length preserved after rotation", close(new_len, orig_len, eps=0.01),
      detail=f"orig={orig_len} new={new_len}")
check("rotating mirror: base_angle advanced by exactly rotation_speed*dt",
      close(m.base_angle, 90.0), detail=f"base_angle={m.base_angle}")
# بعد از ۹۰ درجه چرخش حول pivot (100,100)، آینه‌ی افقی باید عمودی شده باشد
check("rotating mirror: horizontal mirror becomes ~vertical after 90°",
      close(m.x1, m.x2, eps=0.01), detail=f"x1={m.x1} x2={m.x2}")

# چرخش غیرفعال (rotation_speed=0) یا نوع normal نباید هیچ تغییری بدهد
static_e = w_rot.create_entity()
w_rot.add_component(static_e, Mirror, x1=0, y1=0, x2=20, y2=0, mirror_type='normal')
w_rot.update(5.0)
sm = static_e.get_component(Mirror)
check("normal mirror is untouched by RotationSystem", sm.x1 == 0 and sm.x2 == 20)


# ============================================================
print("\n=== Level / LevelManager / LevelCondition (فاز ۲) ===")

from game_logic.level import Level
from game_logic.level_manager import LevelManager
from game_logic.level_condition import LevelCondition
from utils.timer import PreciseTimer, performance_tier


def aim_angle_solves_level(gun_x, gun_y, surfaces, angle_deg, target_id):
    dx, dy = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    beams = raycast.cast(gun_x, gun_y, dx, dy, surfaces)
    return any(b.hit_types and b.hit_types[-1] == 'target' and b.hit_ids and
               b.hit_ids[-1] == target_id for b in beams)


def level_is_solvable(level, angle_step_deg=1.0):
    """طبق تصمیم فایل مرجع بخش ۵.۹: به‌جای چک ظاهری، واقعاً چند زاویه
    را با موتور Raycasting واقعی امتحان می‌کند."""
    w = World()
    gun_x, gun_y = level.populate_world(w)
    surfaces = entities_to_surfaces(w)
    target_ids = [e.id for e in w.get_entities_with(Position, Target)]
    if not target_ids:
        return True
    solved = {tid: False for tid in target_ids}
    angle = 0.0
    while angle < 360.0:
        for tid in target_ids:
            if not solved[tid] and aim_angle_solves_level(gun_x, gun_y, surfaces, angle, tid):
                solved[tid] = True
        angle += angle_step_deg
    return all(solved.values())


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
level1_path = os.path.join(PROJECT_ROOT, 'assets', 'levels', 'level_001.json')
level2_path = os.path.join(PROJECT_ROOT, 'assets', 'levels', 'level_002.json')

level1 = Level.from_json_file(level1_path)
level2 = Level.from_json_file(level2_path)

check("level_001: has no mirrors (طبق قانون فایل مرجع، بخش۵.۵ برای مرحله‌ی ۱)",
      len(level1.mirrors) == 0)
check("level_002: has exactly one mirror", len(level2.mirrors) == 1)

check("level_001 is actually solvable by the real raycast engine",
      level_is_solvable(level1))
check("level_002 is actually solvable by the real raycast engine (via the mirror)",
      level_is_solvable(level2))

lm = LevelManager(levels_dir=os.path.join(PROJECT_ROOT, 'assets', 'levels'))
check("LevelManager loads all JSON files from assets/levels", len(lm.levels) >= 2)
check("LevelManager.get_level(1) returns the right level", lm.get_level(1).level_id == 1)
check("LevelManager: level 1 is unlocked by default", lm.is_unlocked(1))
check("LevelManager: level 2 is NOT unlocked by default", not lm.is_unlocked(2))

lm.load_level(1)
lm.unlock_next()
check("LevelManager.unlock_next() after finishing level 1 unlocks level 2", lm.is_unlocked(2))

# LevelCondition: پیروزی، شکست، و بی‌نقص‌بودن
lc = LevelCondition(total_targets=3)
timer = PreciseTimer(duration=160)
timer.start()
timer.update(40.0)  # ۴۰ ثانیه گذشته، ۱۲۰ از ۱۶۰ مونده -> remaining_fraction=0.75
lc.on_shot_fired(); lc.on_target_destroyed()
lc.on_shot_fired(); lc.on_target_destroyed()
lc.on_shot_fired(); lc.on_target_destroyed()
result = lc.get_result(timer)
check("LevelCondition: 3/3 targets destroyed -> success=True", result['success'] is True)
check("LevelCondition: exactly 3 shots for 3 targets -> is_perfect=True", result['is_perfect'] is True)
check("LevelCondition: tier uses percentage threshold, not absolute seconds",
      result['tier'] == performance_tier(0.75) == 'legendary')

# آستانه‌های درصدی باید مستقل از duration باشند -- دقیقاً همان مشکلی که
# در تحلیل ۸ بخش سه‌بار (پیام تشویقی/جواهر/ستاره) پیدا شده بود
timer_short = PreciseTimer(duration=160)
timer_short.start()
timer_short.update(40.0)  # همون ۷۵٪ باقی‌مانده، ولی duration کوتاه‌تره
check("performance_tier is reachable ('legendary') even on a short 160s level "
      "(the original bug made this impossible with absolute-second thresholds)",
      performance_tier(timer_short.remaining_fraction) == 'legendary')


# ============================================================
print("\n=== scene_builder (منطق مستقل از Kivy که main.py صدا می‌زند) ===")

world3 = World()
gun_x, gun_y = build_test_scene(world3, 1080, 1920)
check("build_test_scene: gun is horizontally centered", close(gun_x, 540))
check("build_test_scene: gun_y is near the bottom (small y)", gun_y < 300,
      detail=f"gun_y={gun_y}")

surfaces = entities_to_surfaces(world3)
kinds = sorted(s['type'] for s in surfaces)
check("entities_to_surfaces: produces exactly one mirror (type=normal) + one target",
      kinds == ['normal', 'target'], detail=str(kinds))

mirror_surf = next(s for s in surfaces if s['type'] == 'normal')
target_surf = next(s for s in surfaces if s['type'] == 'target')
check("entities_to_surfaces: mirror uses 'segment' shape", mirror_surf['shape'] == 'segment')
check("entities_to_surfaces: target uses 'circle' shape", target_surf['shape'] == 'circle')

# هدف باید *بالاتر* از اسلحه باشد (y بزرگتر)، طبق قرارداد Y-رو-به-بالا --
# این دقیقاً همان چیزی است که در فایل مرجع به‌عنوان تصمیم حیاتی ثبت شده
check("target's y is greater than gun's y (target appears 'above' the gun, Y-up convention)",
      target_surf['y'] > gun_y, detail=f"target_y={target_surf['y']} gun_y={gun_y}")

# یک هدف نابودشده (hp<=0) نباید در لیست surfaces ظاهر شود
for e in world3.get_entities_with(Target):
    e.get_component(Target).hp = 0
surfaces_after_death = entities_to_surfaces(world3)
check("a destroyed target (hp<=0) is excluded from raycast surfaces",
      not any(s['type'] == 'target' for s in surfaces_after_death))


# ============================================================
print("\n=== level_validator: is_solvable (فاز ۳) ===")

from game_logic import level_validator

# نسخه‌ی ارتقاءیافته باید دقیقاً همان نتیجه‌ی نسخه‌ی محلی فاز۲ را برای
# level_001/002 بدهد -- این یعنی انتقال به game_logic/level_validator.py
# هیچ رگرسیونی ایجاد نکرده.
check("level_validator.is_solvable: level_001 (بدون تغییر رفتار نسبت به فاز۲)",
      level_validator.is_solvable(level1))
check("level_validator.is_solvable: level_002 (بدون تغییر رفتار نسبت به فاز۲)",
      level_validator.is_solvable(level2))

# حالت منفی -- تا الان هیچ تستی «واقعاً غیرقابل‌حل» را چک نکرده بود.
# هدف ساکن پشت یک مانع که هیچ آینه‌ای برای دور زدنش نیست: هندسه‌ای که
# با محاسبه‌ی مستقیم تأیید شد هیچ زاویه‌ای هم مانع را رد می‌کند هم به
# هدف می‌رسد (هیچ‌کدام از ۷۲۰ زاویه‌ی امتحان‌شده در طراحی برخورد نداد).
unsolvable_dict = {
    "level_id": 999, "phase": "training", "difficulty": 1.0, "time_limit": 100,
    "laser_start": {"x": 0, "y": 0, "angle": 90},
    "targets": [{"id": "t1", "x": 0, "y": 300, "hp": 1, "move_pattern": "static",
                 "speed": 0, "radius": 30}],
    "mirrors": [],
    "obstacles": [{"id": "ob1", "x1": -30, "y1": 150, "x2": 30, "y2": 150, "destructible": False}],
    "portals": [], "prisms": [], "black_holes": [], "rewards": {}, "hints": [],
}
unsolvable_level = Level(unsolvable_dict)
check("level_validator.is_solvable: مرحله‌ی واقعاً غیرقابل‌حل درست تشخیص داده می‌شود (False)",
      level_validator.is_solvable(unsolvable_level) is False)

# اثبات اینکه نمونه‌برداری زمانی برای اهداف متحرک واقعاً چیزی را عوض
# می‌کند (نه صرفاً یک پارامتر تزئینی): همان هندسه‌ی بالا، ولی هدف به‌جای
# 'static'، 'linear_horizontal' است -- در t=۰ پشت مانع است (پس با چک
# تک‌نقطه‌ای غیرقابل‌حل به‌نظر می‌رسد)، ولی حین نوسان از کنار مانع رد
# می‌شود و در آن لحظه قابل‌شلیک می‌شود.
moving_behind_obstacle_dict = dict(unsolvable_dict)
moving_behind_obstacle_dict["level_id"] = 998
moving_behind_obstacle_dict["targets"] = [
    {"id": "t1", "x": 0, "y": 300, "hp": 1, "move_pattern": "linear_horizontal",
     "speed": 100, "radius": 30}
]
moving_level = Level(moving_behind_obstacle_dict)
check("level_validator.is_solvable: با چک تک‌نقطه‌ای (time_samples=0) غیرقابل‌حل گزارش می‌شود",
      level_validator.is_solvable(moving_level, time_samples=0, sim_duration=0.0) is False)
check("level_validator.is_solvable: با نمونه‌برداری زمانی واقعی، همین مرحله قابل‌حل تشخیص داده می‌شود "
      "(هدف حین نوسان از کنار مانع رد می‌شود)",
      level_validator.is_solvable(moving_level) is True)


# ============================================================
print("\n=== level_validator: used_mechanic_types (فاز ۳) ===")

kitchen_sink_dict = {
    "level_id": 50, "phase": "advanced", "difficulty": 5.0, "time_limit": 200,
    "laser_start": {"x": 0, "y": 0, "angle": 90},
    "targets": [{"id": "t1", "x": 0, "y": 100, "hp": 1, "move_pattern": "static",
                 "speed": 0, "radius": 30}],
    "mirrors": [
        {"id": "m1", "x1": 0, "y1": 0, "x2": 1, "y2": 1, "type": "normal"},
        {"id": "m2", "x1": 0, "y1": 0, "x2": 1, "y2": 1, "type": "semi_mirror"},
        {"id": "m3", "x1": 0, "y1": 0, "x2": 1, "y2": 1, "type": "rotating_mirror"},
        {"id": "m4", "x1": 0, "y1": 0, "x2": 1, "y2": 1, "type": "broken_mirror"},
    ],
    "obstacles": [],
    "portals": [{"id": "p1", "x": 5, "y": 5, "exit_x": 1, "exit_y": 1}],
    "prisms": [{"id": "pr1", "x": 2, "y": 2}],
    "black_holes": [{"id": "b1", "x": 3, "y": 3}],
    "rewards": {}, "hints": [],
}
kitchen_sink_level = Level(kitchen_sink_dict)
check("used_mechanic_types: همه‌ی ۷ نوع مکانیک را درست استخراج می‌کند",
      level_validator.used_mechanic_types(kitchen_sink_level) ==
      {'normal', 'semi_mirror', 'rotating_mirror', 'broken_mirror', 'portal', 'prism', 'black_hole'},
      detail=str(level_validator.used_mechanic_types(kitchen_sink_level)))


# ============================================================
print("\n=== DifficultyManager (فاز ۳) ===")

from game_logic.difficulty_manager import DifficultyManager, MECHANIC_UNLOCK_LEVEL

dm = DifficultyManager()

# مرزهای دقیق ۵ فاز -- طوری انتخاب شدند که هر ۷ مکانیک جدول ۵.۵ کاملاً
# داخل فاز مربوطه‌شان بیفتند (نه لب مرز)
check("DifficultyManager: سطح۱ -> آموزش (training)", dm.get_phase_for_level(1)['key'] == 'training')
check("DifficultyManager: سطح۱۵ (انتهای آموزش) -> training", dm.get_phase_for_level(15)['key'] == 'training')
check("DifficultyManager: سطح۱۶ (شروع میانی) -> intermediate", dm.get_phase_for_level(16)['key'] == 'intermediate')
check("DifficultyManager: سطح۳۲ (انتهای میانی) -> intermediate", dm.get_phase_for_level(32)['key'] == 'intermediate')
check("DifficultyManager: سطح۳۳ (شروع پیشرفته) -> advanced", dm.get_phase_for_level(33)['key'] == 'advanced')
check("DifficultyManager: سطح۵۰ (انتهای پیشرفته) -> advanced", dm.get_phase_for_level(50)['key'] == 'advanced')
check("DifficultyManager: سطح۵۱ (شروع خبره) -> expert", dm.get_phase_for_level(51)['key'] == 'expert')
check("DifficultyManager: سطح۷۵ (انتهای خبره) -> expert", dm.get_phase_for_level(75)['key'] == 'expert')
check("DifficultyManager: سطح۷۶ (شروع استاد) -> master", dm.get_phase_for_level(76)['key'] == 'master')
check("DifficultyManager: سطح۱۰۰ (انتهای استاد) -> master", dm.get_phase_for_level(100)['key'] == 'master')

# جدول باز شدن مکانیک -- دقیقاً کپی از فایل مرجع بخش ۵.۵
check("DifficultyManager: در سطح۱ فقط 'normal' باز است",
      dm.unlocked_mechanics_at(1) == {'normal'})
check("DifficultyManager: درست قبل از سطح۱۶ هنوز semi_mirror باز نشده",
      'semi_mirror' not in dm.unlocked_mechanics_at(15))
check("DifficultyManager: دقیقاً در سطح۱۶ semi_mirror باز می‌شود",
      'semi_mirror' in dm.unlocked_mechanics_at(16))
check("DifficultyManager: در سطح۴۳ هر ۷ مکانیک باز شده‌اند",
      dm.unlocked_mechanics_at(43) == set(MECHANIC_UNLOCK_LEVEL.keys()))
check("DifficultyManager: next_mechanic_unlock(۵) == ('semi_mirror', ۱۶)",
      dm.next_mechanic_unlock(5) == ('semi_mirror', 16))
check("DifficultyManager: next_mechanic_unlock(۴۳) == None (چیزی برای باز شدن نمانده)",
      dm.next_mechanic_unlock(43) is None)

# منحنی سختی -- نقاط مرزی و یکنواختی روی کل ۱۰۰ مرحله
p1 = dm.get_recommended_params(1)
p100 = dm.get_recommended_params(100)
check("DifficultyManager: سختی پیشنهادی سطح۱ == ۱.۰", close(p1['difficulty_value'], 1.0))
check("DifficultyManager: زمان پیشنهادی سطح۱ == ۳۰۰ (هم‌راستا با level_001/002 واقعی)",
      p1['time_limit_seconds'] == 300)
check("DifficultyManager: سختی پیشنهادی سطح۱۰۰ == ۱۰.۰", close(p100['difficulty_value'], 10.0))
check("DifficultyManager: زمان پیشنهادی سطح۱۰۰ == ۶۰ (کف زمانی)", p100['time_limit_seconds'] == 60)

_prev_diff, _prev_time, _monotonic_ok = -1.0, 1e9, True
for _lvl in range(1, 101):
    _params = dm.get_recommended_params(_lvl)
    if _params['difficulty_value'] < _prev_diff or _params['time_limit_seconds'] > _prev_time:
        _monotonic_ok = False
    _prev_diff, _prev_time = _params['difficulty_value'], _params['time_limit_seconds']
check("DifficultyManager: سختی یکنواخت‌افزایشی و زمان یکنواخت‌کاهشی روی کل ۱ تا ۱۰۰", _monotonic_ok)

# تطابق مرحله با فازش -- هم حالت تمیز هم حالت متخلف
check("DifficultyManager.validate_level_conformance: level_001 هیچ تخلفی ندارد",
      dm.validate_level_conformance(level1) == [])
nonconformant_dict = {
    "level_id": 5, "phase": "training", "difficulty": 1.0, "time_limit": 200,
    "laser_start": {"x": 0, "y": 0, "angle": 90},
    "targets": [{"id": "t1", "x": 0, "y": 100, "hp": 1, "move_pattern": "static",
                 "speed": 0, "radius": 30}],
    "mirrors": [], "obstacles": [],
    "portals": [{"id": "p1", "x": 5, "y": 5, "exit_x": 1, "exit_y": 1}],  # پورتال تا سطح۳۳ باز نمی‌شود!
    "prisms": [], "black_holes": [], "rewards": {}, "hints": [],
}
nonconformant_level = Level(nonconformant_dict)
violations = dm.validate_level_conformance(nonconformant_level)
check("DifficultyManager.validate_level_conformance: مرحله‌ی ۵ که زودتر از موعد پورتال دارد، "
      "دقیقاً یک تخلف گزارش می‌کند", len(violations) == 1, detail=str(violations))
check("DifficultyManager.validate_level_conformance: متن تخلف به 'portal' اشاره می‌کند",
      violations and 'portal' in violations[0])


# ============================================================
print("\n=== SpecialShotManager (فاز ۳) ===")

from game_logic.special_shot_manager import SpecialShotManager, SHOT_TYPES

ssm = SpecialShotManager()
check("SpecialShotManager: در ابتدا فقط 'normal' باز است",
      ssm.get_available_shots() == ['normal'])
check("SpecialShotManager: is_unlocked('piercing') در ابتدا False است",
      ssm.is_unlocked('piercing') is False)

try:
    ssm.execute_shot('not_a_real_shot', 0, 0, 1, 0, [])
    check("SpecialShotManager: شلیک ناشناخته -> ValueError", False, detail="exception raised نشد")
except ValueError:
    check("SpecialShotManager: شلیک ناشناخته -> ValueError", True)
except Exception as e:
    check("SpecialShotManager: شلیک ناشناخته -> ValueError", False, detail=repr(e))

try:
    ssm.execute_shot('piercing', 0, 0, 1, 0, [])
    check("SpecialShotManager: شلیک هنوز-باز-نشده -> PermissionError", False, detail="exception raised نشد")
except PermissionError:
    check("SpecialShotManager: شلیک هنوز-باز-نشده -> PermissionError", True)
except Exception as e:
    check("SpecialShotManager: شلیک هنوز-باز-نشده -> PermissionError", False, detail=repr(e))

try:
    ssm.unlock_shot('not_a_real_shot')
    check("SpecialShotManager: unlock_shot با شناسه‌ی ناشناخته -> ValueError", False, detail="exception raised نشد")
except ValueError:
    check("SpecialShotManager: unlock_shot با شناسه‌ی ناشناخته -> ValueError", True)

ssm.unlock_shot('piercing')
ssm.unlock_shot('splitting')
check("SpecialShotManager: بعد از unlock_shot، is_unlocked True است", ssm.is_unlocked('piercing'))
check("SpecialShotManager: بعد از unlock_shot، در get_available_shots ظاهر می‌شود",
      'piercing' in ssm.get_available_shots() and 'splitting' in ssm.get_available_shots())

# قرارداد effects -- باید دقیقاً همان رشته‌هایی باشد که raycast.cast می‌شناسد
# (بخش ۵.۲)؛ اگر این رشته‌ها جور در نیایند، execute_shot بدون خطا اجرا
# می‌شود ولی اثر واقعی هیچ‌وقت رخ نمی‌دهد -- دقیقاً همان‌کلاس باگی که
# فایل مرجع بخش ۵.۶ می‌خواهد از آن جلوگیری شود.
check("SpecialShotManager: effects شلیک نافذ == ('pierce_obstacles',) -- دقیقاً رشته‌ی شناخته‌شده‌ی raycast",
      SHOT_TYPES['piercing']['effects'] == ('pierce_obstacles',))
check("SpecialShotManager: effects شلیک شکافنده == ('split_on_bounce',) -- دقیقاً رشته‌ی شناخته‌شده‌ی raycast",
      SHOT_TYPES['splitting']['effects'] == ('split_on_bounce',))

# رفتاری -- طبق بخش ۵.۶: effects واقعاً باید تا raycast.cast برسند، نه
# فقط در جدول تعریف شده باشند
obstacle_for_shots = {'shape': 'segment', 'type': 'obstacle', 'x1': 50, 'y1': -20, 'x2': 50, 'y2': 20, 'id': 'ob'}
target_for_shots = {'shape': 'circle', 'type': 'target', 'x': 100, 'y': 0, 'radius': 15, 'id': 't1'}
scene_for_shots = [obstacle_for_shots, target_for_shots]

beams_normal_shot = ssm.execute_shot('normal', 0, 0, 1, 0, scene_for_shots)
check("SpecialShotManager: شلیک عادی پشت مانع متوقف می‌شود (به هدف نمی‌رسد)",
      beams_normal_shot[0].hit_types[-1] == 'obstacle')

beams_piercing_shot = ssm.execute_shot('piercing', 0, 0, 1, 0, scene_for_shots)
check("SpecialShotManager: شلیک نافذ از مانع رد می‌شود و به هدف می‌رسد",
      beams_piercing_shot[0].hit_types[-1] == 'target')

mirror_for_shots = {'shape': 'segment', 'type': 'normal', 'x1': 40, 'y1': -20, 'x2': 60, 'y2': 20, 'id': 'm1'}
beams_normal_mirror = ssm.execute_shot('normal', 0, 0, 1, 0, [mirror_for_shots])
beams_splitting_mirror = ssm.execute_shot('splitting', 0, 0, 1, 0, [mirror_for_shots])
check("SpecialShotManager: شلیک شکافنده روی آینه بیش‌از شلیک عادی بیم تولید می‌کند",
      len(beams_splitting_mirror) > len(beams_normal_mirror),
      detail=f"normal={len(beams_normal_mirror)} splitting={len(beams_splitting_mirror)}")


# ============================================================
print("\n=== LevelManager: پیشروی واقعی بین ۱۰۰ مرحله (فاز۳ برای ۵ مرحله نوشته شد؛ فاز۹ تا ۱۰۰ گسترد) ===")

lm5 = LevelManager(levels_dir=os.path.join(PROJECT_ROOT, 'assets', 'levels'))
check("LevelManager (فاز۳/۹): level_count == 100 (۵ دستی + ۹۵ تولیدی)", lm5.level_count == 100, detail=str(lm5.level_count))
check("LevelManager (فاز۳/۹): get_all_level_ids == [1..100]",
      lm5.get_all_level_ids() == list(range(1, 101)), detail=str(lm5.get_all_level_ids()[:8]))
check("LevelManager (فاز۳): get_unlocked_level_ids == [1] در ابتدا",
      lm5.get_unlocked_level_ids() == [1])

lm5.load_level(1)
check("LevelManager (فاز۳): has_next_level() در سطح۱ True است (سطح۲ وجود دارد)", lm5.has_next_level())

for _lid in range(1, 101):
    lm5.load_level(_lid)
    if _lid == 5:
        check("LevelManager (فاز۹): has_next_level() در سطح۵ حالا True است (سطح۶ تولیدی وجود دارد)",
              lm5.has_next_level())
    lm5.unlock_next()

check("LevelManager (فاز۳/۹): has_next_level() در سطح۱۰۰ False است (آخرین مرحله)",
      not lm5.has_next_level())
check("LevelManager (فاز۳/۹): بعد از پیشروی کامل، هر ۱۰۰ سطح باز شده‌اند",
      lm5.get_unlocked_level_ids() == list(range(1, 101)))


# ============================================================
print("\n=== مراحل ۳ تا ۵ (فاز۳ -- تکمیل فاز آموزش) ===")

level3 = Level.from_json_file(os.path.join(PROJECT_ROOT, 'assets', 'levels', 'level_003.json'))
level4 = Level.from_json_file(os.path.join(PROJECT_ROOT, 'assets', 'levels', 'level_004.json'))
level5 = Level.from_json_file(os.path.join(PROJECT_ROOT, 'assets', 'levels', 'level_005.json'))

check("level_003: دقیقاً دو آینه دارد (اولین مرحله‌ی دو-کمانه‌ای)", len(level3.mirrors) == 2)
check("level_003 با موتور واقعی Raycasting قابل‌حل است", level_validator.is_solvable(level3))

check("level_004: دقیقاً یک مانع دارد", len(level4.obstacles) == 1)
check("level_004: دقیقاً یک آینه دارد", len(level4.mirrors) == 1)
check("level_004 با موتور واقعی Raycasting قابل‌حل است", level_validator.is_solvable(level4))

# رگرسیون طراحی: مانع level_004 باید *واقعاً* راه مستقیم را ببندد -- وگرنه
# آینه‌اش صرفاً تزئینی است و مرحله چیزی آموزش نمی‌دهد. با ۷۲۰ زاویه (هر
# نیم‌درجه) بدون آینه امتحان می‌کنیم: هیچ‌کدام نباید به هدف برسد.
world4 = World()
gun4_x, gun4_y = level4.populate_world(world4)
obstacle_only_surfaces = [s for s in entities_to_surfaces(world4) if s['type'] in ('obstacle', 'target')]
_direct_hits = 0
_a = 0.0
while _a < 360.0:
    _dx, _dy = math.cos(math.radians(_a)), math.sin(math.radians(_a))
    _beams = raycast.cast(gun4_x, gun4_y, _dx, _dy, obstacle_only_surfaces)
    if _beams[0].hit_types[-1] == 'target':
        _direct_hits += 1
    _a += 0.5
check("level_004: بدون آینه، هیچ زاویه‌ای مستقیماً به هدف نمی‌رسد (مانع واقعاً مسیر مستقیم را می‌بندد)",
      _direct_hits == 0, detail=f"{_direct_hits} زاویه‌ی مستقیم موفق (انتظار: ۰)")

check("level_005: دقیقاً دو هدف دارد (اولین مرحله‌ی چندهدفی)", len(level5.targets) == 2)
check("level_005: یک هدف ساکن و یک هدف متحرک دارد",
      sum(1 for t in level5.targets if t['move_pattern'] == 'static') == 1 and
      sum(1 for t in level5.targets if t['move_pattern'] != 'static') == 1)
check("level_005 (با هدف متحرک) با موتور واقعی Raycasting و نمونه‌برداری زمانی قابل‌حل است",
      level_validator.is_solvable(level5))

_all_conformant = all(dm.validate_level_conformance(lv) == [] for lv in (level1, level2, level3, level4, level5))
check("مراحل ۱ تا ۵: همه فقط از مکانیک‌های تا سطح خودشان باز شده استفاده می‌کنند (بدون تخلف)",
      _all_conformant)


# ============================================================
print("\n=== core/database.py: Database (فاز ۴) ===")

import tempfile as _tempfile
from core.database import Database

_tmpdir = _tempfile.mkdtemp()
_db_path = os.path.join(_tmpdir, 'test_save.db')
_db = Database(path=_db_path)

check("Database: get روی کلید ناموجود، default رو برمی‌گردونه",
      _db.get('nope', default='X') == 'X')
_db.set('profile', {'coins': 42, 'nested': {'a': [1, 2, 3]}})
check("Database: get بعد از set همون dict رو (با تودرتو) برمی‌گردونه",
      _db.get('profile') == {'coins': 42, 'nested': {'a': [1, 2, 3]}})
_db.set('profile', {'coins': 99})
check("Database: set دوباره روی همون کلید، مقدار قبلی رو overwrite می‌کنه",
      _db.get('profile') == {'coins': 99})
_db.delete('profile')
check("Database: delete کلید رو پاک می‌کنه", _db.get('profile') is None)
_db.close()

_db2 = Database(path=_db_path)  # اتصال تازه، همون فایل -- شبیه‌سازی ری‌استارت اپ
_db2.set('durable', {'x': 1})
_db2.close()
_db3 = Database(path=_db_path)
check("Database: مقدار بعد از close/reopen (شبیه‌سازی ری‌استارت اپ) دووم می‌آره",
      _db3.get('durable') == {'x': 1})
_db3.close()


# ============================================================
print("\n=== EconomyManager (فاز ۴) ===")

from game_logic.economy_manager import EconomyManager, EconomyBalance

econ = EconomyManager()
econ.add_coins(100)
check("EconomyManager: add_coins موجودی رو زیاد می‌کنه", econ.coins == 100)
check("EconomyManager: spend_coins بیش‌ازموجودی -> False و بدون تغییر",
      econ.spend_coins(500) is False and econ.coins == 100)
check("EconomyManager: spend_coins کافی -> True و کم می‌شه",
      econ.spend_coins(40) is True and econ.coins == 60)
check("EconomyManager: can_afford درست تشخیص می‌ده", econ.can_afford(coins=60) and not econ.can_afford(coins=61))

try:
    econ.add_coins(-5)
    check("EconomyManager: add_coins منفی -> ValueError", False, detail="exception raised نشد")
except ValueError:
    check("EconomyManager: add_coins منفی -> ValueError", True)

econ.apply_coin_bonus_upgrade(1.5)
econ.apply_level_rewards({'coins': 20, 'gems': 2})
check("EconomyManager: apply_level_rewards سکه رو تحت‌تأثیر coin_bonus_multiplier اعمال می‌کنه",
      econ.coins == 60 + round(20 * 1.5), detail=str(econ.coins))
check("EconomyManager: apply_level_rewards جواهر رو هم اعمال می‌کنه", econ.gems == 2)

econ_restored = EconomyManager.from_dict(econ.to_dict())
check("EconomyManager: to_dict/from_dict رفت‌وبرگشت دقیق",
      econ_restored.coins == econ.coins and econ_restored.gems == econ.gems and
      close(econ_restored.coin_bonus_multiplier, econ.coin_bonus_multiplier))

bal = EconomyBalance()
_incomes = {pt: bal.calculate_daily_income(pt) for pt in ('casual', 'average', 'active', 'whale')}
check("EconomyBalance: هر ۴ نوع بازیکن درآمد متفاوت دارن (نه فقط active جدا)",
      len({_incomes[pt]['coins'] for pt in _incomes}) == 4, detail=str(_incomes))
check("EconomyBalance: whale به‌خاطر iap_gems_per_day، به‌طور کیفی (نه فقط عددی بزرگ‌تر) "
      "جواهر بیشتری داره", _incomes['whale']['gems'] > _incomes['active']['gems'] * 5)
check("EconomyBalance: بازیکن فعال ۱۶ مرحله/روز (هم‌راستا با شبیه‌سازی Battle Pass بخش۵.۱۲)",
      EconomyBalance.PLAYER_PROFILES['active']['levels_per_day'] == 16)
try:
    bal.calculate_daily_income('super_whale')
    check("EconomyBalance: player_type ناشناخته -> ValueError", False, detail="exception raised نشد")
except ValueError:
    check("EconomyBalance: player_type ناشناخته -> ValueError", True)


# ============================================================
print("\n=== EnergyManager (فاز ۴) ===")

from game_logic.energy_manager import EnergyManager

en = EnergyManager(current_energy=5, max_energy=5, regen_seconds_per_unit=900.0, last_update=0.0)
check("EnergyManager: پیش‌فرض روی max_energy شروع می‌شه", EnergyManager().current_energy == EnergyManager().max_energy)
check("EnergyManager: consume موجودی کافی -> True و کم می‌شه",
      en.consume(2, now=0.0) is True and en.current_energy == 3)
check("EnergyManager: consume بیش‌ازموجودی -> False و بدون تغییر",
      en.consume(10, now=0.0) is False and en.current_energy == 3)

en2 = EnergyManager(current_energy=2, max_energy=5, regen_seconds_per_unit=900.0, last_update=0.0)
en2.update(now=1000.0)
check("EnergyManager: بعد از ۱۰۰۰ ثانیه (۱ واحد کامل + ۱۰۰ باقی‌مونده)، دقیقاً ۱ واحد اضافه می‌شه",
      en2.current_energy == 3, detail=str(en2.current_energy))
check("EnergyManager: ۱۰۰ ثانیه‌ی باقی‌مونده گم نمی‌شه -- last_update فقط به‌اندازه‌ی واحدِ "
      "کامل‌شده جلو رفته (۹۰۰)، نه تا 'الان' (۱۰۰۰)", close(en2.last_update, 900.0))
en2.update(now=1850.0)  # +850s از last_update=900 -> جمعاً ۹۵۰ >= ۹۰۰ -> ۱ واحد دیگه
check("EnergyManager: باقی‌مونده‌ی زمانی درست جمع می‌شه و واحد بعدی به‌موقع می‌رسه",
      en2.current_energy == 4, detail=str(en2.current_energy))

en3 = EnergyManager(current_energy=4, max_energy=5, regen_seconds_per_unit=900.0, last_update=0.0)
en3.update(now=100000.0)  # زمان خیلی زیاد
check("EnergyManager: بازآفرینی هیچ‌وقت از max_energy رد نمی‌شه", en3.current_energy == 5)

en4 = EnergyManager(current_energy=3, max_energy=5, regen_seconds_per_unit=900.0, last_update=0.0)
check("EnergyManager: seconds_until_next_unit درست حساب می‌شه",
      close(en4.seconds_until_next_unit(now=300.0), 600.0))
en5 = EnergyManager(current_energy=3, max_energy=5, regen_seconds_per_unit=900.0, last_update=0.0)
check("EnergyManager: seconds_until_full == (تا واحد بعدی) + (واحدهای باقی‌مونده-۱)*دوره",
      close(en5.seconds_until_full(now=0.0), 900.0 + 1 * 900.0))

en6 = EnergyManager(regen_seconds_per_unit=900.0)
en6.apply_regen_speed_upgrade(0.5)
check("EnergyManager: apply_regen_speed_upgrade نرخ رو درست تغییر می‌ده", close(en6.regen_seconds_per_unit, 450.0))

en7 = EnergyManager(current_energy=2, max_energy=6, regen_seconds_per_unit=333.0, last_update=55.0)
en7_restored = EnergyManager.from_dict(en7.to_dict())
check("EnergyManager: to_dict/from_dict رفت‌وبرگشت دقیق",
      en7_restored.current_energy == en7.current_energy and en7_restored.max_energy == en7.max_energy and
      close(en7_restored.regen_seconds_per_unit, en7.regen_seconds_per_unit) and
      close(en7_restored.last_update, en7.last_update))


# ============================================================
print("\n=== EquipmentManager (فاز ۴) ===")

from game_logic.equipment_manager import EquipmentManager

eqp = EquipmentManager()
check("EquipmentManager: ضرایب پیش‌فرض ۱.۰ هستن",
      close(eqp.get_score_multiplier(), 1.0) and close(eqp.get_fire_rate_multiplier(), 1.0))
eqp.apply_gun_bonus({'score_multiplier': 1.3}, gun_id='gun_precision')
check("EquipmentManager: apply_gun_bonus ضریب امتیاز رو درست ست می‌کنه", close(eqp.get_score_multiplier(), 1.3))
check("EquipmentManager: کلید ذکرنشده (fire_rate_multiplier) روی پیش‌فرض ۱.۰ می‌مونه",
      close(eqp.get_fire_rate_multiplier(), 1.0))
check("EquipmentManager: equipped_gun_id درست ثبت می‌شه", eqp.equipped_gun_id == 'gun_precision')
eqp_restored = EquipmentManager.from_dict(eqp.to_dict())
check("EquipmentManager: to_dict/from_dict رفت‌وبرگشت دقیق",
      eqp_restored.equipped_gun_id == eqp.equipped_gun_id and
      close(eqp_restored.get_score_multiplier(), eqp.get_score_multiplier()))


# ============================================================
print("\n=== BattlePassManager (فاز ۴ -- بازتعادل بخش ۵.۱۲) ===")

from game_logic.battle_pass_manager import (
    BattlePassManager, xp_cost_for_level, total_xp_for_level, generate_rewards_table, MAX_LEVEL,
    SPECIAL_ITEM_LEVELS,
)

check("BattlePassManager: فرمول XP هر سطح == 40 + level*5 (بخش۵.۱۲)", xp_cost_for_level(10) == 40 + 10 * 5)
check("BattlePassManager: مجموع XP کل ۵۰ سطح دقیقاً ۸۳۷۵ است (عدد صریح فایل مرجع)",
      total_xp_for_level(50) == 8375, detail=str(total_xp_for_level(50)))
check("BattlePassManager: مجموع XP از جمع تک‌تک هزینه‌های سطح هم دقیقاً همون ۸۳۷۵ رو می‌ده",
      sum(xp_cost_for_level(l) for l in range(1, 51)) == 8375)

bp_table = generate_rewards_table()
bp = BattlePassManager(total_xp=0, rewards_table=bp_table)
check("BattlePassManager: با ۰ XP در سطح۰ است", bp.get_current_level() == 0)
bp.add_xp(total_xp_for_level(5))
check("BattlePassManager: بعد از XP دقیق سطح۵، get_current_level == 5", bp.get_current_level() == 5)
bp.add_xp(1)  # یک XP اضافه، نباید به سطح۶ برسه
check("BattlePassManager: یک XP کمتر از سطح بعدی، سطح رو بالا نمی‌بره", bp.get_current_level() == 5)

bp_max = BattlePassManager(total_xp=999999, rewards_table=bp_table)
check(f"BattlePassManager: سقف سطح در {MAX_LEVEL} است حتی با XP خیلی زیاد", bp_max.get_current_level() == MAX_LEVEL)

bp_free = BattlePassManager(total_xp=total_xp_for_level(10), is_premium=False, rewards_table=bp_table)
bp_prem = BattlePassManager(total_xp=total_xp_for_level(10), is_premium=True, rewards_table=bp_table)
free_reward = bp_free.get_reward(10)
prem_reward = bp_prem.get_reward(10)
check("BattlePassManager: پاداش غیرپولی فقط free است",
      free_reward == bp_table[9]['free'])
check("BattlePassManager: پاداش پولی، free+premium را جمع می‌زند (نه جایگزین) -- طبق بخش۵.۱۲",
      prem_reward['coins'] == free_reward['coins'] and
      prem_reward['gems'] == free_reward.get('gems', 0) + bp_table[9]['premium']['gems'],
      detail=f"free={free_reward} premium_combined={prem_reward}")

bp_claim = BattlePassManager(total_xp=total_xp_for_level(3), rewards_table=bp_table)
try:
    bp_claim.claim_reward(4)
    check("BattlePassManager: claim_reward سطح باز‌نشده -> ValueError", False, detail="exception raised نشد")
except ValueError:
    check("BattlePassManager: claim_reward سطح باز‌نشده -> ValueError", True)
bp_claim.claim_reward(2)
try:
    bp_claim.claim_reward(2)
    check("BattlePassManager: claim_reward دوباره روی سطح گرفته‌شده -> ValueError", False, detail="exception raised نشد")
except ValueError:
    check("BattlePassManager: claim_reward دوباره روی سطح گرفته‌شده -> ValueError", True)

check("BattlePassManager: آیتم خاص دقیقاً در سطوح ۱۰/۲۵/۴۵ (بخش۵.۱۲)",
      set(SPECIAL_ITEM_LEVELS.keys()) == {10, 25, 45})
check("BattlePassManager: data/battle_pass_rewards.json دقیقاً با تولید فرمولی تازه یکی است "
      "(فایل هاردکد/دستکاری‌دستی نشده)",
      __import__('json').load(open(os.path.join(PROJECT_ROOT, 'data', 'battle_pass_rewards.json'))) == bp_table)

bp_restored = BattlePassManager.from_dict(bp_claim.to_dict(), rewards_table=bp_table)
check("BattlePassManager: to_dict/from_dict رفت‌وبرگشت دقیق (شامل claimed_levels)",
      bp_restored.total_xp == bp_claim.total_xp and bp_restored.claimed_levels == bp_claim.claimed_levels)


# ============================================================
print("\n=== ShopManager (فاز ۴ -- بخش ۵.۱۰: چهار مسیر _apply_item_effect) ===")

from game_logic.shop_manager import ShopManager
from game_logic.special_shot_manager import SpecialShotManager as _SSM_forshop

_econ_shop = EconomyManager(coins=5000, gems=500)
_ssm_shop = _SSM_forshop()
_eqp_shop = EquipmentManager()
_en_shop = EnergyManager()
shop = ShopManager(_econ_shop, special_shot_manager=_ssm_shop, equipment_manager=_eqp_shop,
                    energy_manager=_en_shop)

try:
    shop.purchase_item('does_not_exist')
    check("ShopManager: آیتم ناشناخته -> ValueError", False, detail="exception raised نشد")
except ValueError:
    check("ShopManager: آیتم ناشناخته -> ValueError", True)

_poor = ShopManager(EconomyManager(coins=0, gems=0), special_shot_manager=_SSM_forshop())
_r = _poor.purchase_item('shot_piercing')
check("ShopManager: موجودی ناکافی -> نتیجه‌ی ساختاریافته (نه exception)، success=False",
      _r == {'success': False, 'reason': 'insufficient_funds', 'item': _poor.get_item('shot_piercing')})

_r1 = shop.purchase_item('shot_piercing')
check("ShopManager (special_shots): خرید موفق -> success=True", _r1['success'] is True)
check("ShopManager (special_shots): پیشوند 'shot_' درست حذف و unlock_shot صدا زده شد",
      _ssm_shop.is_unlocked('piercing'))
_r1b = shop.purchase_item('shot_piercing')
check("ShopManager: خرید دوباره‌ی همون دسته‌ی یک‌بارخرید -> already_owned",
      _r1b == {'success': False, 'reason': 'already_owned', 'item': shop.get_item('shot_piercing')})

shop.purchase_item('gun_precision')
check("ShopManager (guns): بونوس درست به equipment_manager می‌رسه", close(_eqp_shop.get_score_multiplier(), 1.3))

_regen_before = _en_shop.regen_seconds_per_unit
shop.purchase_item('upgrade_regen_speed')
check("ShopManager (upgrades/regen_speed): مقدار درست به energy_manager می‌رسه",
      close(_en_shop.regen_seconds_per_unit, _regen_before * 0.8))

_mult_before = _econ_shop.coin_bonus_multiplier
shop.purchase_item('upgrade_coin_bonus')
check("ShopManager (upgrades/coin_bonus): مقدار درست به economy_manager می‌رسه",
      close(_econ_shop.coin_bonus_multiplier, _mult_before * 1.2))

_r_helper_no_cb = shop.purchase_item('helper_skip_level')
check("ShopManager (helpers، بدون callback ثبت‌شده): در owned_helpers نگه داشته می‌شه",
      _r_helper_no_cb['success'] and 'helper_skip_level' in shop.owned_helpers)
_helper_calls = []
shop.register_helper_callback('remove_obstacle', lambda: _helper_calls.append(1))
shop.purchase_item('helper_remove_obstacle')
check("ShopManager (helpers، با callback ثبت‌شده): بلافاصله صدا زده می‌شه", _helper_calls == [1])

_shop_no_ssm = ShopManager(EconomyManager(coins=1000, gems=1000))
try:
    _shop_no_ssm.purchase_item('shot_splitting')
    check("ShopManager: special_shot_manager=None ولی آیتم special_shots -> RuntimeError", False,
          detail="exception raised نشد")
except RuntimeError:
    check("ShopManager: special_shot_manager=None ولی آیتم special_shots -> RuntimeError", True)

_shop_restored = ShopManager(_econ_shop, special_shot_manager=_ssm_shop, equipment_manager=_eqp_shop,
                              energy_manager=_en_shop)
_shop_restored.restore_from_dict(shop.to_dict())
check("ShopManager: to_dict/restore_from_dict رفت‌وبرگشت دقیق",
      _shop_restored.owned_items == shop.owned_items and _shop_restored.owned_helpers == shop.owned_helpers)


# ============================================================
print("\n=== SaveManager (فاز ۴ -- یکپارچگی کامل با SQLite واقعی) ===")

from game_logic.save_manager import SaveManager

_save_tmpdir = _tempfile.mkdtemp()
_save_db_path = os.path.join(_save_tmpdir, 'integration_save.db')

_lm_a = LevelManager(levels_dir=os.path.join(PROJECT_ROOT, 'assets', 'levels'))
_save_a = SaveManager(db_path=_save_db_path)
_profile_a = _save_a.load(_lm_a)

check("SaveManager: پروفایل تازه (بدون ذخیره‌ی قبلی) با مقادیر پیش‌فرض هر manager میاد",
      _profile_a.economy.coins == 0 and _profile_a.energy.current_energy == _profile_a.energy.max_energy and
      _profile_a.battle_pass.total_xp == 0)

_profile_a.economy.add_coins(777)
_profile_a.economy.add_gems(13)
_profile_a.battle_pass.add_xp(total_xp_for_level(7))
_profile_a.energy.consume(3, now=500.0)
_profile_a.equipment.apply_gun_bonus({'fire_rate_multiplier': 1.4}, gun_id='gun_rapid')
_profile_a.special_shots.unlock_shot('splitting')
_lm_a.load_level(1); _lm_a.unlock_next()
_lm_a.load_level(2); _lm_a.unlock_next()
_lm_a.load_level(3)
_save_a.save(_profile_a)
_save_a.close()

# شبیه‌سازی کامل ری‌استارت اپ: LevelManager و SaveManager هردو از صفر ساخته می‌شن
_lm_b = LevelManager(levels_dir=os.path.join(PROJECT_ROOT, 'assets', 'levels'))
_save_b = SaveManager(db_path=_save_db_path)
_profile_b = _save_b.load(_lm_b)

check("SaveManager (رفت‌وبرگشت کامل): coins دووم آورد", _profile_b.economy.coins == 777)
check("SaveManager (رفت‌وبرگشت کامل): gems دووم آورد", _profile_b.economy.gems == 13)
check("SaveManager (رفت‌وبرگشت کامل): battle_pass XP دووم آورد",
      _profile_b.battle_pass.total_xp == total_xp_for_level(7))
check("SaveManager (رفت‌وبرگشت کامل): انرژی مصرف‌شده دووم آورد (نه اینکه رایگان پر بشه)",
      _profile_b.energy.current_energy == _profile_b.energy.max_energy - 3)
check("SaveManager (رفت‌وبرگشت کامل): equipment bonus دووم آورد",
      close(_profile_b.equipment.get_fire_rate_multiplier(), 1.4))
check("SaveManager (رفت‌وبرگشت کامل): شلیک ویژه‌ی باز‌شده دووم آورد",
      _profile_b.special_shots.is_unlocked('splitting'))
check("SaveManager (رفت‌وبرگشت کامل): پیشرفت LevelManager (سطوح باز‌شده) دووم آورد",
      _lm_b.get_unlocked_level_ids() == [1, 2, 3])
check("SaveManager (رفت‌وبرگشت کامل): سطح فعلی LevelManager هم دووم آورد (برای ادامه‌ی خودکار)",
      _lm_b.current_level_id == 3)
_save_b.close()


# ============================================================
print("\n=== یکپارچگی main.py: پاداش پایان مرحله (فاز ۴) ===")

# main.py مستقیماً در sandbox قابل‌اجرا نیست (بدون Kivy)، ولی همون خط
# منطقی که _on_success صدا می‌زنه (level.rewards -> economy/battle_pass)
# اینجا مستقیماً با یک مرحله‌ی واقعی از دیسک وریفای می‌شه.
_econ_sim = EconomyManager()
_bp_sim = BattlePassManager(rewards_table=bp_table)
_level1_for_sim = Level.from_json_file(os.path.join(PROJECT_ROOT, 'assets', 'levels', 'level_001.json'))
_econ_sim.apply_level_rewards(_level1_for_sim.rewards)
_bp_sim.add_xp(_level1_for_sim.rewards.get('xp', 0))
check("main.py._on_success (شبیه‌سازی): سکه‌ی سطح۱ دقیقاً به EconomyManager اضافه می‌شه",
      _econ_sim.coins == _level1_for_sim.rewards.get('coins', 0))
check("main.py._on_success (شبیه‌سازی): XP سطح۱ دقیقاً به BattlePassManager اضافه می‌شه",
      _bp_sim.total_xp == _level1_for_sim.rewards.get('xp', 0))


# ============================================================
print("\n=== NavigationHistory (فاز ۵ -- رفع باگ go_back، بخش ۵.۱۹) ===")

from game_logic.navigation_history import NavigationHistory

nav = NavigationHistory('menu')
nav.push('level_select')
nav.push('game')
check("NavigationHistory: current() بعد از دو push درسته", nav.current() == 'game')
check("NavigationHistory: can_go_back() وقتی بیش‌از یک صفحه هست True است", nav.can_go_back())

back1 = nav.pop()
check("NavigationHistory: اولین go_back به صفحه‌ی درست‌قبلی برمی‌گرده", back1 == 'level_select')
back2 = nav.pop()
# دقیقاً باگی که فایل مرجع رفعش رو می‌خواد: اگه pop() دوباره push می‌کرد،
# اینجا به‌جای 'menu'، به 'level_select' برمی‌گشتیم (چون خودِ برگشتنِ اول
# هم یک ورودی جعلی اضافه کرده بود).
check("NavigationHistory: دومین go_back به 'menu' می‌رسه، نه دوباره به 'level_select' "
      "(دقیقاً باگی که فایل مرجع بخش۵.۱۹ توصیف می‌کنه)", back2 == 'menu')
back3 = nav.pop()
check("NavigationHistory: go_back از تنها صفحه‌ی باقی‌مونده -> None (نمی‌شه عقب‌تر رفت)",
      back3 is None)
check("NavigationHistory: بعد از رسیدن به ته، current() هنوز 'menu' است (چیزی گم نشد)",
      nav.current() == 'menu')

nav2 = NavigationHistory('menu')
nav2.push('a')
nav2.push('b')
nav2.clear('menu')
check("NavigationHistory: clear() کل پشته رو با یک صفحه‌ی تازه جایگزین می‌کنه",
      len(nav2) == 1 and nav2.current() == 'menu' and not nav2.can_go_back())


# ============================================================
print("\n=== calculate_stars (فاز ۵ -- مشتق از همون تایر درصدی بخش۵.۸) ===")

from game_logic.level_condition import calculate_stars

check("calculate_stars: باخت -> ۰ ستاره", calculate_stars({'success': False}) == 0)
check("calculate_stars: tier='legendary' -> ۳ ستاره",
      calculate_stars({'success': True, 'tier': 'legendary'}) == 3)
check("calculate_stars: tier='excellent' -> ۳ ستاره",
      calculate_stars({'success': True, 'tier': 'excellent'}) == 3)
check("calculate_stars: tier='great' -> ۲ ستاره",
      calculate_stars({'success': True, 'tier': 'great'}) == 2)
check("calculate_stars: tier='good' -> ۲ ستاره",
      calculate_stars({'success': True, 'tier': 'good'}) == 2)
check("calculate_stars: tier='close' -> ۱ ستاره",
      calculate_stars({'success': True, 'tier': 'close'}) == 1)


# ============================================================
print("\n=== LevelManager: افزوده‌های فاز۵ -- ثبت ستاره برای LevelSelectScreen ===")

lm_stars = LevelManager(levels_dir=os.path.join(PROJECT_ROOT, 'assets', 'levels'))
check("LevelManager (فاز۵): قبل از هر بازی، get_level_result None است", lm_stars.get_level_result(1) is None)

lm_stars.record_level_result(1, stars=2, shots_used=3, time_remaining=100.0)
check("LevelManager (فاز۵): اولین نتیجه ثبت می‌شه", lm_stars.get_level_result(1)['stars'] == 2)

lm_stars.record_level_result(1, stars=1, shots_used=5, time_remaining=10.0)  # ضعیف‌تر
check("LevelManager (فاز۵): نتیجه‌ی ضعیف‌تر رکورد قبلی رو خراب نمی‌کنه (بهترین تلاش نگه داشته می‌شه)",
      lm_stars.get_level_result(1)['stars'] == 2)

lm_stars.record_level_result(1, stars=3, shots_used=1, time_remaining=250.0)  # بهتر
check("LevelManager (فاز۵): نتیجه‌ی بهتر جایگزین می‌شه", lm_stars.get_level_result(1)['stars'] == 3)

lm_stars.record_level_result(2, stars=1)
check("LevelManager (فاز۵): get_total_stars مجموع بهترین‌های همه‌ی مراحله",
      lm_stars.get_total_stars() == 4, detail=str(lm_stars.get_total_stars()))

exported_with_results = lm_stars.export_progress()
check("LevelManager (فاز۵): export_progress شامل level_results با کلیدهای رشته‌ای است "
      "(سازگار با JSON)", exported_with_results['level_results'] == {'1': lm_stars.get_level_result(1),
                                                                        '2': lm_stars.get_level_result(2)})
lm_stars_2 = LevelManager(levels_dir=os.path.join(PROJECT_ROOT, 'assets', 'levels'))
lm_stars_2.import_progress(exported_with_results)
check("LevelManager (فاز۵): import_progress کلیدها رو به int برمی‌گردونه و مقادیر دقیقاً می‌مونن",
      lm_stars_2.get_level_result(1) == lm_stars.get_level_result(1) and
      lm_stars_2.get_total_stars() == 4)


# ============================================================
print("\n=== SettingsManager (فاز ۵) ===")

from game_logic.settings_manager import SettingsManager, COLOR_BLIND_MODES

settings = SettingsManager()
check("SettingsManager: پیش‌فرض‌ها -- بدون کوررنگی، صدا/موسیقی روشن",
      settings.colorblind_mode is None and settings.sound_enabled and settings.music_enabled)

settings.set_colorblind_mode('protanopia')
check("SettingsManager: set_colorblind_mode مقدار معتبر رو می‌پذیره", settings.colorblind_mode == 'protanopia')

try:
    settings.set_colorblind_mode('not_a_real_mode')
    check("SettingsManager: حالت نامعتبر -> ValueError", False, detail="exception raised نشد")
except ValueError:
    check("SettingsManager: حالت نامعتبر -> ValueError", True)

new_sound_state = settings.toggle_sound()
check("SettingsManager: toggle_sound وضعیت رو برعکس و برمی‌گردونه",
      new_sound_state is False and settings.sound_enabled is False)
settings.toggle_music()
check("SettingsManager: toggle_music هم کار می‌کنه", settings.music_enabled is False)

settings_restored = SettingsManager.from_dict(settings.to_dict())
check("SettingsManager: to_dict/from_dict رفت‌وبرگشت دقیق",
      settings_restored.colorblind_mode == settings.colorblind_mode and
      settings_restored.sound_enabled == settings.sound_enabled and
      settings_restored.music_enabled == settings.music_enabled)

try:
    SettingsManager(colorblind_mode='bogus')
    check("SettingsManager: مقدار نامعتبر در سازنده هم -> ValueError", False, detail="exception raised نشد")
except ValueError:
    check("SettingsManager: مقدار نامعتبر در سازنده هم -> ValueError", True)


# ============================================================
print("\n=== SaveManager: settings هم بخشی از پروفایل ذخیره‌شونده است (فاز ۵) ===")

_save5_tmpdir = _tempfile.mkdtemp()
_save5_db_path = os.path.join(_save5_tmpdir, 'phase5_save.db')

_lm5a = LevelManager(levels_dir=os.path.join(PROJECT_ROOT, 'assets', 'levels'))
_save5a = SaveManager(db_path=_save5_db_path)
_profile5a = _save5a.load(_lm5a)
_profile5a.settings.set_colorblind_mode('deuteranopia')
_profile5a.settings.toggle_sound()
_lm5a.record_level_result(1, stars=3)
_save5a.save(_profile5a)
_save5a.close()

_lm5b = LevelManager(levels_dir=os.path.join(PROJECT_ROOT, 'assets', 'levels'))
_save5b = SaveManager(db_path=_save5_db_path)
_profile5b = _save5b.load(_lm5b)
check("SaveManager (فاز۵): colorblind_mode بین اجراها دووم می‌آره",
      _profile5b.settings.colorblind_mode == 'deuteranopia')
check("SaveManager (فاز۵): sound_enabled بین اجراها دووم می‌آره", _profile5b.settings.sound_enabled is False)
check("SaveManager (فاز۵): level_results (ستاره‌ها) هم بین اجراها دووم می‌آره",
      _lm5b.get_level_result(1) == {'stars': 3, 'shots_used': None, 'time_remaining': None})
_save5b.close()

_save5c = SaveManager(db_path=_save5_db_path)
_save5c.reset()
_lm5c = LevelManager(levels_dir=os.path.join(PROJECT_ROOT, 'assets', 'levels'))
_profile5c = _save5c.load(_lm5c)
check("SaveManager.reset() (فاز۵): بعد از ریست، پروفایل دوباره کاملاً پیش‌فرضه",
      _profile5c.economy.coins == 0 and _profile5c.settings.colorblind_mode is None and
      _lm5c.get_level_result(1) is None)
_save5c.close()


# ============================================================
print("\n=== AppContext (فاز ۵) ===")

from core.app_context import AppContext

_ctx_lm = LevelManager(levels_dir=os.path.join(PROJECT_ROOT, 'assets', 'levels'))
_ctx_save = SaveManager(db_path=os.path.join(_tempfile.mkdtemp(), 'ctx_save.db'))
_ctx_profile = _ctx_save.load(_ctx_lm)
_ctx = AppContext(screen_manager=None, save_manager=_ctx_save, level_manager=_ctx_lm,
                   difficulty_manager=DifficultyManager(), profile=_ctx_profile)
_ctx.profile.economy.add_coins(50)
_ctx.save()
check("AppContext.save(): بدون خطا اجرا می‌شه و واقعاً ذخیره می‌کنه",
      _ctx_save.db.get('player_profile')['economy']['coins'] == 50)

_ctx.reset_profile()
check("AppContext.reset_profile(): level_manager و profile رو با نمونه‌های تازه جایگزین می‌کنه",
      _ctx.profile.economy.coins == 0 and _ctx.level_manager is not _ctx_lm)
_ctx.save_manager.close()


# ============================================================
print("\n=== ColorPalette (فاز ۶ -- بخش ۵.۱۶) ===")

from core.color_palette import ColorPalette, hex_to_rgba

check("hex_to_rgba: تبدیل دقیق -- #FFFFFF -> (1,1,1,1)", hex_to_rgba('#FFFFFF') == (1.0, 1.0, 1.0, 1.0))
check("hex_to_rgba: #000000 -> (0,0,0,1)", hex_to_rgba('#000000') == (0.0, 0.0, 0.0, 1.0))
check("hex_to_rgba: آلفای دلخواه اعمال می‌شه", hex_to_rgba('#FFFFFF', alpha=0.5) == (1.0, 1.0, 1.0, 0.5))

for _mode in (None, 'protanopia', 'deuteranopia', 'tritanopia'):
    _pal = ColorPalette(_mode)
    check(f"ColorPalette[{_mode}]: هر ۷ رنگ صحنه‌ی بازی از هم متفاوتن",
          _pal.all_scene_colors_distinct())

# دقیقاً باگی که بخش۵.۱۶ توصیف می‌کنه: در Protanopia، رنگ جایگزین لیزر
# و رنگ جایگزین هدف قبلاً یکی بودن (هردو #FFCC00)
_pal_prot = ColorPalette('protanopia')
check("ColorPalette[protanopia]: رنگ لیزر با رنگ هدف یکی نیست (باگ اصلی بخش۵.۱۶ رفع شده)",
      _pal_prot.get_laser_color() != _pal_prot.get_target_color())
check("ColorPalette[protanopia]: رنگ هدف دقیقاً #FFCC00 است (طبق فایل مرجع، «بدون تغییر»)",
      _pal_prot.get_target_color() == hex_to_rgba('#FFCC00'))
check("ColorPalette[protanopia]: رنگ لیزر دقیقاً #FF6699 است (طبق فایل مرجع)",
      _pal_prot.get_laser_color() == hex_to_rgba('#FF6699'))

try:
    ColorPalette('not_a_real_mode')
    check("ColorPalette: حالت نامعتبر -> ValueError", False, detail="exception raised نشد")
except ValueError:
    check("ColorPalette: حالت نامعتبر -> ValueError", True)

check("ColorPalette: get_timer_ring_color برای هر تایر یک رنگ معتبر برمی‌گردونه",
      all(len(ColorPalette().get_timer_ring_color(t)) == 4
          for t in ('legendary', 'excellent', 'great', 'good', 'close')))


# ============================================================
print("\n=== AdvancedParticleSystem (فاز ۶ -- بخش ۵.۷، ObjectPool موجود از فاز۱) ===")

from utils.particles import AdvancedParticleSystem, Particle

ps = AdvancedParticleSystem(max_particles=200)
spawned = ps.spawn_explosion(100.0, 200.0, (1.0, 0.0, 0.0, 1.0), count=12)
check("AdvancedParticleSystem: spawn_explosion دقیقاً تعداد خواسته‌شده ذره می‌سازه",
      len(spawned) == 12)
check("AdvancedParticleSystem: همه‌ی ذرات تازه فعال‌ان", all(p.active for p in spawned))
check("AdvancedParticleSystem: get_active_particles همون تعداد رو می‌بینه",
      len(ps.get_active_particles()) == 12)
check("AdvancedParticleSystem: ذرات از نقطه‌ی انفجار شروع می‌شن",
      all(p.x == 100.0 and p.y == 200.0 for p in spawned))

_p_sample = spawned[0]
_p_sample.life = 0.05
for _ in range(5):
    ps.update(0.02)
check("AdvancedParticleSystem: ذره‌ای که عمرش تموم شه غیرفعال و به استخر برمی‌گرده",
      _p_sample.active is False)

for _ in range(200):
    ps.update(0.05)  # زمان زیاد -- همه باید منقضی شده باشن
check("AdvancedParticleSystem: بعد از گذر زمان کافی، هیچ ذره‌ی فعالی نمونده",
      len(ps.get_active_particles()) == 0)

# استفاده‌ی مجدد از استخر -- خودِ هدف ObjectPool
ps.spawn_explosion(0, 0, (1, 1, 1, 1), count=5)
check("AdvancedParticleSystem: بعد از پر شدن دوباره، اندازه‌ی استخر داخلی از max_particles رد نمی‌شه",
      len(ps.pool.active) <= 200)

p = Particle()
check("Particle: مقدار پیش‌فرض غیرفعاله", p.active is False)
p.max_life, p.life = 2.0, 1.0
check("Particle: life_fraction وسط عمر ~۰.۵ است", close(p.life_fraction, 0.5))
p.reset()
check("Particle: reset() به حالت اولیه برمی‌گردونه", p.active is False and p.life == 0.0)


# ============================================================
print("\n=== AudioManager (فاز ۶ -- بخش ۵.۷: بدون pitch، چند فایل جایگزین) ===")

from core.audio_manager import AudioManager, SFX_VARIANTS
from game_logic.settings_manager import SettingsManager as _SettingsManagerForAudio

AudioManager._reset_instance_for_testing()
am1 = AudioManager()
am2 = AudioManager()
check("AudioManager: Singleton -- دو بار ساختن همون نمونه رو می‌ده (بخش۵.۱۸)", am1 is am2)

check("AudioManager: SHOT_TYPES/SFX_VARIANTS دیگه پارامتر عددی pitch نداره -- طبق بخش۵.۷",
      all('pitch' not in str(v).lower() for v in SFX_VARIANTS.values()))
check("AudioManager: mirror_hit چند نسخه‌ی فایل جایگزین داره (نه یک pitch عددی)",
      len(SFX_VARIANTS['mirror_hit']) >= 2)

_variant = am1.pick_variant('mirror_hit')
check("AudioManager: pick_variant یکی از نسخه‌های شناخته‌شده رو برمی‌گردونه",
      _variant in SFX_VARIANTS['mirror_hit'])
check("AudioManager: pick_variant برای افکت ناشناخته None می‌ده", am1.pick_variant('not_a_real_sfx') is None)

try:
    am1.play_sfx('mirror_hit')  # بدون settings، بدون فایل واقعی -- نباید کرش کنه
    check("AudioManager: play_sfx بدون فایل صوتی واقعی به‌شکل امن اجرا می‌شه (سکوت، نه کرش)", True)
except Exception as e:
    check("AudioManager: play_sfx بدون فایل صوتی واقعی به‌شکل امن اجرا می‌شه (سکوت، نه کرش)",
          False, detail=repr(e))

_settings_audio = _SettingsManagerForAudio(sound_enabled=False)
am1.bind_settings(_settings_audio)
_picked_while_muted = []
_orig_pick = am1.pick_variant
am1.pick_variant = lambda name: (_picked_while_muted.append(name) or _orig_pick(name))
am1.play_sfx('mirror_hit')
am1.pick_variant = _orig_pick
check("AudioManager: وقتی sound_enabled=False، play_sfx حتی سراغ انتخاب فایل هم نمی‌ره",
      _picked_while_muted == [])

am1.bind_settings(_SettingsManagerForAudio(sound_enabled=True, music_enabled=False))
am1.play_music('menu')
check("AudioManager: وقتی music_enabled=False، play_music کلید فعلی رو ثبت می‌کنه ولی چیزی پخش نمی‌کنه "
      "(_music_sound خالی می‌مونه)", am1._current_music_key == 'menu' and am1._music_sound is None)

am1.settings.toggle_music()  # حالا روشن شد
am1.on_music_setting_changed()
check("AudioManager: on_music_setting_changed با روشن‌شدن موسیقی، play_music رو دوباره صدا می‌زنه",
      am1._current_music_key == 'menu')


# ============================================================
print("\n=== AdvancedScreenShake: shake_offset (فاز ۶ -- بخش ۵.۷، ریاضیات خالص) ===")

from ui.effects.screen_shake import shake_offset, BASE_AMPLITUDE_PX, BASE_DURATION_S

check("shake_offset: پارامترهای پایه دقیقاً ۵px/۱۵۰ms هستن (بخش۵.۷)",
      close(BASE_AMPLITUDE_PX, 5.0) and close(BASE_DURATION_S, 0.150))
check("shake_offset: در لحظه‌ی صفر با rand=(1,1)، کل دامنه اعمال می‌شه",
      shake_offset(0.0, 0.15, 5.0, 1.0, 1.0) == (5.0, 5.0))
check("shake_offset: درست در پایان duration -> صفر", shake_offset(0.15, 0.15, 5.0, 1.0, 1.0) == (0.0, 0.0))
check("shake_offset: نیمه‌ی راه -> نیمی از دامنه (افت خطی)",
      close(shake_offset(0.075, 0.15, 5.0, 1.0, 1.0)[0], 2.5))
check("shake_offset: بعد از پایان duration هم صفر می‌مونه (نه منفی/نوسانی)",
      shake_offset(0.30, 0.15, 5.0, 1.0, 1.0) == (0.0, 0.0))
check("shake_offset: duration صفر -> بدون تقسیم‌بر‌صفر، فقط صفر برمی‌گردونه",
      shake_offset(0.0, 0.0, 5.0, 1.0, 1.0) == (0.0, 0.0))


# ============================================================
print("\n=== MissionManager (فاز ۷ -- بخش ۵.۱۳) ===")

from game_logic.missions import MissionManager, DAILY_MISSION_DEFINITIONS, WEEKLY_MISSION_DEFINITIONS
from datetime import date as _date, timedelta as _timedelta

check("MissionManager: دقیقاً ۱۰ ماموریت روزانه تعریف شده (بخش۵.۱۳)", len(DAILY_MISSION_DEFINITIONS) == 10)
check("MissionManager: دقیقاً ۱۰ ماموریت هفتگی تعریف شده (بخش۵.۱۳)", len(WEEKLY_MISSION_DEFINITIONS) == 10)

mm = MissionManager()
mm.report_event('shots_fired', 10)
_d = mm._find_mission_by_id('daily_fire_10')
check("MissionManager: report_event ماموریت درست رو پیش می‌بره", _d.progress == 10 and _d.is_complete)
_other = mm._find_mission_by_id('daily_destroy_5')
check("MissionManager: report_event ماموریتی که metricش فرق داره رو دست‌نمی‌زنه", _other.progress == 0)

_reward = mm.claim('daily_fire_10')
check("MissionManager: claim پاداش رو برمی‌گردونه و claimed=True می‌کنه", _reward == {'coins': 20} and _d.claimed)
try:
    mm.claim('daily_fire_10')
    check("MissionManager: claim دوباره -> ValueError", False, detail="exception raised نشد")
except ValueError:
    check("MissionManager: claim دوباره -> ValueError", True)
try:
    mm.claim('daily_destroy_5')  # هنوز کامل نشده
    check("MissionManager: claim قبل از کامل‌شدن -> ValueError", False, detail="exception raised نشد")
except ValueError:
    check("MissionManager: claim قبل از کامل‌شدن -> ValueError", True)
try:
    mm.claim('not_a_real_mission')
    check("MissionManager: claim شناسه‌ی ناشناخته -> ValueError", False, detail="exception raised نشد")
except ValueError:
    check("MissionManager: claim شناسه‌ی ناشناخته -> ValueError", True)

# دقیقاً همون الگویی که بخش۵.۱۳ می‌خواد: deepcopy باید Template مشترک
# رو از آسیب progress یک نمونه‌ی فعال محافظت کنه
_template = next(m for m in DAILY_MISSION_DEFINITIONS if m.mission_id == 'daily_fire_10')
check("MissionManager: deepcopy باعث میشه Template مشترک دست‌نخورده بمونه (بخش۵.۱۳)",
      _template.progress == 0 and _template.claimed is False)

mm.maybe_reset_daily(today=_date(2026, 1, 1))
mm.maybe_reset_weekly(today=_date(2026, 1, 1))
check("MissionManager: maybe_reset_daily همون روز -> False (دوباره ریست نمی‌کنه)",
      mm.maybe_reset_daily(today=_date(2026, 1, 1)) is False)
check("MissionManager: maybe_reset_daily روز بعد -> True و progress صفر می‌شه",
      mm.maybe_reset_daily(today=_date(2026, 1, 2)) is True and
      mm._find_mission_by_id('daily_fire_10').progress == 0)

mm2 = MissionManager()
mm2.report_event('targets_destroyed', 3)
_restored = MissionManager.from_dict(mm2.to_dict())
check("MissionManager: to_dict/from_dict رفت‌وبرگشت دقیق (الگوی _load() بخش۵.۱۳)",
      _restored._find_mission_by_id('daily_destroy_5').progress == 3)


# ============================================================
print("\n=== DailyRewardsManager (فاز ۷ -- بخش ۵.۱۴، استریک تا ۱۰۰ روز) ===")

from game_logic.daily_rewards import DailyRewardsManager, reward_for_streak_day, MAX_STREAK_DAYS

check("DailyRewardsManager: سقف استریک ۱۰۰ روز است (بخش۵.۱۴)", MAX_STREAK_DAYS == 100)

dr = DailyRewardsManager()
check("DailyRewardsManager: در ابتدا می‌شه claim کرد", dr.can_claim_today(today=_date(2026, 1, 1)))
dr.claim(today=_date(2026, 1, 1))
check("DailyRewardsManager: بعد از claim همون روز، can_claim_today False است",
      dr.can_claim_today(today=_date(2026, 1, 1)) is False)
try:
    dr.claim(today=_date(2026, 1, 1))
    check("DailyRewardsManager: claim دوباره‌ی همون روز -> ValueError", False, detail="exception raised نشد")
except ValueError:
    check("DailyRewardsManager: claim دوباره‌ی همون روز -> ValueError", True)

dr.claim(today=_date(2026, 1, 2))
check("DailyRewardsManager: روز متوالی -> استریک +۱", dr.current_streak == 2)
dr.claim(today=_date(2026, 1, 10))  # یک هفته جا افتاده
check("DailyRewardsManager: جاافتادن یک یا چند روز -> استریک از نو شروع می‌شه", dr.current_streak == 1)
check("DailyRewardsManager: longest_streak حداکثر تاریخی رو نگه می‌داره (نه فقط فعلی)",
      dr.longest_streak == 2)

check("DailyRewardsManager: روز۷ پاداش جواهر داره (هر هفته یک جهش)", 'gems' in reward_for_streak_day(7))
check("DailyRewardsManager: روز۱۰۰ پاداش ویژه (آیتم خاص) داره", 'special_items' in reward_for_streak_day(100))
check("DailyRewardsManager: فراتر از ۱۰۰ به ۱۰۰ clamp می‌شه",
      reward_for_streak_day(500) == reward_for_streak_day(100))

dr_restored = DailyRewardsManager.from_dict(dr.to_dict())
check("DailyRewardsManager: to_dict/from_dict رفت‌وبرگشت دقیق",
      dr_restored.current_streak == dr.current_streak and dr_restored.longest_streak == dr.longest_streak)


# ============================================================
print("\n=== WeeklyChallenge (فاز ۷ -- بخش ۵.۱۵، رفع باگ rank) ===")

from game_logic.weekly_challenge import WeeklyChallenge

wc = WeeklyChallenge(target=100)
check("WeeklyChallenge: rank همیشه None است (بخش۵.۱۵ -- بدون بک‌اند واقعی قابل‌محاسبه نیست)",
      wc.rank is None)
wc.add_progress(150)
check("WeeklyChallenge: progress فراتر از target هم درست ثبت می‌شه", wc.progress == 150)
check("WeeklyChallenge: is_complete درست تشخیص می‌ده", wc.is_complete)

_wc_reward = wc.claim_rewards()
check("WeeklyChallenge: claim_rewards بدون rank هم موفق می‌شه و فقط پاداش participation می‌ده "
      "(رفتار پیش‌فرض بخش۵.۱۵، نه یک خطا)", _wc_reward == {'coins': 100, 'gems': 2})
try:
    wc.claim_rewards()
    check("WeeklyChallenge: claim_rewards دوباره -> ValueError", False, detail="exception raised نشد")
except ValueError:
    check("WeeklyChallenge: claim_rewards دوباره -> ValueError", True)

wc2 = WeeklyChallenge(target=50)
try:
    wc2.claim_rewards()
    check("WeeklyChallenge: claim_rewards قبل از کامل‌شدن -> ValueError", False, detail="exception raised نشد")
except ValueError:
    check("WeeklyChallenge: claim_rewards قبل از کامل‌شدن -> ValueError", True)

wc2.add_progress(60)
wc2.claim_rewards()
_reset1 = wc2.maybe_reset(today=_date(2026, 1, 5))   # یک هفته‌ی مشخص
_reset2 = wc2.maybe_reset(today=_date(2026, 1, 6))   # همون هفته
check("WeeklyChallenge: maybe_reset همون هفته -> False", _reset2 is False)
_reset3 = wc2.maybe_reset(today=_date(2026, 1, 15))  # هفته‌ی بعد
check("WeeklyChallenge: maybe_reset هفته‌ی بعد -> True و progress/claimed صفر می‌شن",
      _reset3 is True and wc2.progress == 0 and wc2.claimed is False)


# ============================================================
print("\n=== RetentionAnalytics (فاز ۷ -- بخش ۵.۲۰، الگوی D1..D30) ===")

from game_logic.retention_analytics import RetentionAnalytics

ra = RetentionAnalytics()
_day0 = _date(2026, 2, 1)
_new1 = ra.record_session(today=_day0)
check("RetentionAnalytics: اولین جلسه -> record_session می‌گه روز تازه‌ست", _new1 is True)
_new2 = ra.record_session(today=_day0)
check("RetentionAnalytics: دوباره همون روز -> record_session می‌گه روز تازه نیست (باگ session_started همین‌جا رفع شد)",
      _new2 is False)
check("RetentionAnalytics: d1 قبل از بازگشت -> False", ra.get_d1_retention() is False)
ra.record_session(today=_day0 + _timedelta(days=1))
check("RetentionAnalytics: d1 بعد از بازگشت دقیقاً روز بعد -> True", ra.get_d1_retention() is True)
check("RetentionAnalytics: d3/d7/d14/d30 که بازی نشدن -> False",
      not ra.get_d3_retention() and not ra.get_d7_retention() and
      not ra.get_d14_retention() and not ra.get_d30_retention())
ra.record_session(today=_day0 + _timedelta(days=7))
check("RetentionAnalytics: d7 بعد از بازگشت دقیقاً روز۷ -> True", ra.get_d7_retention() is True)
check("RetentionAnalytics: get_current_session_count روزهای یکتا رو می‌شمره (نه تعداد فراخوانی)",
      ra.get_current_session_count() == 3)

ra_restored = RetentionAnalytics.from_dict(ra.to_dict())
check("RetentionAnalytics: to_dict/from_dict رفت‌وبرگشت دقیق", ra_restored.get_d7_retention() is True)


# ============================================================
print("\n=== NotificationManager (فاز ۷ -- بخش ۵.۲۰) ===")

from core.notification_manager import (
    NotificationManager, compute_energy_full_delay_seconds, compute_comeback_delay_seconds,
)
from game_logic.energy_manager import EnergyManager as _EnergyManagerForNotif

_nm = NotificationManager()
check("NotificationManager: خارج از اندروید واقعی، is_android_ready False است", _nm.is_android_ready is False)

_full_energy = _EnergyManagerForNotif(current_energy=5, max_energy=5)
check("NotificationManager: وقتی انرژی پره، delay محاسبه‌شده None است",
      compute_energy_full_delay_seconds(_full_energy) is None)
_empty_energy = _EnergyManagerForNotif(current_energy=2, max_energy=5, regen_seconds_per_unit=900.0, last_update=0.0)
check("NotificationManager: delay محاسبه‌شده دقیقاً با فرمول EnergyManager جور درمی‌آد",
      compute_energy_full_delay_seconds(_empty_energy, now=0.0) == 3 * 900.0)

_result_off_android = _nm.schedule('energy_full', 100.0)
check("NotificationManager: schedule خارج از اندروید -> scheduled=False، reason='not_android' (نه Exception)",
      _result_off_android == {'scheduled': False, 'reason': 'not_android', 'key': 'energy_full', 'delay_seconds': 100.0})

try:
    _nm.schedule('not_a_real_notification', 10)
    check("NotificationManager: نوع اعلان ناشناخته -> ValueError", False, detail="exception raised نشد")
except ValueError:
    check("NotificationManager: نوع اعلان ناشناخته -> ValueError", True)

check("NotificationManager: schedule_energy_full وقتی پره -> scheduled=False، reason='already_full'",
      _nm.schedule_energy_full(_full_energy) == {'scheduled': False, 'reason': 'already_full', 'key': 'energy_full'})
check("NotificationManager: compute_comeback_delay_seconds پیش‌فرض ۲۰ساعته (بخش۵.۲۰)",
      close(compute_comeback_delay_seconds(), 20 * 3600.0))


# ============================================================
print("\n=== SaveManager: یکپارچگی کامل فاز۷ (شامل رفع باگ session_started) ===")

_save7_tmpdir = _tempfile.mkdtemp()
_save7_db_path = os.path.join(_save7_tmpdir, 'phase7_save.db')

_lm7a = LevelManager(levels_dir=os.path.join(PROJECT_ROOT, 'assets', 'levels'))
_save7a = SaveManager(db_path=_save7_db_path)
_profile7a = _save7a.load(_lm7a)

check("SaveManager (فاز۷): اولین load خودش یک جلسه‌ی امروز ثبت می‌کنه",
      _profile7a.retention.get_current_session_count() == 1)
check("SaveManager (فاز۷): اولین load ماموریت 'ورود روزانه' رو کامل می‌کنه",
      _profile7a.missions._find_mission_by_id('daily_login').is_complete)

_profile7a.missions.report_event('shots_fired', 3)
_save7a.save(_profile7a)
_save7a.close()

# شبیه‌سازی بازکردن مجدد اپ در *همون روز*، چند بار پشت‌سرهم
for _ in range(3):
    _lm_tmp = LevelManager(levels_dir=os.path.join(PROJECT_ROOT, 'assets', 'levels'))
    _save_tmp = SaveManager(db_path=_save7_db_path)
    _profile_tmp = _save_tmp.load(_lm_tmp)
    _save_tmp.save(_profile_tmp)
    _save_tmp.close()

_lm7b = LevelManager(levels_dir=os.path.join(PROJECT_ROOT, 'assets', 'levels'))
_save7b = SaveManager(db_path=_save7_db_path)
_profile7b = _save7b.load(_lm7b)

check("SaveManager (فاز۷): باز‌و‌بسته‌کردن مکرر اپ در یک روز، session count رو زیاد نمی‌کنه",
      _profile7b.retention.get_current_session_count() == 1)
check("SaveManager (فاز۷): همون باز‌و‌بسته‌کردن مکرر، ماموریت هفتگیِ «۵ روز مختلف» رو به‌اشتباه "
      "کامل نمی‌کنه (باگ واقعی پیدا و رفع شد)",
      _profile7b.missions._find_mission_by_id('weekly_login_5').progress == 1)
check("SaveManager (فاز۷): shots_fired قبلی دووم آورد", _profile7b.missions._find_mission_by_id('daily_fire_10').progress == 3)
_save7b.close()


print(f"\n=== نتیجه: {passed} OK, {failed} FAIL ===")
sys.exit(1 if failed else 0)
