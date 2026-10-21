"""
game_logic/level_validator.py  (فاز ۳)

ابزارهای وریفای مرحله -- دو بررسی مستقل و بدون‌وابستگی‌به‌Kivy:

۱. is_solvable(level): آیا مرحله با موتور Raycasting واقعی، با شلیک از
   ده‌ها زاویه‌ی مختلف، واقعاً قابل‌حل است؟

   این تابع در فاز۲ به‌صورت محلی داخل tests/test_core.py نوشته شده بود
   (aim_angle_solves_level + level_is_solvable) و فقط موقعیت شروع
   (t=0) هدف‌ها را چک می‌کرد -- که برای level_001/002 (هر دو ساکن) کافی
   بود. اینجا به game_logic منتقل شد تا هم تست‌ها هم مراحل جدید فاز۳
   بتوانند از آن استفاده کنند، **و** طبق تصمیم فایل مرجع (بخش ۵.۹):
   «با احتساب موقعیت لحظه‌ای‌شون در چند نقطه‌ی زمانی برای اهداف متحرک»
   بسط داده شد -- چون level_005 (فاز۳) اولین مرحله‌ای‌ست که هدف متحرک
   دارد و t=0-only دیگر کافی نیست.

   برای اهداف ساکن، نتیجه دقیقاً همان چیزی‌ست که نسخه‌ی فاز۲ می‌داد
   (هیچ رگرسیونی روی level_001/002 رخ نمی‌دهد -- با تست دوباره تأیید
   شده). برای اهداف متحرک، موقعیت واقعی هدف در چند نقطه‌ی زمانی با
   خودِ MovementSystem (نه یک فرمول جدا و بالقوه ناهماهنگ) شبیه‌سازی
   می‌شود -- تا هیچ‌وقت این تابع و رفتار واقعی بازی از هم جدا نیفتند.

   محدودیت شناخته‌شده: الگوی 'chase_crosshair' به موقعیت لحظه‌ای لمس
   بازیکن وابسته است که اینجا شبیه‌سازی نمی‌شود (world.crosshair_x/y
   پیش‌فرض ۰،۰ می‌ماند) -- برای مراحل فعلی (فاز۳) استفاده نشده، پس
   مشکلی ایجاد نمی‌کند؛ اگر بعداً مرحله‌ای با chase_crosshair نوشته شد،
   این محدودیت باید بازبینی شود.

۲. used_mechanic_types(level): چه نوع مکانیک‌هایی (mirror_type ها +
   portal/prism/black_hole) در این مرحله استفاده شده؟ -- توسط
   DifficultyManager.validate_level_conformance برای اطمینان از اینکه
   یک مرحله فقط از مکانیک‌های تا همان سطح بازشده استفاده می‌کند
   به‌کار می‌رود (جدول سطح معرفی، فایل مرجع بخش ۵.۵).
"""
import math

from ecs.world import World
from ecs.components.position import Position
from ecs.components.mirror import Mirror
from ecs.components.target import Target
from ecs.systems.movement_system import MovementSystem
from ecs.systems.rotation_system import RotationSystem
from game_logic import raycast
from game_logic.scene_builder import entities_to_surfaces

#: طول شبیه‌سازی (ثانیه) برای نمونه‌برداری از موقعیت اهداف متحرک، و
#: تعداد نمونه‌ها در همین بازه -- طبق تصمیم فایل مرجع بخش ۵.۹
#: ("چند نقطه‌ی زمانی"). ۶ ثانیه با ۱۲ نمونه یعنی هر نیم‌ثانیه یک‌بار،
#: که برای دامنه‌ی حرکت فعلی الگوها (بخش ۵.۴) به‌اندازه‌ی کافی از
#: مسیر حرکت هر الگو را می‌پوشاند.
DEFAULT_TIME_SAMPLES = 12
DEFAULT_SIM_DURATION = 6.0

#: فاز۹: انواعی که رفتارشان به random سراسری پایتون وابسته است (پراکندگی آینه‌ی شکسته،
#: زاویه‌ی خروج تصادفی سیاه‌چاله). یک مرحله را فقط با تکیه بر مکانیک‌های *قطعی* می‌شود
#: «اثبات‌شده حل‌پذیر» نامید؛ پس در حالت deterministic_only این دو مثل مانع (جاذب) رفتار
#: می‌کنند: هر زاویه‌ی حلی که پیدا شود از تماس با آن‌ها رد نمی‌شود، پس به شانس وابسته نیست.
STOCHASTIC_TYPES = ('black_hole', 'broken_mirror')


def deterministic_surfaces(surfaces):
    """کپی surfaceها که در آن سیاه‌چاله/آینه‌ی شکسته به مانع تبدیل شده‌اند."""
    result = []
    for surface in surfaces:
        if surface.get('type') in STOCHASTIC_TYPES:
            surface = dict(surface)
            surface['type'] = 'obstacle'
        result.append(surface)
    return result


def _aim_hits_target(gun_x, gun_y, surfaces, angle_deg, target_id):
    dx, dy = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    beams = raycast.cast(gun_x, gun_y, dx, dy, surfaces)
    return any(b.hit_types and b.hit_types[-1] == 'target' and b.hit_ids and
               b.hit_ids[-1] == target_id for b in beams)


def _sweep_all_angles(world, gun_x, gun_y, solved, angle_step_deg,
                      deterministic_only=False, angle_range=(0.0, 360.0)):
    """یک بار کل بازه‌ی زاویه (پیش‌فرض ۰..۳۶۰ درجه) را (با موقعیت *فعلی* دنیا) می‌گردد و
    solved را برای هر هدفی که هنوز حل‌نشده ولی الان قابل‌شلیک است،
    به‌روز می‌کند -- درجا (in place)."""
    surfaces = entities_to_surfaces(world)
    if deterministic_only:
        surfaces = deterministic_surfaces(surfaces)
    remaining = [tid for tid, done in solved.items() if not done]
    if not remaining:
        return
    angle, angle_end = angle_range
    while angle < angle_end:
        for tid in remaining:
            if not solved[tid] and _aim_hits_target(gun_x, gun_y, surfaces, angle, tid):
                solved[tid] = True
        angle += angle_step_deg


def is_solvable(level, angle_step_deg=1.0,
                 time_samples=DEFAULT_TIME_SAMPLES,
                 sim_duration=DEFAULT_SIM_DURATION,
                 deterministic_only=False, angle_range=(0.0, 360.0)):
    """طبق تصمیم فایل مرجع بخش ۵.۹: به‌جای یک چک سطحی، واقعاً چند
    زاویه‌ی شلیک را با موتور Raycasting واقعی امتحان می‌کند؛ برای
    اهداف متحرک، همین کار را در چند نقطه‌ی زمانی (با MovementSystem
    واقعی) هم تکرار می‌کند.

    فاز۹ (سازگار با گذشته؛ پیش‌فرض‌ها رفتار قبلی را نگه می‌دارند):
    * RotationSystem هم اجرا می‌شود -- قبلاً آینه‌ی چرخان هرگز نمی‌چرخید و مرحله‌ی دارای آن
      فقط در جهت اولیه‌اش اعتبارسنجی می‌شد (برای مراحل ۱ تا ۵ که چرخان ندارند تفاوتی نیست).
    * deterministic_only: سیاه‌چاله/آینه‌ی شکسته مانع حساب می‌شوند (حل‌پذیری قطعی، بدون شانس).
    * angle_range: مثلاً (5, 175) فقط نیم‌صفحه‌ی بالای اسلحه (جایی که بازیکن واقعاً هدف می‌گیرد)."""
    world = World()
    world.add_system(MovementSystem())
    world.add_system(RotationSystem())
    gun_x, gun_y = level.populate_world(world)

    target_entities = world.get_entities_with(Position, Target)
    if not target_entities:
        return True

    solved = {e.id: False for e in target_entities}
    moving_ids = {e.id for e in target_entities if e.get_component(Target).is_moving}
    has_rotation = any(e.get_component(Mirror).mirror_type == 'rotating_mirror'
                       and e.get_component(Mirror).rotation_speed != 0.0
                       for e in world.get_entities_with(Mirror))
    time_dependent = bool(moving_ids) or has_rotation

    # نقطه‌ی زمانی صفر -- برای هدف ساکن (در دنیای بدون آینه‌ی چرخان) این تنها و کافی‌ترین چک است.
    _sweep_all_angles(world, gun_x, gun_y, solved, angle_step_deg, deterministic_only, angle_range)

    if time_dependent and time_samples > 0 and not all(solved.values()):
        dt = sim_duration / float(time_samples)
        for _ in range(time_samples):
            if all(solved.values()):
                break
            world.update(dt)
            _sweep_all_angles(world, gun_x, gun_y, solved, angle_step_deg, deterministic_only, angle_range)

    return all(solved.values())


def used_mechanic_types(level):
    """مجموعه‌ی همه‌ی انواع مکانیک استفاده‌شده در این مرحله (mirror_type
    ها + portal/prism/black_hole در صورت وجود) -- برای چک تطابق سطح
    توسط DifficultyManager."""
    types = set()
    for m in level.mirrors:
        types.add(m.get('type', 'normal'))
    if level.portals:
        types.add('portal')
    if level.prisms:
        types.add('prism')
    if level.black_holes:
        types.add('black_hole')
    return types
