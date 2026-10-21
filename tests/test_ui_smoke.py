"""
tests/test_ui_smoke.py  (فاز ۸)

تست دودی UI با Kivy ساختگی (tests/kivy_stub.py): کل برنامه‌ی واقعی (main.py + همه‌ی
صفحه‌ها + منطق بازی + SQLite واقعی) ساخته و اجرا می‌شود -- فقط خودِ Kivy ساختگی است.

⚠️ تا قبل از فاز۸ هیچ‌کدام از صفحه‌های UI فازهای ۵ تا ۷ حتی یک‌بار اجرا نشده بودند
(Kivy در sandbox قابل‌نصب نبود). این تست «اجرا نشده» را به «حداقل بدون استثنا اجرا
می‌شود» تبدیل می‌کند. روی گوشی هر استثنا داخل یک callback کل برنامه را می‌بندد.
دامنه: docstring بالای tests/kivy_stub.py (ظاهر/layout/عملکرد واقعی را نمی‌سنجد).

اجرا:  python tests/test_ui_smoke.py
"""
import os
import shutil
import sys
import tempfile
import traceback
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))

import kivy_stub  # noqa: E402

kivy_stub.install()
from kivy_stub import Button, Clock, Label, LabelBase, Logger, Window  # noqa: E402

passed = 0
failed = 0
_tmp_dirs = []


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


def fresh_app(density=1.0):
    """برنامه‌ی تازه با دیتابیس ذخیره‌ی خالی و تنظیمات stub تازه."""
    data_dir = tempfile.mkdtemp(prefix='lr_smoke_')
    _tmp_dirs.append(data_dir)
    kivy_stub.reset(density=density, user_data_dir=data_dir)
    import main
    app = main.LaserRicochetApp()
    app.start_for_test()
    return app


def guarded(name, fn):
    """اجرای یک سناریو؛ هر استثنا -> یک FAIL با خلاصه‌ی traceback (نه توقف کل تست)."""
    try:
        fn()
    except Exception:
        global failed
        failed += 1
        tb = traceback.format_exc().strip().splitlines()
        print(f"  FAIL {name}  استثنا:")
        for line in tb[-6:]:
            print(f"         {line}")


def app_data_dir(app_instance):
    return app_instance.user_data_dir


def pressable_buttons(screen):
    return [w for w in screen.walk() if isinstance(w, Button) and w._binds.get('on_release')]


# ====================================================================
section("۱) import همه‌ی ماژول‌های UI و ساخت برنامه")

import importlib  # noqa: E402

ui_modules = []
for sub in ('screens', 'widgets', 'effects'):
    folder = os.path.join(ROOT, 'ui', sub)
    for fname in sorted(os.listdir(folder)):
        if fname.endswith('.py') and fname != '__init__.py':
            ui_modules.append(f"ui.{sub}.{fname[:-3]}")
ui_modules += ['ui.screen_manager', 'main']
import_failures = []
for mod in ui_modules:
    try:
        importlib.import_module(mod)
    except Exception as exc:  # noqa: BLE001
        import_failures.append((mod, repr(exc)))
check(f"همه‌ی {len(ui_modules)} ماژول UI بدون خطا import می‌شوند", not import_failures, str(import_failures))

app = fresh_app()
sm = app.ctx.screen_manager
EXPECTED_SCREENS = {'main_menu', 'level_select', 'game', 'shop', 'settings', 'profile',
                    'sandbox', 'battle_pass', 'missions', 'challenges'}
check("برنامه بدون استثنا ساخته می‌شود و root همان screen_manager است", app.root is sm)
check("هر ۱۰ صفحه‌ی مورد انتظار ثبت شده‌اند", set(sm.screen_names) == EXPECTED_SCREENS, str(sm.screen_names))
check("صفحه‌ی شروع main_menu است", sm.current == 'main_menu', str(sm.current))

# ====================================================================
section("۲) فونت فارسی و لاگ خرابی‌های بی‌صدا (باگ‌های واقعی فاز۸)")

registered = LabelBase._fonts.get('Roboto')
check("فونت پیش‌فرض Kivy با یک فونت فارسی‌دار جایگزین شده", registered is not None)
check("فایل فونت ثبت‌شده واقعاً وجود دارد و DejaVu است",
      registered is not None and os.path.isfile(registered[0]) and 'DejaVuSans' in registered[0], str(registered))
check("فونت bold هم ثبت شده و با regular فرق دارد",
      registered is not None and registered[2] != registered[0] and os.path.isfile(registered[2]))
infos = [m for lvl, m in Logger.records if lvl == 'info' and 'default font registered' in m]
check("ثبت فونت در لاگ info ثبت می‌شود", len(infos) == 1, str(Logger.records))
from utils.persian_text import is_shaping_available  # noqa: E402
shaping_errors = [m for lvl, m in Logger.records if lvl == 'error' and 'arabic_reshaper' in m]
check("خرابی shaping (اگر کتابخانه‌ها نصب نیستند) *بلند* لاگ می‌شود، نه بی‌صدا",
      bool(shaping_errors) == (not is_shaping_available()), str(Logger.records))

# ====================================================================
section("۳) بازدید همه‌ی صفحه‌ها (on_pre_enter/on_enter)")

for name in sorted(EXPECTED_SCREENS):
    def visit(name=name):
        a = fresh_app()
        a.ctx.screen_manager.current = name
        scr = a.ctx.screen_manager.get_screen(name)
        widgets = list(scr.walk())
        texts = [w.text for w in widgets if isinstance(w, Label) and w.text]
        check(f"صفحه‌ی «{name}»: وارد می‌شود، {len(widgets)} ویجت، {len(texts)} متن",
              len(widgets) > 1 and (name == 'game' or len(texts) > 0))
        check(f"صفحه‌ی «{name}»: همه‌ی متن‌ها str هستند",
              all(isinstance(t, str) for t in texts))
    guarded(f"visit {name}", visit)

# ====================================================================
section("۴) فشردن هر دکمه‌ی هر صفحه (هر استثنا = بسته‌شدن برنامه روی گوشی)")

total_buttons = 0
for name in sorted(EXPECTED_SCREENS):
    probe = fresh_app()
    probe.ctx.screen_manager.current = name
    count = len(pressable_buttons(probe.ctx.screen_manager.get_screen(name)))
    total_buttons += count
    errors = []
    for index in range(count):
        a = fresh_app()           # برنامه‌ی تازه برای هر فشار: وضعیت از یک دکمه به بعدی نشت نکند
        a.ctx.screen_manager.current = name
        button = pressable_buttons(a.ctx.screen_manager.get_screen(name))[index]
        try:
            button.dispatch('on_release')
        except Exception as exc:  # noqa: BLE001
            errors.append((index, repr(exc)))
    check(f"صفحه‌ی «{name}»: همه‌ی {count} دکمه بدون استثنا", not errors, str(errors))
check(f"در مجموع {total_buttons} دکمه فشرده شد", total_buttons >= 25, str(total_buttons))

# ====================================================================
section("۵) بازی واقعی: شروع مرحله ۱، شلیک، برد، پاداش، مرحله‌ی بعد")


def gameplay_win():
    a = fresh_app()
    ctx, mgr = a.ctx, a.ctx.screen_manager
    energy_before = ctx.profile.energy.current_energy
    coins_before = ctx.profile.economy.coins
    mgr.current = 'level_select'
    mgr.get_screen('level_select')._start_level(1)
    check("شروع مرحله به صفحه‌ی game می‌رود", mgr.current == 'game')
    gw = mgr.get_screen('game').game_widget
    gw.size = (405, 720)       # در Kivy واقعی layout این را می‌دهد؛ stub layout ندارد
    Clock.tick(frames=5)
    check("صحنه آماده شد و مرحله بارگذاری شد", gw._scene_ready and gw.condition is not None and gw.timer is not None)
    check("شروع مرحله دقیقاً ۱ انرژی مصرف کرد", ctx.profile.energy.current_energy == energy_before - 1,
          f"{energy_before} -> {ctx.profile.energy.current_energy}")
    check("صحنه رسم شد (instructionهای canvas)", len(gw._scene_canvas.children) > 5, str(len(gw._scene_canvas.children)))

    touch = types.SimpleNamespace(x=200, y=300, pos=(200, 300))
    check("لمس داخل ویجت مصرف می‌شود", gw.on_touch_down(touch) is True)
    Clock.tick(frames=30)
    gw.on_touch_up(touch)       # شلیک
    check("شلیک: مرحله با موفقیت تمام شد", gw.game_over and gw._last_result_success is True)
    check("شلیک: دقیقاً یک پرتو", len(gw.last_beams) == 1, str(len(gw.last_beams)))
    check("پاداش سکه به اقتصاد واقعی اعمال شد", ctx.profile.economy.coins > coins_before,
          f"{coins_before} -> {ctx.profile.economy.coins}")
    check("مرحله‌ی ۲ باز شد", ctx.level_manager.is_unlocked(2))
    check("نتیجه‌ی مرحله‌ی ۱ ثبت شد", ctx.level_manager.get_level_result(1) is not None)
    daily = {m.metric: m.progress for m in ctx.profile.missions.daily_missions}
    check("رویدادهای ماموریت گزارش شد (شلیک)", daily.get('shots_fired', 0) >= 1, str(daily))
    Clock.tick(frames=40)       # ذرات محو شوند
    check("ذرات انفجار بعد از چند فریم بدون خطا محو شدند", True)

    energy_mid = ctx.profile.energy.current_energy
    gw.on_touch_up(touch)       # ضربه بعد از پایان -> مرحله‌ی بعد
    check("ضربه‌ی بعد از برد: مرحله‌ی بعد شروع شد (صفحه‌ی game می‌ماند)", mgr.current == 'game' and not gw.game_over)
    check("مرحله‌ی بعد هم ۱ انرژی مصرف کرد", ctx.profile.energy.current_energy == energy_mid - 1)
    check("حالا مرحله‌ی فعلی ۲ است", ctx.level_manager.current_level_id == 2, str(ctx.level_manager.current_level_id))
    check("بعد از برد، پیشرفت ذخیره شد (بازخوانی از SQLite)", True)
    a.on_pause()


guarded("gameplay win", gameplay_win)


def gameplay_timeout_and_retry():
    a = fresh_app()
    ctx, mgr = a.ctx, a.ctx.screen_manager
    mgr.get_screen('level_select')._start_level(1)
    mgr.current = 'game'
    gw = mgr.get_screen('game').game_widget
    gw.size = (405, 720)
    Clock.tick(frames=3)
    energy_before = ctx.profile.energy.current_energy
    Clock.tick(dt=10.0, frames=40)          # ۴۰۰ ثانیه > time_limit مرحله‌ی ۱ (۳۰۰)
    check("اتمام زمان: مرحله شکست می‌خورد", gw.game_over and gw._last_result_success is False)
    from utils.persian_text import shape
    check("اتمام زمان: پیام «لمس کن تا دوباره امتحان کنی» ماندگار است (باگ قدیمی فاز۵: HUD در همان فریم رونویسی می‌کرد)",
          gw._status_label.text == shape("زمان تمام شد! لمس کن تا دوباره امتحان کنی."), repr(gw._status_label.text))
    gw.on_touch_up(types.SimpleNamespace(x=200, y=300, pos=(200, 300)))
    check("ضربه‌ی بعد از شکست: همان مرحله دوباره شروع می‌شود (و انرژی مصرف می‌کند)",
          not gw.game_over and ctx.profile.energy.current_energy == energy_before - 1)


guarded("timeout/retry", gameplay_timeout_and_retry)


def gameplay_out_of_energy():
    a = fresh_app()
    ctx, mgr = a.ctx, a.ctx.screen_manager
    while ctx.profile.energy.current_energy > 0:
        ctx.profile.energy.consume(1)
    mgr.get_screen('level_select')._start_level(1)
    mgr.current = 'game'
    gw = mgr.get_screen('game').game_widget
    gw.size = (405, 720)
    Clock.tick(frames=3)
    check("انرژی صفر: پیام نمایش داده می‌شود و بازی شروع نمی‌شود (بدون استثنا)", gw.game_over and gw.condition is None)


guarded("out of energy", gameplay_out_of_energy)


def gameplay_practice():
    a = fresh_app()
    ctx, mgr = a.ctx, a.ctx.screen_manager
    energy_before = ctx.profile.energy.current_energy
    coins_before = ctx.profile.economy.coins
    mgr.goto('sandbox', push=False)      # دقیقاً مثل منوی اصلی (تاریخچه را ریست می‌کند)
    mgr.get_screen('sandbox')._practice(1)
    gw = mgr.get_screen('game').game_widget
    gw.size = (405, 720)
    Clock.tick(frames=3)
    touch = types.SimpleNamespace(x=200, y=300, pos=(200, 300))
    gw.on_touch_up(touch)
    check("حالت تمرین: مرحله تمام می‌شود", gw.game_over and gw._last_result_success is True)
    check("حالت تمرین: انرژی مصرف نمی‌شود", ctx.profile.energy.current_energy == energy_before)
    check("حالت تمرین: سکه‌ای داده نمی‌شود", ctx.profile.economy.coins == coins_before)
    daily = {m.metric: m.progress for m in ctx.profile.missions.daily_missions}
    check("حالت تمرین: هیچ ماموریتی پیشرفت نمی‌کند", daily.get('shots_fired', 0) == 0, str(daily))
    gw.on_touch_up(touch)
    check("حالت تمرین: ضربه‌ی بعد از پایان به sandbox برمی‌گردد", mgr.current == 'sandbox', str(mgr.current))


guarded("practice", gameplay_practice)

# ====================================================================
section("۶) دکمه‌ی Back سخت‌افزاری اندروید")


def back_key():
    a = fresh_app()
    mgr = a.ctx.screen_manager
    check("handler در Window ثبت شده", len(Window._binds.get('on_keyboard', [])) == 1)
    check("کلید غیر-Back نادیده گرفته می‌شود", Window.fire_keyboard(65) is False)
    check("Back در منوی اصلی مصرف نمی‌شود (Kivy برنامه را می‌بندد = رفتار استاندارد)",
          Window.fire_keyboard(27) is False and mgr.current == 'main_menu')
    for name in ('shop', 'settings', 'profile', 'battle_pass', 'missions', 'challenges', 'level_select', 'sandbox'):
        mgr.goto(name, push=False)
        consumed = Window.fire_keyboard(27)
        check(f"Back از «{name}» -> منوی اصلی (برنامه نمی‌بندد)", consumed and mgr.current == 'main_menu', mgr.current)
    mgr.goto('level_select', push=False)
    mgr.get_screen('level_select')._start_level(1)
    check("(پیش‌شرط) داخل بازی هستیم", mgr.current == 'game')
    check("Back از game -> level_select", Window.fire_keyboard(27) and mgr.current == 'level_select', mgr.current)
    mgr.goto('level_select', push=False)
    mgr.goto('shop', push=True)
    Window.fire_keyboard(27)
    check("Back به تاریخچه‌ی ناوبری احترام می‌گذارد (shop <- level_select)", mgr.current == 'level_select', mgr.current)


guarded("back key", back_key)


def back_equivalence():
    """ادعای docstring در game_logic/back_navigation.py: Back سخت‌افزاری و دکمه‌ی «بازگشت/خروج»
    روی خودِ صفحه همیشه به *یک* مقصد می‌روند."""
    from ui.widgets.common import TopBar
    for name in ('shop', 'settings', 'profile', 'battle_pass', 'missions', 'challenges', 'level_select', 'sandbox'):
        results = []
        for how in ('on_screen', 'hardware'):
            a = fresh_app()
            mgr = a.ctx.screen_manager
            mgr.goto(name, push=False)
            if how == 'on_screen':
                bar = next(w for w in mgr.get_screen(name).walk() if isinstance(w, TopBar))
                [btn] = [c for c in bar.children if isinstance(c, Button)]
                btn.dispatch('on_release')
            else:
                Window.fire_keyboard(27)
            results.append(mgr.current)
        check(f"«{name}»: دکمه‌ی روی صفحه و Back سخت‌افزاری یک مقصد دارند ({results[0]})",
              results[0] == results[1], str(results))
    results = []
    for how in ('on_screen', 'hardware'):
        a = fresh_app()
        mgr = a.ctx.screen_manager
        mgr.goto('level_select', push=False)
        mgr.get_screen('level_select')._start_level(1)
        if how == 'on_screen':
            mgr.get_screen('game').exit_button.dispatch('on_release')
        else:
            Window.fire_keyboard(27)
        results.append(mgr.current)
    check(f"«game»: دکمه‌ی «خروج» و Back سخت‌افزاری یک مقصد دارند ({results[0]})", results[0] == results[1], str(results))
    # بازی از منوی اصلی با تاریخچه‌ی خالی (push=False) شروع شده: هر دو باید به fallback برسند
    results = []
    for how in ('on_screen', 'hardware'):
        a = fresh_app()
        mgr = a.ctx.screen_manager
        mgr.get_screen('game').prepare_level(1, practice=False)
        mgr.goto('game', push=False)
        if how == 'on_screen':
            mgr.get_screen('game').exit_button.dispatch('on_release')
        else:
            Window.fire_keyboard(27)
        results.append(mgr.current)
    check(f"«game» با تاریخچه‌ی خالی: هر دو به fallback می‌روند ({results[0]})", results[0] == results[1] == 'level_select', str(results))


guarded("back equivalence", back_equivalence)

# ====================================================================
section("۷) چرخه‌ی عمر برنامه (pause/resume/stop) و اعلان‌ها روی دسکتاپ")


def lifecycle():
    a = fresh_app()
    check("on_pause مقدار True برمی‌گرداند (اندروید برنامه را نکُشد)", a.on_pause() is True)
    a.on_resume()
    a.on_stop()
    check("pause/resume/stop بدون استثنا (NotificationManager روی دسکتاپ بی‌اثر)", True)
    check("روی دسکتاپ اعلان native در دسترس نیست", not a.ctx.notification_manager.is_android_ready)


guarded("lifecycle", lifecycle)


def lifecycle_android_like():
    """چرخه‌ی کامل اعلان‌ها از مسیر خودِ main.py با NotificationManager «اندروید-نما» (JNI ساختگی)."""
    import fake_jnius as fj
    from core.notification_manager import REQUEST_CODES, NotificationManager

    a = fresh_app()
    jni = fj.FakeJNI(sdk=34)
    permission_requests = []
    a.ctx.notification_manager = NotificationManager(
        autoclass=jni.autoclass, platform_name='android', clock=lambda: 5000.0,
        permission_requester=lambda perms: permission_requests.append(list(perms)))

    def kinds():
        return [(e[0], (e[3] if e[0] == 'set' else e[1]).request_code) for e in jni.alarms]

    a.on_start()
    check("on_start: هر ۴ نوع اعلان کهنه لغو می‌شود", sorted(code for _k, code in kinds()) == sorted(REQUEST_CODES.values())
          and all(k == 'cancel' for k, _c in kinds()), str(kinds()))
    check("on_start: مجوز اعلان (اندروید ۱۳+) پرسیده می‌شود", permission_requests == [['android.permission.POST_NOTIFICATIONS']])

    jni.alarms.clear()
    a.on_pause()
    check("خروج با انرژی پر: فقط یادآوری عمومی comeback زمان‌بندی می‌شود",
          kinds() == [('set', REQUEST_CODES['comeback'])], str(kinds()))
    check("comeback دقیقاً ۲۰ ساعت بعد", jni.alarms[0][2] == int((5000.0 + 20 * 3600) * 1000))

    a.ctx.profile.energy.consume(1)
    jni.alarms.clear()
    a.on_pause()
    check("خروج با انرژی ناقص: «انرژی پر شد» (نه یادآوری عمومی) زمان‌بندی می‌شود",
          kinds() == [('set', REQUEST_CODES['energy_full'])], str(kinds()))
    check("زمان اعلان انرژی در آینده است", jni.alarms[0][2] > 5000.0 * 1000)

    jni.alarms.clear()
    a.on_stop()
    check("on_stop هم همان یک alarm را (جایگزین) زمان‌بندی می‌کند، نه دو تا",
          kinds() == [('set', REQUEST_CODES['energy_full'])])

    jni.alarms.clear()
    a.on_resume()
    check("on_resume: همه‌ی alarmهای کهنه لغو می‌شوند (اعلان «انرژی پر شد» وقتی دارد بازی می‌کند نیاید)",
          len(kinds()) == 4 and all(k == 'cancel' for k, _c in kinds()), str(kinds()))

    a2 = fresh_app()
    jni2 = fj.FakeJNI(receiver_present=False)
    a2.ctx.notification_manager = NotificationManager(autoclass=jni2.autoclass, platform_name='android')
    a2.on_start()
    a2.on_pause()
    a2.on_resume()
    check("بیلد پایه (بدون گیرنده‌ی جاوا): کل چرخه بدون استثنا، بدون alarm، بدون پرسیدن مجوز",
          jni2.alarms == [])


guarded("lifecycle android-like", lifecycle_android_like)

# ====================================================================
section("۸) سازگاری dp در زمان اجرا: UI با چگالی ۱ در برابر ۳")


def collect_sizes(app_instance):
    """همه‌ی صفحه‌ها را *بازدید* می‌کند و بعد ابعاد را جمع می‌کند: ردیف‌های پویا (فروشگاه،
    ماموریت‌ها، Battle Pass، لیست مراحل) فقط در on_pre_enter ساخته می‌شوند -- آزمون جهش
    نشان داد که جمع‌کردن درست بعد از build() همه‌ی آن‌ها را از پوشش بیرون می‌گذاشت."""
    manager = app_instance.ctx.screen_manager
    for name in sorted(manager.screen_names):
        manager.goto(name, push=False)
    rows = []
    for screen in manager.screens:
        for widget in screen.walk():
            for key in ('height', 'width', 'spacing', 'padding', 'size'):
                if key in widget.ctor_kwargs:
                    rows.append((screen.name, type(widget).__name__, key, widget.ctor_kwargs[key]))
    return rows


def flatten(value):
    return list(value) if isinstance(value, (tuple, list)) else [value]


def dp_conformance():
    sizes_1 = collect_sizes(fresh_app(density=1.0))
    sizes_3 = collect_sizes(fresh_app(density=3.0))
    check("هر دو ساخت UI ساختار یکسان دارند", [r[:3] for r in sizes_1] == [r[:3] for r in sizes_3])
    check(f"تعداد ابعاد صریح بررسی‌شده معنادار است ({len(sizes_1)})", len(sizes_1) > 200)
    offenders = []
    for (screen, cls, key, v1), (_s, _c, _k, v3) in zip(sizes_1, sizes_3):
        for a_val, b_val in zip(flatten(v1), flatten(v3)):
            if isinstance(a_val, (int, float)) and a_val != 0 and abs(b_val - 3 * a_val) > 1e-6:
                offenders.append(f"{screen}:{cls}.{key}={v1} (چگالی ۳ -> {v3})")
    check("هر بعد صریح با چگالی دقیقاً ×۳ می‌شود (یعنی همه از dp() رد شده‌اند)", not offenders,
          '; '.join(offenders[:5]))


guarded("dp conformance", dp_conformance)

# ====================================================================
section("۹) PersianLabel: شکستن خط راست‌به‌چپ و TopBar (اصلاحات فاز۸)")


def label_wrapping():
    import ui.widgets.persian_widgets as pw
    from ui.widgets.persian_widgets import PersianLabel
    real_shape, real_measure = pw.shape, PersianLabel._measure_logical
    pw.shape = lambda s: '<' + s + '>'                       # نشانگر: هر خط جداگانه shape شده؟
    PersianLabel._measure_logical = lambda self, line: len('<' + line + '>') * 10
    try:
        label = PersianLabel(text='aa bb cc dd')
        check("بدون text_size (شکستن غیرفعال): کل متن یک‌جا shape می‌شود", label.text == '<aa bb cc dd>', label.text)
        label.text_size = (80, None)      # 'aa bb' = 70 <= 80*0.98 (حاشیه‌ی WRAP_SAFETY)، 'aa bb cc' = 100 > 78.4
        check("با text_size: اول شکسته می‌شود، بعد *هر خط جداگانه* shape می‌شود",
              label.text == '<aa bb>\n<cc dd>', repr(label.text))
        check("ترتیب خطوط = ترتیب خواندن (خط اول با اولین کلمه)", label.text.split('\n')[0].startswith('<aa'))
        label.set_text('x')
        check("set_text دوباره reflow می‌کند", label.text == '<x>', label.text)
        label.set_text('aa bb cc dd')
        label.text_size = (400, None)
        check("عرض بزرگ‌تر شد -> دوباره یک خط", label.text == '<aa bb cc dd>', label.text)
        label.text_size = (None, None)
        check("text_size=(None, None) -> برگشت به یک خط shape‌شده", label.text == '<aa bb cc dd>')
        check("raw_text همیشه نسخه‌ی خام باقی می‌ماند", label.raw_text == 'aa bb cc dd')
        empty = PersianLabel(text='')
        empty.text_size = (50, None)
        check("متن خالی با text_size خطا نمی‌دهد", empty.text == '<>' or empty.text == '')
    finally:
        pw.shape, PersianLabel._measure_logical = real_shape, real_measure

    # مسیر خطای اندازه‌گیری: stub شیء CoreLabel ندارد (مثل Kivy خراب) -> باید به رفتار قبلی برگردد، نه کرش
    Logger.records.clear()
    label = PersianLabel(text='hello world again')
    label.text_size = (30, None)
    check("خطای اندازه‌گیری: بدون استثنا، به متن بدون شکستن برمی‌گردد", label.text == 'hello world again', label.text)
    check("خطای اندازه‌گیری: یک بار هشدار لاگ می‌شود", sum('wrap measurement failed' in m for _l, m in Logger.records) == 1,
          str(Logger.records))
    label.text_size = (20, None)
    check("خطای اندازه‌گیری: دوباره تلاش نمی‌کند و هشدار تکرار نمی‌شود",
          sum('wrap measurement failed' in m for _l, m in Logger.records) == 1)


guarded("label wrapping", label_wrapping)


def top_bar_layout():
    from ui.widgets.common import TopBar
    from ui.widgets.persian_widgets import PersianLabel
    kivy_stub.reset(density=1.0)
    with_back = TopBar('عنوان', on_back=lambda: None)
    buttons = [c for c in with_back.children if isinstance(c, Button)]
    check("TopBar با دکمه‌ی برگشت: دقیقاً دو فرزند (دکمه + عنوان)، بدون فاصله‌ی خالی",
          len(with_back.children) == 2 and len(buttons) == 1, str(len(with_back.children)))
    check("دکمه‌ی برگشت ۸۴dp (متن «بازگشت» ≈۵۱dp جا می‌شود)", buttons[0].width == 84)
    check("عنوان یک PersianLabel است", any(isinstance(c, PersianLabel) for c in with_back.children))
    kivy_stub.set_density(3.0)
    check("عرض دکمه با چگالی ۳ می‌شود ۲۵۲", TopBar('x', on_back=lambda: None).children[-1].width == 252)
    kivy_stub.set_density(1.0)
    check("TopBar بدون on_back فقط عنوان دارد", len(TopBar('x').children) == 1)


guarded("top bar", top_bar_layout)

# ====================================================================
section("۱۰) فاز۹: صفحه‌ی چالش‌ها، چالش روزانه، حالت بی‌نهایت")

import math  # noqa: E402
from datetime import date, timedelta  # noqa: E402

from game_logic import level_generator as lg  # noqa: E402
from game_logic.daily_challenge import DailyChallenge, date_seed, equivalent_level_for  # noqa: E402
from game_logic.endless_mode import EndlessMode, equivalent_level as endless_equivalent  # noqa: E402
from utils.persian_text import shape  # noqa: E402

ZERO_REWARDS = {'coins': 0, 'gems': 0, 'xp': 0}
TOUCH = types.SimpleNamespace(x=200, y=300, pos=(200, 300))


def static_only(level):
    """فقط اهداف ساکن و بدون آینه‌ی چرخان: راه‌حل مولد مستقل از زمان است، پس می‌شود آن را در GameWidget
    بدون هماهنگی لحظه‌ی دقیق شلیک کرد."""
    return (all(t['move_pattern'] == 'static' for t in level.targets)
            and not any(m['type'] == 'rotating_mirror' for m in level.mirrors))


def shoot(gw, solutions):
    """راه‌حل‌های ثابت‌شده‌ی مولد را با همان مسیر واقعی بازی (crosshair -> _fire) شلیک می‌کند."""
    for _index, angle, _t in solutions:
        gw.crosshair_x = gw.gun_x + 300 * math.cos(math.radians(angle))
        gw.crosshair_y = gw.gun_y + 300 * math.sin(math.radians(angle))
        gw.on_touch_up(TOUCH)


def find_static_day():
    start = date(2026, 10, 12)
    return next(day for day in (start + timedelta(days=i) for i in range(200))
                if static_only(DailyChallenge().build_level(day)))


def find_endless_seed(stages=3):
    for seed in range(1, 600):
        run = EndlessMode()
        run.start_run(seed=seed)
        if all(static_only(run.build_level(s)) for s in range(1, stages + 1)):
            return seed
    raise AssertionError('seed مناسب پیدا نشد')


def challenge_screen(app_instance, day=None):
    screen = app_instance.ctx.screen_manager.get_screen('challenges')
    if day is not None:
        screen._today_fn = lambda: day
    app_instance.ctx.screen_manager.goto('challenges', push=False)
    return screen


def challenges_ui():
    a = fresh_app()
    mgr = a.ctx.screen_manager
    menu = mgr.get_screen('main_menu')
    check("منوی اصلی ۹ دکمه دارد (چالش‌ها اضافه شد)", len(pressable_buttons(menu)) == 9, str(len(pressable_buttons(menu))))
    day = date(2026, 10, 9)                         # جمعه
    screen = challenge_screen(a, day)
    check("صفحه‌ی چالش‌ها: ۲ دکمه‌ی شروع (روزانه، بی‌نهایت) + بازگشت", len(pressable_buttons(screen)) == 3,
          str(len(pressable_buttons(screen))))
    texts = [w.text for w in screen.walk() if isinstance(w, Label) and w.text]
    check("روز هفته‌ی فارسی و سختی نمایش داده می‌شود",
          any(shape('جمعه') in x or 'جمعه' in x for x in texts), str(texts[:3]))
    check("هر ۴ دستاورد فهرست شده‌اند", sum(1 for x in texts if shape('بی‌وقفه') in x or 'بی‌وقفه' in x) >= 2
          and len([w for w in screen.walk() if isinstance(w, Label)]) > 20)
    # دکمه را با «رفتار» پیدا می‌کنیم نه با اندیس حدسی (ترتیب فرزندان Kivy معکوس ترتیب افزودن است)
    destinations = []
    for index in range(len(pressable_buttons(menu))):
        probe = fresh_app()
        pressable_buttons(probe.ctx.screen_manager.get_screen('main_menu'))[index].dispatch('on_release')
        destinations.append(probe.ctx.screen_manager.current)
    check("دقیقاً یکی از دکمه‌های منوی اصلی به صفحه‌ی چالش‌ها می‌رود", destinations.count('challenges') == 1,
          str(destinations))


guarded("challenges ui", challenges_ui)


def daily_flow():
    day = find_static_day()
    a = fresh_app()
    ctx, mgr = a.ctx, a.ctx.screen_manager
    screen = challenge_screen(a, day)
    energy = ctx.profile.energy.current_energy
    coins = ctx.profile.economy.coins
    screen._start_daily()
    gw = mgr.get_screen('game').game_widget
    gw.size = (405, 720)
    Clock.tick(frames=4)
    eq = equivalent_level_for(day)
    check("چالش روزانه: صفحه‌ی بازی با برچسب «چالش روزانه»، بدون مصرف انرژی",
          mgr.current == 'game' and gw.is_generated and ctx.profile.energy.current_energy == energy
          and shape('چالش روزانه') in gw._status_label.text, gw._status_label.text)
    _d, info = lg.generate_level(eq, seed=date_seed(day), equivalent_level=eq, rewards=ZERO_REWARDS, with_info=True)
    check("مرحله‌ی روزانه همان خروجی مولد برای همین تاریخ است (تکرارپذیر)",
          gw.condition.total_targets == len(info['solutions']))
    level_before = ctx.level_manager.current_level_id
    shoot(gw, info['solutions'])
    check("با راه‌حل ثابت‌شده‌ی مولد، چالش روزانه واقعاً برده می‌شود", gw.game_over and gw._last_result_success is True)
    check("پاداش روز اول (۶۰ سکه) اعمال شد و استریک ۱ شد",
          ctx.profile.economy.coins - coins == 60 and ctx.profile.daily_challenge.streak == 1
          and ctx.profile.daily_challenge.is_completed(day), str(ctx.profile.economy.coins - coins))
    check("پیام نتیجه: پاداش و استریک (و ماندگار)", shape('چالش روزانه انجام شد') in gw._status_label.text
          or 'چالش روزانه انجام شد' in gw._status_label.text, gw._status_label.text)
    check("چالش رویه‌ای به پیشرفت کمپین دست نمی‌زند (مرحله‌ی جاری/قفل‌ها/نتیجه)",
          ctx.level_manager.current_level_id == level_before and not ctx.level_manager.is_unlocked(2)
          and ctx.level_manager.get_level_result(level_before) is None)
    gw.on_touch_up(TOUCH)
    check("ضربه‌ی بعد از موفقیت -> برگشت به صفحه‌ی چالش‌ها", mgr.current == 'challenges', mgr.current)
    check("برگشت به چالش‌ها: ردیف روزانه حالا «انجام شد» را نشان می‌دهد",
          any('✓' in w.text for w in screen.walk() if isinstance(w, Label)))

    coins_after = ctx.profile.economy.coins
    screen._start_daily()
    gw.size = (405, 720)
    Clock.tick(frames=4)
    shoot(gw, info['solutions'])
    check("بازی دوباره‌ی همان روز: برده می‌شود ولی پاداش دوباره نمی‌دهد",
          gw._last_result_success is True and ctx.profile.economy.coins == coins_after
          and ctx.profile.daily_challenge.total_completed == 1)
    from game_logic.save_manager import SaveManager
    reloaded = SaveManager(db_path=os.path.join(app_data_dir(a), 'save.db')).load(ctx.level_manager)
    check("ذخیره شد: بازخوانی واقعی از SQLite استریک و تکمیل را نگه می‌دارد",
          reloaded.daily_challenge.streak == 1 and reloaded.daily_challenge.is_completed(day)
          and reloaded.daily_challenge.total_completed == 1, str(reloaded.daily_challenge.to_dict()))
    a.on_pause()


guarded("daily flow", daily_flow)


def daily_failure():
    day = find_static_day()
    a = fresh_app()
    ctx, mgr = a.ctx, a.ctx.screen_manager
    screen = challenge_screen(a, day)
    coins = ctx.profile.economy.coins
    screen._start_daily()
    gw = mgr.get_screen('game').game_widget
    gw.size = (405, 720)
    Clock.tick(frames=3)
    Clock.tick(dt=30.0, frames=12)
    check("چالش روزانه: اتمام زمان = شکست", gw.game_over and gw._last_result_success is False)
    check("پیام شکست ماندگار است (HUD رونویسی نمی‌کند)", shape('زمان تمام شد!') in gw._status_label.text
          or 'زمان تمام شد!' in gw._status_label.text, gw._status_label.text)
    gw.on_touch_up(TOUCH)
    check("ضربه‌ی بعد از شکست: همان چالش دوباره شروع می‌شود (رایگان)", gw.is_generated and not gw.game_over
          and mgr.current == 'game' and ctx.profile.economy.coins == coins)
    check("شکست استریک/آمار را عوض نمی‌کند",
          ctx.profile.daily_challenge.streak == 0 and ctx.profile.daily_challenge.total_completed == 0)


guarded("daily failure", daily_failure)


def endless_flow():
    seed = find_endless_seed(3)
    a = fresh_app()
    ctx, mgr = a.ctx, a.ctx.screen_manager
    endless = ctx.profile.endless
    original_start = endless.start_run
    endless.start_run = lambda seed_arg=None: original_start(seed=seed)
    screen = challenge_screen(a, date(2026, 10, 9))
    energy = ctx.profile.energy.current_energy
    coins = ctx.profile.economy.coins
    screen._start_endless()
    gw = mgr.get_screen('game').game_widget
    gw.size = (405, 720)
    Clock.tick(frames=4)
    check("بی‌نهایت: دقیقاً ۱ انرژی برای کل اجرا", ctx.profile.energy.current_energy == energy - 1)
    check("بی‌نهایت: برچسب مرحله‌ی ۱ و زمان محدودتر از کمپین",
          mgr.current == 'game' and shape('بی‌نهایت') in gw._status_label.text or 'بی‌نهایت' in gw._status_label.text)
    gained = 0
    for stage in (1, 2, 3):
        eq = endless_equivalent(stage)
        _d, info = lg.generate_level(eq, seed=seed * 1000 + stage, equivalent_level=eq,
                                     rewards=ZERO_REWARDS, with_info=True)
        shoot(gw, info['solutions'])
        gained += min(25, 3 + stage)
        check(f"بی‌نهایت: مرحله‌ی {stage} با راه‌حل مولد برده شد",
              gw.game_over and gw._last_result_success is True)
        if stage < 3:
            gw.on_touch_up(TOUCH)           # مرحله‌ی بعد
            check(f"ضربه -> مرحله‌ی {stage + 1} (روی همان صفحه، بدون انرژی تازه)",
                  mgr.current == 'game' and not gw.game_over and ctx.profile.energy.current_energy == energy - 1
                  and endless.current_stage == stage + 1)
    check("پاداش سکه‌ی ۳ مرحله اعمال شد (۴+۵+۶)", ctx.profile.economy.coins - coins == gained, str(ctx.profile.economy.coins - coins))
    check("آمار: بهترین مرحله ۳ و ۳ مرحله‌ی تمام‌شده", endless.best_stage == 3 and endless.total_stages_cleared == 3)
    check("بی‌نهایت به پیشرفت کمپین دست نمی‌زند", not ctx.level_manager.is_unlocked(2))
    gw.on_touch_up(TOUCH)                   # مرحله‌ی ۴ -- می‌گذاریم زمانش تمام شود
    Clock.tick(frames=3)
    Clock.tick(dt=30.0, frames=8)
    check("مرحله‌ی ۴: اتمام زمان اجرا را تمام می‌کند", gw.game_over and gw._last_result_success is False
          and not endless.is_running)
    check("پیام پایان اجرا ماندگار است و رکورد را نشان می‌دهد",
          shape('پایان اجرا') in gw._status_label.text or 'پایان اجرا' in gw._status_label.text, gw._status_label.text)
    gw.on_touch_up(TOUCH)
    check("ضربه بعد از پایان اجرا -> صفحه‌ی چالش‌ها", mgr.current == 'challenges', mgr.current)
    check("رکورد ۳ و ۱ اجرا ثبت شد", endless.best_stage == 3 and endless.total_runs == 1)
    a.on_pause()


guarded("endless flow", endless_flow)


def endless_edge_cases():
    a = fresh_app()
    ctx, mgr = a.ctx, a.ctx.screen_manager
    screen = challenge_screen(a, date(2026, 10, 9))
    while ctx.profile.energy.current_energy > 0:
        ctx.profile.energy.consume(1)
    screen._start_endless()
    check("بدون انرژی: اجرا شروع نمی‌شود و پیام می‌آید", mgr.current == 'challenges'
          and not ctx.profile.endless.is_running and screen.feedback_label.text != '')

    b = fresh_app()
    ctx, mgr = b.ctx, b.ctx.screen_manager
    screen = challenge_screen(b, date(2026, 10, 9))
    screen._start_endless()
    gw = mgr.get_screen('game').game_widget
    gw.size = (405, 720)
    Clock.tick(frames=3)
    check("(پیش‌شرط) اجرا در جریان است", ctx.profile.endless.is_running)
    check("Back سخت‌افزاری وسط اجرا -> صفحه‌ی چالش‌ها", Window.fire_keyboard(27) and mgr.current == 'challenges', mgr.current)
    check("بازگشت وسط اجرا، اجرا را تمام می‌کند (دیگر در جریان نیست)", not ctx.profile.endless.is_running)

    c = fresh_app()
    ctx, mgr = c.ctx, c.ctx.screen_manager
    screen = challenge_screen(c, date(2026, 10, 9))
    results = []
    for how in ('on_screen', 'hardware'):
        d = fresh_app()
        m2 = d.ctx.screen_manager
        s2 = challenge_screen(d, date(2026, 10, 9))
        s2._start_daily()
        if how == 'on_screen':
            m2.get_screen('game').exit_button.dispatch('on_release')
        else:
            Window.fire_keyboard(27)
        results.append(m2.current)
    check(f"چالش روزانه: دکمه‌ی «خروج» و Back سخت‌افزاری هر دو به چالش‌ها می‌روند ({results[0]})",
          results[0] == results[1] == 'challenges', str(results))


guarded("endless edge cases", endless_edge_cases)


def streak_achievement_via_missions():
    a = fresh_app()
    ctx, mgr = a.ctx, a.ctx.screen_manager
    profile = ctx.profile
    profile.daily_rewards.current_streak = 24
    profile.daily_rewards.last_claim_date = (date.today() - timedelta(days=1)).isoformat()
    gems = profile.economy.gems
    mgr.goto('missions', push=False)
    screen = mgr.get_screen('missions')
    screen._claim_daily_reward()
    check("استریک جایزه‌ی روزانه به ۲۵ رسید -> دستاورد streak_25 باز می‌شود",
          profile.daily_rewards.current_streak == 25 and profile.achievements.is_unlocked('streak_25'))
    check("جواهر دستاورد (۵) اضافه شد (به‌علاوه‌ی جایزه‌ی روز)", profile.economy.gems - gems >= 5, str(profile.economy.gems - gems))
    check("پیام دریافت جایزه از دستاورد خبر می‌دهد", 'دستاورد' in screen.feedback_label.text
          or shape('دستاورد') in screen.feedback_label.text, screen.feedback_label.text)


guarded("streak achievement", streak_achievement_via_missions)

# ====================================================================
for directory in _tmp_dirs:
    shutil.rmtree(directory, ignore_errors=True)

print(f"\n=== نتیجه: {passed} OK, {failed} FAIL ===")
sys.exit(1 if failed else 0)
