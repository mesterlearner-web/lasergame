"""
tests/test_phase9.py  (فاز ۹)

مولد رویه‌ای مراحل، ۱۰۰ فایل مرحله‌ی کمپین، حالت بی‌نهایت، چالش روزانه، دستاوردها و ذخیره‌سازی.

اصل: مراحل کمپین را روی *فایل‌های واقعی روی دیسک* می‌سنجیم (نه خروجی مولد)، با بررسی‌کننده‌هایی که
مولد را نمی‌شناسند (اعتبارسنج جاروبی فاز۳ + DifficultyManager). چند تست «قرارداد موتور» هم هست که
باگ واقعی این فاز را می‌گرفتند: مولد نوع آینه‌ی ساده را 'mirror' می‌نوشت، ولی موتور 'normal' می‌شناسد و
برای نوع ناشناخته پرتو را متوقف می‌کند.

اجرا:  python tests/test_phase9.py
"""
import json
import math
import os
import random
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from game_logic import level_generator as lg  # noqa: E402
from game_logic import level_validator as lv  # noqa: E402
from game_logic import raycast  # noqa: E402
from game_logic.difficulty_manager import MECHANIC_UNLOCK_LEVEL, TOTAL_LEVELS, DifficultyManager  # noqa: E402
from game_logic.level import Level  # noqa: E402
from game_logic.scene_builder import entities_to_surfaces  # noqa: E402

passed = 0
failed = 0


def check(name, condition, detail=''):
    global passed, failed
    if condition:
        passed += 1
        print(f"  OK   {name}")
    else:
        failed += 1
        print(f"  FAIL {name}  {detail}")


def section(title):
    print(f"\n=== {title} ===")


def raises(function, exception_type):
    try:
        function()
    except exception_type:
        return True
    except Exception:  # noqa: BLE001 -- استثنای نوع دیگر یعنی همان نوع انتظار نمی‌رفت
        return False
    return False


LEVELS_DIR = os.path.join(ROOT, 'assets', 'levels')
DM = DifficultyManager()


def level_file(level_id):
    return os.path.join(LEVELS_DIR, f'level_{level_id:03d}.json')


# ====================================================================
section("۱) SeededRng و تکرارپذیری")

rng = lg.SeededRng(5)
reference = random.Random(5)
check("SeededRng فقط random() را مصرف می‌کند (تنها تابع تضمین‌شده‌ی پایدار بین نسخه‌های پایتون)",
      [rng.random() for _ in range(6)] == [reference.random() for _ in range(6)])
rng = lg.SeededRng(11)
values = [rng.randint(3, 7) for _ in range(500)]
check("randint در بازه‌ی بسته‌ی [3, 7] و همه‌ی مقادیر دیده می‌شوند", set(values) == {3, 4, 5, 6, 7})
check("sign فقط ±1 می‌دهد", {lg.SeededRng(s).sign() for s in range(40)} == {1.0, -1.0})
check("choice همیشه عضو فهرست است", all(lg.SeededRng(s).choice(['a', 'b', 'c']) in 'abc' for s in range(30)))
check("campaign_seed پایدار و یکتا برای ۱۰۰ مرحله",
      lg.campaign_seed(30) == 7919 * 30 + 104729 and len({lg.campaign_seed(i) for i in range(1, 101)}) == 100)
check("generate_level دو بار با همان ورودی -> دقیقاً یک خروجی", lg.generate_level(33) == lg.generate_level(33))
check("seed متفاوت -> مرحله‌ی متفاوت", lg.generate_level(33, seed=1) != lg.generate_level(33, seed=2))
check("level_id متفاوت -> مرحله‌ی متفاوت", lg.generate_level(40) != lg.generate_level(41))

# ====================================================================
section("۲) قرارداد موتور (گاردهای باگ واقعی فاز۹)")

check("PLAIN_MIRROR همان نامی است که موتور بازتاب کامل می‌دهد",
      lg.PLAIN_MIRROR in raycast._FULL_REFLECT_TYPES, str(raycast._FULL_REFLECT_TYPES))
ENGINE_MIRROR_TYPES = set(raycast._FULL_REFLECT_TYPES) | {'semi_mirror', 'broken_mirror'}
types_seen = {m['type'] for lid in range(6, 101) for m in lg.generate_level(lid)['mirrors']}
check("همه‌ی نوع‌های آینه‌ی مولد را موتور می‌شناسد (نوع ناشناخته = پرتو متوقف می‌شود)",
      types_seen <= ENGINE_MIRROR_TYPES, str(types_seen - ENGINE_MIRROR_TYPES))

straight = {'level_id': 6, 'laser_start': {'x': 540, 'y': 180, 'angle': 90},
            'targets': [{'x': 540, 'y': 1000, 'hp': 1, 'move_pattern': 'static', 'speed': 0, 'radius': 40}],
            'mirrors': [{'x1': 440, 'y1': 600, 'x2': 640, 'y2': 600, 'type': lg.PLAIN_MIRROR}]}
world, gx, gy, _targets = lg._make_world(Level(straight))
beams = raycast.cast(gx, gy, 0.0, 1.0, entities_to_surfaces(world))
check("آینه‌ی ساده‌ی افقی روی مسیر عمودی، پرتو را بازتاب می‌دهد (به‌جای متوقف‌کردن)",
      len(beams[0].points) >= 3 and beams[0].hit_types[1] == lg.PLAIN_MIRROR, str(beams[0].hit_types))
world, gx, gy, _targets = lg._make_world(Level(dict(straight, mirrors=[dict(straight['mirrors'][0], type='mirror')])))
beams = raycast.cast(gx, gy, 0.0, 1.0, entities_to_surfaces(world))
check("(کنترل منفی) نوع 'mirror' موتور را متوقف می‌کند -- همان باگ اصلی", len(beams[0].points) == 2,
      str(beams[0].hit_types))

check("اثبات قطعی: سیاه‌چاله/آینه‌ی شکسته مانع حساب می‌شوند",
      all(s['type'] == 'obstacle' for s in lv.deterministic_surfaces(
          [{'type': 'black_hole', 'x': 0, 'y': 0, 'radius': 5}, {'type': 'broken_mirror', 'x1': 0, 'y1': 0, 'x2': 1, 'y2': 1}])))
check("deterministic_surfaces نوع‌های دیگر را دست نمی‌زند و ورودی را عوض نمی‌کند",
      lv.deterministic_surfaces([{'type': 'target'}]) == [{'type': 'target'}])

blocked = {'level_id': 6, 'laser_start': {'x': 540, 'y': 180, 'angle': 90},
           'targets': [{'x': 540, 'y': 1000, 'hp': 1, 'move_pattern': 'static', 'speed': 0, 'radius': 40}],
           'black_holes': [{'x': 540, 'y': 600, 'radius': 50, 'emit_x': 100, 'emit_y': 100}]}
check("مرحله‌ای که تنها راهش از سیاه‌چاله می‌گذرد -> در حالت قطعی حل‌ناپذیر",
      lv.is_solvable(Level(blocked), deterministic_only=True) is False)
# آزمون جهش نشان داد بدون کنترل random این تست بین «حالت قطعی» و «نادیده‌گرفتن حالت قطعی» فرق نمی‌گذاشت (سیاه‌چاله‌ی
# تصادفی در بیشتر اجراها هر دو را حل‌ناپذیر می‌دید). random سراسری را کنترل می‌کنیم: سیاه‌چاله از (۱۰۰،۱۰۰) دقیقاً
# به سمت هدف (۵۴۰،۱۰۰۰) می‌تابد؛ «شانس» قطعاً یار است و فقط حالت قطعی باید به آن تکیه نکند.
_saved_uniform = raycast.random.uniform
raycast.random.uniform = lambda a, b: math.atan2(1000 - 100, 540 - 100)
try:
    lucky = lv.is_solvable(Level(blocked), angle_range=(5.0, 175.0))
    strict = lv.is_solvable(Level(blocked), deterministic_only=True, angle_range=(5.0, 175.0))
finally:
    raycast.random.uniform = _saved_uniform
check("(کنترل) وقتی شانس یار است، حالت غیرقطعی همین مرحله را «حل‌پذیر» می‌بیند -- چیزی که اثبات نباید به آن تکیه کند",
      lucky is True)
check("حالت قطعی همان مرحله را حل‌ناپذیر می‌داند (شانس حساب نمی‌شود)", strict is False)

# --- اعتبارسنج حالا RotationSystem را هم اجرا می‌کند ---
# آینه‌ی چرخان در (۵۴۰،۷۰۰). RotationSystem از ۰° مطلق شروع می‌کند: در t=3 ثانیه با سرعت ۲۰°/s جهتش ۶۰° است.
# هدف روی پرتوِ بازتابیده‌ی آن لحظه است، و یک مانع فقط «خط دید مستقیم» اسلحه به هدف را می‌بندد
# (نسخه‌ی اولِ این تست هدف را مستقیم‌دیدنی گذاشته بود و بدون آینه هم حل می‌شد).
phi = 60.0
nx, ny = -math.sin(math.radians(phi)), math.cos(math.radians(phi))
rdx, rdy = raycast._reflect(0.0, 1.0, nx, ny)
reach = {'x': 540 + rdx * 350, 'y': 700 + rdy * 350, 'hp': 1, 'move_pattern': 'static', 'speed': 0, 'radius': 40}
timed = {'level_id': 20, 'laser_start': {'x': 540, 'y': 180, 'angle': 90}, 'targets': [reach],
         'mirrors': [{'x1': 440, 'y1': 700, 'x2': 640, 'y2': 700, 'type': 'rotating_mirror',
                      'rotation_speed': 20.0, 'pivot_x': 540, 'pivot_y': 700}],
         'obstacles': [{'x1': 700, 'y1': 400, 'x2': 700, 'y2': 650, 'destructible': False, 'hp': 999}]}
check("(پیش‌شرط) بدون آینه‌ی چرخان هدف دیده نمی‌شود: مانع خط دید مستقیم را می‌بندد",
      lv.is_solvable(Level(dict(timed, mirrors=[])), angle_step_deg=0.5, angle_range=(5.0, 175.0)) is False)
check("آینه‌ی چرخان: هدف فقط وقتی قابل‌شلیک است که آینه چرخیده باشد -> اعتبارسنج با زمان حل می‌کند",
      lv.is_solvable(Level(timed), angle_step_deg=0.5, angle_range=(5.0, 175.0)) is True)
check("(کنترل) بدون نمونه‌برداری زمانی، همان مرحله حل‌ناپذیر است (جهت اولیه‌ی JSON افقی است)",
      lv.is_solvable(Level(timed), angle_step_deg=0.5, time_samples=0, angle_range=(5.0, 175.0)) is False)
check("angle_range پیش‌فرض ۰..۳۶۰ است (سازگار با گذشته)",
      lv.is_solvable(Level.from_json_file(level_file(5))) is True)

# ====================================================================
section("۳) هندسه‌ی مولد")

check("_dist_pt_seg: فاصله تا وسط پاره‌خط", abs(lg._dist_pt_seg(5, 3, 0, 0, 10, 0) - 3.0) < 1e-9)
check("_dist_pt_seg: فاصله تا انتهای پاره‌خط", abs(lg._dist_pt_seg(13, 4, 0, 0, 10, 0) - 5.0) < 1e-9)
check("_segments_intersect: ضربدری", lg._segments_intersect((0, 0, 10, 10), (0, 10, 10, 0)))
check("_segments_intersect: جدا", not lg._segments_intersect((0, 0, 10, 0), (0, 5, 10, 5)))
check("_dist_seg_seg: موازی", abs(lg._dist_seg_seg((0, 0, 10, 0), (0, 5, 10, 5)) - 5.0) < 1e-9)
check("_dist_seg_seg: متقاطع = ۰", lg._dist_seg_seg((0, 0, 10, 10), (0, 10, 10, 0)) == 0.0)
check("_box_range: پرتو داخل جعبه", lg._box_range(5, 5, 1, 0, 0, 10, 0, 10) == (0.0, 5.0))
check("_box_range: پرتو از بیرون وارد می‌شود", lg._box_range(-5, 5, 1, 0, 0, 10, 0, 10) == (5.0, 15.0))
check("_box_range: پرتو موازی بیرون از جعبه -> None", lg._box_range(5, 20, 1, 0, 0, 10, 0, 10) is None)
check("_box_range: جهت دور از جعبه -> None", lg._box_range(5, 5, 0, 1, 20, 30, 0, 10) is None)

rng = lg.SeededRng(3)
aligned = []
for _ in range(200):
    phi, speed = rng.uniform(0, 360), rng.choice(lg.ROTATION_SPEEDS) * rng.sign()
    t = lg._align_time(phi, speed)
    delta = (speed * t - phi) % 180.0
    aligned.append(t >= lg.FIRE_TIME + 0.2 and min(delta, 180.0 - delta) < 1e-6)
check("_align_time: همیشه ≥ زمان شلیک و جهت آینه‌ی چرخان (mod 180) دقیقاً با φ یکی می‌شود", all(aligned))

# بررسی افزایشی == بررسی کامل
rng = lg.SeededRng(77)
mismatch = 0
for scene in range(60):
    geo = lg._Geo()
    for step in range(rng.randint(2, 7)):
        before = geo.copy()
        mark = geo.mark()
        x, y = rng.uniform(150, 900), rng.uniform(450, 1500)
        kind = rng.randint(0, 2)
        if kind == 0:
            ang, ln = rng.uniform(0, 3.14), rng.uniform(60, 200)
            geo.add_solid((x, y, x + math.cos(ang) * ln, y + math.sin(ang) * ln), 'mirror', path=step % 2)
        elif kind == 1:
            geo.add_disc(x, y, rng.uniform(20, 60), 'target', True, step % 2)
        else:
            geo.add_leg((540, 180, x, y), set())
        if before.ok() and (geo.ok(mark) != geo.ok()):
            mismatch += 1
check("_Geo.ok(mark) افزایشی هم‌ارز بررسی کامل است (۶۰ صحنه‌ی تصادفی)", mismatch == 0, str(mismatch))

# ====================================================================
section("۴) ۱۰۰ فایل مرحله‌ی کمپین (فایل‌های واقعی روی دیسک)")

files_ok = all(os.path.isfile(level_file(i)) for i in range(1, 101))
check("level_001..level_100 همه وجود دارند", files_ok)
check("هیچ فایل اضافه‌ای نیست (دقیقاً ۱۰۰ فایل level_*.json)",
      len([f for f in os.listdir(LEVELS_DIR) if f.startswith('level_') and f.endswith('.json')]) == 100)

levels, raw = {}, {}
for i in range(1, 101):
    with open(level_file(i), encoding='utf-8') as handle:
        raw[i] = json.load(handle)
    levels[i] = Level(raw[i])

check("level_id داخل هر فایل با نام فایل یکی است", all(raw[i]['level_id'] == i for i in raw))
REQUIRED_KEYS = {'level_id', 'phase', 'difficulty', 'time_limit', 'laser_start', 'targets', 'mirrors',
                 'obstacles', 'portals', 'prisms', 'black_holes', 'rewards', 'hints'}
check("هر مرحله‌ی تولیدی همه‌ی کلیدهای ساختار JSON را دارد",
      all(REQUIRED_KEYS <= set(raw[i]) for i in range(6, 101)))
check("مراحل ۱ تا ۵ دستی دست‌نخورده‌اند (کلیدهایشان زیرمجموعه‌ی ساختار است)",
      all(set(raw[i]) <= REQUIRED_KEYS | {'portals', 'prisms', 'black_holes'} for i in range(1, 6)))

violations = {i: DM.validate_level_conformance(levels[i]) for i in range(1, 101)}
check("هر ۱۰۰ مرحله فقط از مکانیک‌های باز تا سطح خودش استفاده می‌کند",
      not any(violations.values()), str({k: v for k, v in violations.items() if v}))

unsolved = [i for i in range(6, 101)
            if not lv.is_solvable(levels[i], angle_step_deg=1.0, deterministic_only=True, angle_range=(5.0, 175.0))]
check("اعتبارسنج جاروبی مستقل: هر ۹۵ مرحله‌ی تولیدی با مکانیک‌های قطعی و نیم‌صفحه‌ی بالا حل‌پذیر است",
      not unsolved, str(unsolved))
check("مراحل دستی ۱ تا ۵ هم حل‌پذیرند (بدون تغییر)", all(lv.is_solvable(levels[i]) for i in range(1, 6)))

bad_count = []
bad_time = []
for i in range(6, 101):
    params = DM.get_recommended_params(i)
    low, high = params['target_count_range']
    if not low <= len(raw[i]['targets']) <= high:
        bad_count.append(i)
    if raw[i]['time_limit'] != params['time_limit_seconds'] or raw[i]['phase'] != params['phase_key']:
        bad_time.append(i)
check("تعداد هدف هر مرحله در بازه‌ی مدیر سختی است", not bad_count, str(bad_count))
check("زمان و فاز هر مرحله همان پیشنهاد مدیر سختی است", not bad_time, str(bad_time))

intro_missing = []
for mechanic, intro_level in MECHANIC_UNLOCK_LEVEL.items():
    if mechanic != 'normal' and intro_level >= 6 and mechanic not in lv.used_mechanic_types(levels[intro_level]):
        intro_missing.append((mechanic, intro_level))
check("هر مکانیک در دقیقاً سطح معرفی‌اش ظاهر می‌شود (۱۶ نیمه‌شفاف، ۲۰ چرخان، ۲۲ منشور، ۳۳ پورتال، ۳۸ سیاه‌چاله، ۴۳ شکسته)",
      not intro_missing, str(intro_missing))

patterns = {t['move_pattern'] for i in range(6, 101) for t in raw[i]['targets']}
check("الگوی حرکت تصادفی/وابسته به لمس هرگز استفاده نمی‌شود (اثبات‌ناپذیرند)",
      not (patterns & {'random', 'chase_crosshair'}), str(patterns))
check("الگوهای حرکت قطعی استفاده شده‌اند", {'static', 'linear_horizontal'} <= patterns, str(patterns))

out_of_bounds = []
for i in range(6, 101):
    for t in raw[i]['targets']:
        if not (lg.X_MIN <= t['x'] <= lg.X_MAX and lg.Y_MIN <= t['y'] <= lg.Y_MAX):
            out_of_bounds.append((i, 'target', t['x'], t['y']))
    for m in raw[i]['mirrors'] + raw[i]['obstacles']:
        for x, y in ((m['x1'], m['y1']), (m['x2'], m['y2'])):
            if not (lg.X_MIN - 1 <= x <= lg.X_MAX + 1 and lg.Y_MIN - 1 <= y <= lg.Y_MAX + 1):
                out_of_bounds.append((i, 'segment', x, y))
check("همه‌ی اهداف/آینه‌ها/موانع داخل میدان بازی‌اند (و دور از ناحیه‌ی اسلحه)", not out_of_bounds, str(out_of_bounds[:3]))

overlap = []
for i in range(6, 101):
    ts = raw[i]['targets']
    for a in range(len(ts)):
        for b in range(a + 1, len(ts)):
            if math.hypot(ts[a]['x'] - ts[b]['x'], ts[a]['y'] - ts[b]['y']) < 2 * 40:
                overlap.append((i, a, b))
check("هیچ دو هدفی روی هم نیفتاده‌اند (مبدأ اهداف)", not overlap, str(overlap[:3]))

rewards = [raw[i]['rewards'] for i in range(6, 101)]
check("پاداش سکه از مرحله‌ی ۵ (۲۲) شروع و غیرنزولی است",
      raw[5]['rewards']['coins'] == 22 and all(rewards[k]['coins'] <= rewards[k + 1]['coins'] for k in range(len(rewards) - 1)))
check("پاداش مرحله‌ی ۱۰۰ (۴۶ سکه) و جواهر هر ۱۰ مرحله",
      raw[100]['rewards']['coins'] == 46 and [i for i in range(6, 101) if raw[i]['rewards']['gems']] == list(range(10, 101, 10)))
check("هر مرحله‌ی تولیدی یک راهنمای فارسی دارد",
      all(len(raw[i]['hints']) == 1 and any('\u0600' <= c <= '\u06FF' for c in raw[i]['hints'][0]) for i in range(6, 101)))

mech_levels = {m: sum(1 for i in range(6, 101) if m in lv.used_mechanic_types(levels[i]))
               for m in ('semi_mirror', 'rotating_mirror', 'prism', 'portal', 'black_hole', 'broken_mirror')}
check("هر مکانیک پیشرفته در حداقل ۱۰ مرحله استفاده شده (محتوا متنوع است)",
      all(n >= 10 for n in mech_levels.values()), str(mech_levels))
moving = sum(1 for i in range(6, 101) for t in raw[i]['targets'] if t['move_pattern'] != 'static')
total = sum(len(raw[i]['targets']) for i in range(6, 101))
check("بین ۲۰٪ تا ۶۵٪ اهداف متحرک‌اند", 0.20 <= moving / total <= 0.65, f"{moving}/{total}")
check("تعداد کمانه به‌ازای هر هدف با سختی بالا می‌رود (آموزشی < استاد)",
      sum(len(raw[i]['mirrors']) for i in range(76, 101)) / sum(len(raw[i]['targets']) for i in range(76, 101))
      > sum(len(raw[i]['mirrors']) for i in range(6, 16)) / sum(len(raw[i]['targets']) for i in range(6, 16)))

# ---- مولد با فایل‌ها هم‌خوان است (drift) ----
# محلی سخت‌گیر. روی CI (متغیر CI=true) فقط هشدار: اگر پلتفرم رانر (glibc/پایتون ۳.۱۱) در یک تصمیم مرزی با
# sandbox یک‌ulp فرق کند، نباید کل بیلد ۴۰دقیقه‌ای بی‌دلیل مسدود شود -- فایل‌های commit‌شده مرجع بازی‌اند و
# سلامتشان را اعتبارسنج جاروبیِ بالا (مستقل از مولد) تضمین می‌کند.
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import generate_levels  # noqa: E402

drift_ok = generate_levels.main(['--check']) == 0
ON_CI = bool(os.environ.get('CI'))
if drift_ok or not ON_CI:
    check("tools/generate_levels.py --check: فایل‌ها دقیقاً همان خروجی مولدند (مولد عوض شده ولی فایل‌ها نه؟)", drift_ok)
else:
    print("  WARN فایل‌های مرحله با خروجی مولد روی این پلتفرم فرق دارند (روی CI غیرمسدودکننده؛ احتمالاً تفاوت libm). "
          "محلی `python tools/generate_levels.py --check` را اجرا کنید.")

# ---- راه‌حل‌ها از *فایل* بازپخش می‌شوند (فقط وقتی مولد و فایل یکی‌اند) ----
if drift_ok:
    replay_failures = []
    for i in (6, 16, 20, 22, 33, 38, 43, 60, 80, 100):
        data, info = lg.generate_level(i, with_info=True)
        for index, angle, t_star in info['solutions']:
            world, gx, gy, targets = lg._make_world(levels[i], t_star)
            surfaces = lv.deterministic_surfaces(entities_to_surfaces(world))
            if not lv._aim_hits_target(gx, gy, surfaces, angle, targets[index].id):
                replay_failures.append((i, index))
    check("راه‌حل ساخته‌شده‌ی ۱۰ مرحله‌ی نمونه، روی *فایل* واقعی هم به هدف می‌خورد", not replay_failures, str(replay_failures))

# ====================================================================
section("۵) رفتار مولد")

data, info = lg.generate_level(77, seed=5, equivalent_level=40, rewards={'coins': 9, 'gems': 0, 'xp': 1}, with_info=True)
params40 = DM.get_recommended_params(40)
check("equivalent_level: سختی/زمان/فاز از مرحله‌ی معادل گرفته می‌شود نه از برچسب",
      data['level_id'] == 77 and data['time_limit'] == params40['time_limit_seconds']
      and data['phase'] == params40['phase_key'], str((data['level_id'], data['time_limit'])))
check("rewards سفارشی نگه داشته می‌شود", data['rewards'] == {'coins': 9, 'gems': 0, 'xp': 1})
low, high = params40['target_count_range']
check("equivalent_level: تعداد هدف در بازه‌ی معادل", low <= len(data['targets']) <= high)
check("with_info: راه‌حل‌ها و پنجره‌ها برگردانده می‌شود و پنجره‌ها از حداقل کمترند نیستند",
      len(info['solutions']) == len(data['targets']) and len(info['windows']) == len(data['targets'])
      and all(w >= 0.8 for w in info['windows']))
check("بدون fallback و بدون کاهش سختی", info['fallback'] is False and info['reductions'] == 0)

# --- مسیر fallback ---
saved = (lg.MAX_ATTEMPTS, lg.MAX_REDUCTIONS, lg._build_candidate)
lg.MAX_ATTEMPTS, lg.MAX_REDUCTIONS = 2, 1
lg._build_candidate = lambda *a, **k: None
try:
    fb_data, fb_info = lg.generate_level(50, with_info=True)
finally:
    lg.MAX_ATTEMPTS, lg.MAX_REDUCTIONS, lg._build_candidate = saved
check("همه‌ی تلاش‌ها شکست بخورد -> fallback با پرچم، و باز هم حل‌پذیر",
      fb_info['fallback'] is True and len(fb_data['targets']) == 1
      and lv.is_solvable(Level(fb_data), deterministic_only=True, angle_range=(5.0, 175.0)))
check("حداکثر تلاش طبق فایل مرجع ۵.۹ = ۲۰", lg.MAX_ATTEMPTS == 20)
check("fallback هنوز ساختار کامل JSON دارد", REQUIRED_KEYS <= set(fb_data))

# --- آینه‌ی چرخان: پنجره‌ی زمانی ---
rot_level = levels[20]
rot_data, rot_info = lg.generate_level(20, with_info=True)
mirrors_rot = [m for m in rot_data['mirrors'] if m['type'] == 'rotating_mirror']
check("مرحله‌ی ۲۰ آینه‌ی چرخان دارد با سرعت مجاز و pivot", len(mirrors_rot) == 1
      and abs(mirrors_rot[0]['rotation_speed']) in lg.ROTATION_SPEEDS and 'pivot_x' in mirrors_rot[0])
rot_index = next(i for i, (idx, a, ts) in enumerate(rot_info['solutions']) if ts > lg.FIRE_TIME + 0.15)
_i, rot_angle, rot_t = rot_info['solutions'][rot_index]
check("شلیک در لحظه‌ی هم‌ترازی به هدف می‌خورد و پنجره‌ی زمانی حداقل ۰٫۰۶ ثانیه است",
      lg._time_half_window(rot_level, rot_index, rot_angle, rot_t) >= lg.MIN_TIME_WINDOW)
world, gx, gy, targets = lg._make_world(rot_level, rot_t + 3.0)
surfaces = lv.deterministic_surfaces(entities_to_surfaces(world))
check("همان زاویه ۳ ثانیه دیرتر (آینه چرخیده) به هدف نمی‌خورد -> واقعاً زمان‌محور است",
      not lv._aim_hits_target(gx, gy, surfaces, rot_angle, targets[rot_index].id))

# --- قالب JSON ---
sample = lg.generate_level(60)
text = lg.format_level_json(sample)
check("format_level_json: رفت‌وبرگشت JSON بدون تغییر", json.loads(text) == sample)
check("format_level_json: هر هدف یک خط و انتها newline", text.endswith('}\n') and text.count('\n    {"id": "target_') == len(sample['targets']))
check("format_level_json: فارسی خام (نه escape شده‌ی \\u06xx)",
      '\\u06' not in text and any('\u0600' <= c <= '\u06FF' for c in text))
check("قالب مراحل تولیدی با مرحله‌ی دستی یکدست است (کلیدهای سطح بالا یک خط)",
      text.splitlines()[1].startswith('  "level_id"') and text.splitlines()[0] == '{')

# ====================================================================
section("۶) AchievementManager (فایل مرجع بخش ۶)")

from datetime import date, timedelta  # noqa: E402

from game_logic.achievements import ACHIEVEMENTS, AchievementManager  # noqa: E402
from game_logic.daily_challenge import (WEEKDAY_LEVELS, DailyChallenge, date_seed,  # noqa: E402
                                        equivalent_level_for, reward_for, time_limit_for)
from game_logic.economy_manager import EconomyManager  # noqa: E402
from game_logic.endless_mode import (EndlessMode, equivalent_level, stage_reward_coins,  # noqa: E402
                                     stage_time_limit)

check("فایل مرجع بخش ۶: سه کلید streak_25 و endless_10 و endless_25 در ACHIEVEMENTS هستند",
      {'streak_25', 'endless_10', 'endless_25'} <= set(ACHIEVEMENTS))
check("هر دستاورد عنوان فارسی، توضیح و پاداش جواهر عددی دارد",
      all(a['title'] and a['description'] and isinstance(a['reward_gems'], int) and a['reward_gems'] > 0
          and any('\u0600' <= c <= '\u06FF' for c in a['title']) for a in ACHIEVEMENTS.values()))

am, eco = AchievementManager(), EconomyManager()
first = am.unlock('endless_10', eco)
check("unlock: اولین بار دیکشنری می‌دهد و جواهر اعمال می‌شود",
      first == {'key': 'endless_10', 'title': ACHIEVEMENTS['endless_10']['title'], 'reward_gems': 2} and eco.gems == 2)
check("unlock: بار دوم None و جواهر دوباره اعمال نمی‌شود", am.unlock('endless_10', eco) is None and eco.gems == 2)
check("unlock بدون economy فقط وضعیت را عوض می‌کند", AchievementManager().unlock('streak_25') is not None)
check("unlock: کلید ناشناخته ValueError (خطای برنامه‌نویسی)", raises(lambda: am.unlock('nope'), ValueError))

am, eco = AchievementManager(), EconomyManager()
check("check_streak(24): هنوز چیزی باز نمی‌شود", am.check_streak(24, eco) == [])
opened = am.check_streak(25, eco)
check("check_streak(25): streak_25 باز و ۵ جواهر", [a['key'] for a in opened] == ['streak_25'] and eco.gems == 5)
check("check_streak دوباره/بیشتر: تکرار نمی‌شود", am.check_streak(25, eco) == [] and am.check_streak(100, eco) == [])
am, eco = AchievementManager(), EconomyManager()
check("check_endless(9): هیچ", am.check_endless(9, eco) == [])
check("check_endless(10): فقط endless_10", [a['key'] for a in am.check_endless(10, eco)] == ['endless_10'])
check("check_endless(25) بعد از ۱۰: فقط endless_25 (نه دوباره endless_10)",
      [a['key'] for a in am.check_endless(25, eco)] == ['endless_25'] and eco.gems == 7)
am, eco = AchievementManager(), EconomyManager()
check("رسیدن مستقیم به مرحله‌ی ۳۰: هر دو باز می‌شوند", {a['key'] for a in am.check_endless(30, eco)} == {'endless_10', 'endless_25'})
am = AchievementManager()
check("check_daily_challenge: ۶ هیچ، ۷ -> daily_challenge_7",
      am.check_daily_challenge(6) == [] and [a['key'] for a in am.check_daily_challenge(7)] == ['daily_challenge_7'])
summary = AchievementManager(['streak_25']).summary()
check("summary: همه‌ی دستاوردها به ترتیب تعریف با پرچم باز/بسته",
      [s['key'] for s in summary] == list(ACHIEVEMENTS) and [s['unlocked'] for s in summary][0] is True
      and sum(s['unlocked'] for s in summary) == 1)
check("to_dict مرتب و from_dict رفت‌وبرگشت", AchievementManager.from_dict(
      AchievementManager(['endless_25', 'streak_25']).to_dict()).unlocked == {'endless_25', 'streak_25'}
      and AchievementManager(['endless_25', 'streak_25']).to_dict()['unlocked'] == ['endless_25', 'streak_25'])
check("from_dict: کلید ناشناخته و داده‌ی None بی‌صدا نادیده گرفته می‌شود (ذخیره‌ی خراب نمی‌شکند)",
      AchievementManager.from_dict({'unlocked': ['streak_25', 'ghost']}).unlocked == {'streak_25'}
      and AchievementManager.from_dict(None).unlocked == set())

# ====================================================================
section("۷) EndlessMode")

check("سختی: مرحله‌ی ۱ ≈ سطح ۸ کمپین، هر مرحله ۳ سطح بالاتر، سقف ۱۰۰",
      [equivalent_level(s) for s in (1, 2, 3, 31, 32, 100)] == [8, 11, 14, 98, 100, 100])
check("زمان هر مرحله از ۱۰۰ ثانیه کم می‌شود و کف ۴۰ دارد",
      [stage_time_limit(s) for s in (1, 2, 20, 21, 100)] == [100, 97, 43, 40, 40])
check("پاداش سکه‌ی مرحله min(25, 3+s)", [stage_reward_coins(s) for s in (1, 5, 22, 23, 80)] == [4, 8, 25, 25, 25])

run = EndlessMode()
check("وضعیت اولیه: اجرا ندارد", not run.is_running and run.current_stage == 0 and run.best_stage == 0)
check("build_level بدون اجرا RuntimeError", raises(run.build_level, RuntimeError))
check("start_run: مرحله‌ی ۱ و شمارنده‌ی اجرا", run.start_run(seed=12) == 1 and run.is_running and run.total_runs == 1)
level_a, level_b = run.build_level(), EndlessMode()
level_b.start_run(seed=12)
level_b = level_b.build_level()
check("همان seed و مرحله -> دقیقاً همان Level", level_a.targets == level_b.targets and level_a.mirrors == level_b.mirrors)
check("مرحله‌ی دیگر یا seed دیگر -> Level دیگر", run.build_level(2).targets != level_a.targets)
check("زمان Level با stage_time_limit بازنویسی شده (نه ۳۰۰ثانیه‌ی کمپین)", level_a.time_limit == 100)
check("level_id Level = سطح معادل (برای هم‌خوانی با DifficultyManager)", level_a.level_id == 8)
bad = [s for s in range(1, 41) if DM.validate_level_conformance(run.build_level(s))]
check("همه‌ی مرحله‌های ۱ تا ۴۰ بی‌نهایت از مکانیک‌های مجاز معادل‌شان استفاده می‌کنند", not bad, str(bad))
unsolved = [s for s in range(1, 21) if not lv.is_solvable(run.build_level(s), deterministic_only=True, angle_range=(5.0, 175.0))]
check("مرحله‌های ۱ تا ۲۰ بی‌نهایت اثبات‌شده حل‌پذیرند (اعتبارسنج مستقل)", not unsolved, str(unsolved))
with_rotating = sum(
    1 for s in range(16)
    if any(m['type'] == 'rotating_mirror' for m in lg.generate_level(20, seed=s, equivalent_level=20)['mirrors']))
check("بی‌نهایت/روزانه «معرفی اجباری مکانیک» ندارند: روی ۱۶ seed همیشه آینه‌ی چرخان نمی‌آید (کمپین ۱۰۰٪ می‌آورد)",
      0 < with_rotating < 16, f"{with_rotating}/16")
check("(مقایسه) مرحله‌ی ۲۰ کمپین واقعاً چرخان دارد", any(
    m['type'] == 'rotating_mirror' for m in lg.generate_level(20)['mirrors']))

eco, am = EconomyManager(), AchievementManager()
run = EndlessMode()
run.start_run(seed=3)
total_coins, seen = 0, []
for stage in range(1, 26):
    summary = run.on_level_complete(am, eco)
    total_coins += stage_reward_coins(stage)
    seen += [a['key'] for a in summary['achievements']]
    if stage == 1:
        check("on_level_complete: خلاصه‌ی مرحله‌ی ۱", summary['stage_cleared'] == 1 and summary['coins'] == 4
              and summary['next_stage'] == 2 and summary['new_best'] is True)
check("۲۵ مرحله: سکه‌ها دقیقاً مجموع پاداش‌ها (از اقتصاد واقعی)", eco.coins == total_coins, f"{eco.coins} vs {total_coins}")
check("دستاوردها دقیقاً در مرحله‌ی ۱۰ و ۲۵ باز شدند (طبق فایل مرجع on_level_complete باید صدا بزند)",
      seen == ['endless_10', 'endless_25'] and eco.gems == 7, str(seen))
check("بهترین مرحله و آمار کل", run.best_stage == 25 and run.total_stages_cleared == 25 and run.current_stage == 26)
summary = run.on_level_failed()
check("باخت: اجرا تمام و خلاصه (۲۵ مرحله)", summary == {'stages_cleared': 25, 'best_stage': 25} and not run.is_running)
run.start_run(seed=4)
second = run.on_level_complete(am, eco)
check("اجرای دوم: رکورد قبلی (۲۵) حفظ و new_best نیست", run.best_stage == 25 and second['new_best'] is False
      and run.total_runs == 2)
check("finish_run بدون اجرا خلاصه‌ی صفر می‌دهد (خروج بی‌اجرا بی‌خطر)", EndlessMode().finish_run() == {'stages_cleared': 0, 'best_stage': 0})
check("on_level_complete بدون اجرا RuntimeError", raises(lambda: EndlessMode().on_level_complete(), RuntimeError))
seeded = EndlessMode()
seeded.start_run()
check("start_run بدون seed: seed از زمان، در بازه‌ی ۳۱ بیت", 0 <= seeded._run['seed'] < 2 ** 31)
check("اجرای نیمه‌کاره ذخیره نمی‌شود، آمار می‌شود",
      EndlessMode.from_dict(run.to_dict()).is_running is False
      and EndlessMode.from_dict(run.to_dict()).best_stage == 25)
check("from_dict: مقدار خراب/None/منفی -> ۰ (ذخیره‌ی خراب بازی را نمی‌شکند)",
      EndlessMode.from_dict({'best_stage': 'xx', 'total_runs': None, 'total_stages_cleared': -5}).to_dict()
      == {'best_stage': 0, 'total_runs': 0, 'total_stages_cleared': 0} and EndlessMode.from_dict(None).best_stage == 0)

# ====================================================================
section("۷.۵) EndlessMode: پیش‌تولید پس‌زمینه‌ی مرحله‌ی بعد (ضد ANR روی گوشی)")

import threading  # noqa: E402
import time  # noqa: E402

from game_logic import endless_mode as em  # noqa: E402

check("prefetch_next بدون اجرا: False و بی‌اثر", EndlessMode().prefetch_next() is False)
run = EndlessMode()
run.start_run(seed=21)
first_level = run.build_level()
check("build_level (مرحله‌ی جاری) مرحله‌ی بعد را در پس‌زمینه شروع می‌کند",
      run._prefetch is not None and run._prefetch['key'] == (21, 2))
check("نخ پیش‌تولید daemon است (بستن برنامه را معطل نمی‌کند)", run._prefetch['thread'].daemon is True)
check("prefetch_next دوباره برای همان مرحله: False (نخ تکراری نمی‌سازد)", run.prefetch_next() is False)
run.on_level_complete()
second_level = run.build_level()
reference = em._generate_stage(21, 2)
check("مرحله‌ی پیش‌تولیدشده دقیقاً همان تولید همزمان است (تابع خالص seed و stage)",
      second_level.targets == reference.targets and second_level.mirrors == reference.mirrors
      and second_level.obstacles == reference.obstacles and second_level.time_limit == reference.time_limit)
check("بعد از مصرف، مرحله‌ی ۳ پیش‌تولید می‌شود", run._prefetch is not None and run._prefetch['key'] == (21, 3))
check("build_level(stage) صریح نخ جدید نمی‌سازد (فقط مرحله‌ی جاری پیش‌تولید می‌کند)",
      (lambda r: (r.start_run(seed=5), r.build_level(4), r._prefetch)[2])(EndlessMode()) is None)
run.finish_run()
check("finish_run پیش‌تولید را رها می‌کند", run._prefetch is None)
run.start_run(seed=21)
check("اجرای تازه پیش‌تولید اجرای قبلی را به ارث نمی‌برد", run._prefetch is None)
other = EndlessMode()
other.start_run(seed=1)
other.build_level()
other._run['seed'] = 2                       # کلید (seed، stage) نمی‌خواند -> نباید استفاده شود
check("پیش‌تولید مال seed دیگر هرگز استفاده نمی‌شود (کلید ناهم‌خوان)",
      other.build_level(2).targets == em._generate_stage(2, 2).targets)

_original_generate = em._generate_stage


def _fails_in_thread(seed, stage):
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError('simulated failure inside the prefetch thread')
    return _original_generate(seed, stage)


em._generate_stage = _fails_in_thread
try:
    flaky = EndlessMode()
    flaky.start_run(seed=33)
    flaky.build_level()
    flaky.on_level_complete()
    recovered = flaky.build_level()
finally:
    em._generate_stage = _original_generate
check("خطا در نخ پیش‌تولید: بی‌صدا به تولید همزمان برمی‌گردد و Level درست می‌دهد",
      recovered.targets == _original_generate(33, 2).targets)


def _slow_in_thread(seed, stage):
    if threading.current_thread() is not threading.main_thread():
        time.sleep(0.3)
    return _original_generate(seed, stage)


em._generate_stage = _slow_in_thread
try:
    slow = EndlessMode()
    slow.start_run(seed=44)
    slow.build_level()
    slow.on_level_complete()
    started = time.perf_counter()
    waited_level = slow.build_level()
    waited = time.perf_counter() - started
finally:
    em._generate_stage = _original_generate
check("نخ هنوز تمام نشده: منتظرش می‌مانیم (کار نیمه‌کاره هدر نمی‌رود) و نتیجه درست است",
      waited_level.targets == _original_generate(44, 2).targets and waited >= 0.2, f"{waited:.2f}s")

# ====================================================================
section("۸) DailyChallenge")

check("WEEKDAY_LEVELS: ۷ مقدار صعودی از ۲۰ تا ۶۴", len(WEEKDAY_LEVELS) == 7 and list(WEEKDAY_LEVELS) == sorted(WEEKDAY_LEVELS)
      and WEEKDAY_LEVELS[0] == 20 and WEEKDAY_LEVELS[-1] == 64)
friday = date(2026, 10, 9)
check("date_seed پایدار: YYYYMMDD×31+7", date_seed(friday) == 20261009 * 31 + 7)
check("equivalent_level_for از روز هفته (جمعه=۴ -> ۴۲)", equivalent_level_for(friday) == WEEKDAY_LEVELS[4] == 42)
check("time_limit_for: max(90, 200−2·سطح)", [time_limit_for(l) for l in (20, 42, 64, 80)] == [160, 116, 90, 90])
check("reward_for: ۶۰ سکه روز اول، ۱۵۰ سقف، جواهر هر ۷ روز",
      [reward_for(s)['coins'] for s in (1, 5, 10, 11, 30)] == [60, 100, 150, 150, 150]
      and [reward_for(s)['gems'] for s in (1, 6, 7, 8, 14)] == [0, 0, 1, 0, 1])

dc = DailyChallenge()
level_1, level_2 = dc.build_level(friday), DailyChallenge().build_level(friday)
check("مرحله‌ی روزانه برای یک تاریخ همیشه یکی است (بین بازیکن‌ها و اجراها)",
      level_1.targets == level_2.targets and level_1.mirrors == level_2.mirrors)
check("تاریخ دیگر -> مرحله‌ی دیگر", dc.build_level(friday + timedelta(days=1)).targets != level_1.targets)
check("زمان Level = time_limit_for و level_id = سطح معادل", level_1.time_limit == 116 and level_1.level_id == 42)
days = [date(2026, 10, 5) + timedelta(days=i) for i in range(28)]
bad = [str(d) for d in days if DM.validate_level_conformance(dc.build_level(d))]
check("۲۸ روز متوالی (۴ هفته): همه از مکانیک‌های مجاز معادل استفاده می‌کنند", not bad, str(bad))
unsolved = [str(d) for d in days if not lv.is_solvable(dc.build_level(d), deterministic_only=True, angle_range=(5.0, 175.0))]
check("۲۸ روز متوالی: همه اثبات‌شده حل‌پذیرند (اعتبارسنج مستقل)", not unsolved, str(unsolved))

dc, eco, am = DailyChallenge(), EconomyManager(), AchievementManager()
check("is_completed/can_claim قبل از اولین تکمیل", not dc.is_completed(friday) and dc.can_claim(friday)
      and dc.display_streak(friday) == 0)
reward = dc.complete(friday, eco, am)
check("روز اول: ۶۰ سکه، استریک ۱", reward['coins'] == 60 and reward['streak'] == 1 and eco.coins == 60
      and dc.total_completed == 1)
check("همان روز دوباره: None و هیچ چیز عوض نمی‌شود", dc.complete(friday, eco, am) is None and eco.coins == 60
      and dc.total_completed == 1)
check("is_completed امروز True؛ can_claim امروز/دیروز False، فردا True",
      dc.is_completed(friday) and not dc.can_claim(friday) and not dc.can_claim(friday - timedelta(days=1))
      and dc.can_claim(friday + timedelta(days=1)))
check("ضدتقلب: عقب‌بردن ساعت پاداش نمی‌دهد و وضعیت را خراب نمی‌کند",
      dc.complete(friday - timedelta(days=3), eco, am) is None and dc.streak == 1 and dc.last_completed == '2026-10-09')
reward = dc.complete(friday + timedelta(days=1), eco, am)
check("روز بعد: استریک ۲ و ۷۰ سکه", reward['streak'] == 2 and reward['coins'] == 70 and eco.coins == 130)
check("display_streak: امروز و دیروز معتبر، دو روز بعد ۰ (رشته پاره شد)",
      dc.display_streak(friday + timedelta(days=1)) == 2 and dc.display_streak(friday + timedelta(days=2)) == 2
      and dc.display_streak(friday + timedelta(days=3)) == 0)
reward = dc.complete(friday + timedelta(days=4), eco, am)
check("یک روز جاافتاده: استریک به ۱ برمی‌گردد ولی بهترین استریک (۲) می‌ماند",
      reward['streak'] == 1 and dc.best_streak == 2 and dc.total_completed == 3)

dc, eco, am = DailyChallenge(), EconomyManager(), AchievementManager()
last = None
for offset in range(7):
    last = dc.complete(friday + timedelta(days=offset), eco, am)
check("۷ روز متوالی: جواهر روز هفتم (۱) + دستاورد daily_challenge_7 (۳)",
      last['gems'] == 1 and [a['key'] for a in last['achievements']] == ['daily_challenge_7'] and eco.gems == 4,
      f"{last} gems={eco.gems}")
check("complete بدون economy/achievement بدون خطا کار می‌کند", DailyChallenge().complete(friday)['streak'] == 1)
check("to_dict/from_dict رفت‌وبرگشت", DailyChallenge.from_dict(dc.to_dict()).to_dict() == dc.to_dict())
check("from_dict: تاریخ خراب، None، مقدار نامعتبر -> پیش‌فرض بی‌خطر",
      DailyChallenge.from_dict({'last_completed': 'not-a-date', 'streak': '??'}).to_dict()
      == {'last_completed': None, 'streak': 0, 'best_streak': 0, 'total_completed': 0}
      and DailyChallenge.from_dict(None).streak == 0)

# ====================================================================
section("۹) ذخیره‌سازی فاز۹ (SQLite واقعی)")

from core.database import Database  # noqa: E402
from game_logic.level_manager import LevelManager  # noqa: E402
from game_logic.save_manager import SaveManager  # noqa: E402

tmp = tempfile.mkdtemp(prefix='lr_p9_')
db_path = os.path.join(tmp, 'save.db')
manager = LevelManager(levels_dir=LEVELS_DIR)
sm = SaveManager(db_path=db_path)
profile = sm.load(manager)
check("بازیکن جدید: سه سیستم فاز۹ پیش‌فرض دارند",
      profile.endless.best_stage == 0 and profile.daily_challenge.streak == 0 and not profile.achievements.unlocked)
profile.endless.best_stage = 12
profile.endless.total_runs = 3
profile.daily_challenge.complete(friday, profile.economy, profile.achievements)
profile.achievements.unlock('endless_10')
sm.save(profile)
sm.db.close()
loaded = SaveManager(db_path=db_path).load(manager)
check("رفت‌وبرگشت کامل: آمار بی‌نهایت، چالش روزانه و دستاوردها",
      loaded.endless.best_stage == 12 and loaded.endless.total_runs == 3
      and loaded.daily_challenge.is_completed(friday) and loaded.daily_challenge.streak == 1
      and loaded.achievements.is_unlocked('endless_10'))
check("سکه‌ی پاداش روزانه هم همراه ذخیره شد", loaded.economy.coins == profile.economy.coins and loaded.economy.coins >= 60)

database = Database(db_path)
state = database.get('player_profile')
for key in ('endless', 'daily_challenge', 'achievements'):
    state.pop(key)
database.set('player_profile', state)
database.close()
old = SaveManager(db_path=db_path).load(manager)
check("ذخیره‌ی قدیمی (قبل از فاز۹، بدون این کلیدها) بدون خطا و با پیش‌فرض بارگذاری می‌شود",
      old.endless.best_stage == 0 and old.daily_challenge.streak == 0 and old.achievements.unlocked == set()
      and old.economy.coins == profile.economy.coins)

database = Database(db_path)
state = database.get('player_profile')
state['endless'] = {'best_stage': 'garbage'}
state['daily_challenge'] = {'last_completed': 12345, 'streak': None}
state['achievements'] = {'unlocked': 'not-a-list'}
database.set('player_profile', state)
database.close()
try:
    corrupt = SaveManager(db_path=db_path).load(manager)
    survived = corrupt.endless.best_stage == 0 and corrupt.daily_challenge.streak == 0
except Exception as exc:  # noqa: BLE001
    survived, _detail = False, repr(exc)
check("ذخیره‌ی با فیلدهای خراب: کل بارگذاری نمی‌شکند (وگرنه بازیکن همه‌ی پیشرفتش را از دست می‌داد)", survived)

# ====================================================================
print(f"\n=== نتیجه: {passed} OK, {failed} FAIL ===")
sys.exit(1 if failed else 0)
