"""
tests/test_phase10.py  (فاز ۱۰)

صدای واقعی، آیکن/presplash، پیام HUD که دیگر بریده نمی‌شود، راهنمای مرحله، لرزش واقعی صحنه،
صدای لمس دکمه‌ها، و بازتوازن اقتصاد با ۱۰۰ مرحله‌ی واقعی. Kivy ساختگی (مثل test_ui_smoke).

اجرا:  python tests/test_phase10.py
"""
import glob
import json
import os
import re
import shutil
import struct
import sys
import tempfile
import traceback
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))

import kivy_stub  # noqa: E402

kivy_stub.install()
from kivy_stub import Clock, dp  # noqa: E402

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


def guarded(name, fn):
    try:
        fn()
    except Exception:
        global failed
        failed += 1
        tb = traceback.format_exc().strip().splitlines()
        print(f"  FAIL {name}  استثنا:")
        for line in tb[-6:]:
            print(f"         {line}")


def fresh_app(density=1.0):
    data_dir = tempfile.mkdtemp(prefix='lr_p10_')
    _tmp_dirs.append(data_dir)
    kivy_stub.reset(density=density, user_data_dir=data_dir)
    import main
    app = main.LaserRicochetApp()
    app.start_for_test()
    return app


TOUCH = types.SimpleNamespace(x=200, y=300, pos=(200, 300))

# ====================================================================
section("۱) فایل‌های صوتی واقعی (assets/audio)")

from core import audio_manager as am  # noqa: E402

AUDIO_DIR = os.path.join(ROOT, 'assets', 'audio')
expected = {f for files in am.SFX_VARIANTS.values() for f in files} | set(am.MUSIC_TRACKS.values())
present = {os.path.basename(p) for p in glob.glob(os.path.join(AUDIO_DIR, '*.ogg'))}
check("هر فایلِ SFX_VARIANTS/MUSIC_TRACKS واقعاً وجود دارد", expected <= present, str(sorted(expected - present)))
check("فایل اضافه‌ی بی‌مصرف در پوشه نیست", present <= expected, str(sorted(present - expected)))
check(f"تعداد کل فایل‌ها ۱۵ است ({len(expected)})", len(expected) == 15)

bad_header = []
bad_size = []
for name in sorted(expected):
    path = os.path.join(AUDIO_DIR, name)
    if not os.path.isfile(path):
        continue
    with open(path, 'rb') as fh:
        head = fh.read(64)
    # صفحه‌ی اول OGG: 'OggS' و بسته‌ی شناسه‌ی Vorbis (0x01 + 'vorbis')
    if not (head[:4] == b'OggS' and b'\x01vorbis' in head):
        bad_header.append(name)
    size = os.path.getsize(path)
    if not (1500 <= size <= 200 * 1024):
        bad_size.append((name, size))
check("همه‌ی فایل‌ها OGG/Vorbis معتبرند (هدر)", not bad_header, str(bad_header))
check("اندازه‌ی هر فایل منطقی است (۱٫۵KB تا ۲۰۰KB)", not bad_size, str(bad_size))
total = sum(os.path.getsize(os.path.join(AUDIO_DIR, n)) for n in present)
check(f"حجم کل صدا زیر ۵۰۰KB است ({total // 1024}KB)", total < 500 * 1024, str(total))

from tools import generate_audio as ga  # noqa: E402

synth = ga.build_all()
check("نام فایل‌های مولد دقیقاً همان‌هایی‌اند که AudioManager می‌خواهد",
      set(synth) == {os.path.splitext(f)[0] for f in expected}, str(set(synth) ^ {os.path.splitext(f)[0] for f in expected}))
loud_enough, finite = [], []
for name, samples in synth.items():
    norm = ga.normalize(samples, 0.85)
    peak = max(abs(v) for v in norm)
    if peak < 0.5:
        loud_enough.append((name, peak))
    if any(v != v or abs(v) == float('inf') for v in samples):
        finite.append(name)
check("هیچ افکتی ساکت/ناتمام نیست (قله بعد از نرمال‌سازی ≥ ۰٫۵)", not loud_enough, str(loud_enough))
check("نمونه‌ها NaN/∞ ندارند", not finite, str(finite))
for name in ('shot_fire_1', 'mirror_hit_1', 'button_tap', 'level_win'):
    d = len(synth[name]) / ga.SR
    check(f"طول {name} منطقی است ({d:.2f}s)", 0.03 <= d <= 1.2, str(d))
for name in ('menu_theme', 'gameplay_theme'):
    s = synth[name]
    d = len(s) / ga.SR
    check(f"{name}: طول حلقه ۱۰ تا ۳۰ ثانیه ({d:.1f}s)", 10 <= d <= 30)
    check(f"{name}: ابتدا و انتهای صفر => حلقه بدون تق", abs(s[0]) < 1e-3 and abs(s[-1]) < 1e-3, f"{s[0]} {s[-1]}")
variants = {n: synth[n] for n in ('mirror_hit_1', 'mirror_hit_2', 'mirror_hit_3')}
check("سه نسخه‌ی mirror_hit واقعاً فرق دارند (تنوع به‌جای pitch)",
      len({tuple(round(v, 4) for v in s[:400]) for s in variants.values()}) == 3)
again = ga.sfx_shot_fire(1)
check("سنتز قطعی است (دو بار اجرا => نمونه‌های یکسان)", again == synth['shot_fire_1'])

# ====================================================================
section("۲) AudioManager: مسیر مطلق و پخش واقعی فایل‌های موجود")

check("DEFAULT_AUDIO_DIR مطلق است (نه وابسته به cwd)", os.path.isabs(am.DEFAULT_AUDIO_DIR), am.DEFAULT_AUDIO_DIR)
check("DEFAULT_AUDIO_DIR به همین پروژه اشاره می‌کند", os.path.samefile(am.DEFAULT_AUDIO_DIR, AUDIO_DIR))


class _FakeSound:
    def __init__(self, path):
        self.path = path
        self.plays = 0
        self.loop = False

    def play(self):
        self.plays += 1

    def stop(self):
        pass


class _FakeLoader:
    loaded = []

    @classmethod
    def load(cls, path):
        sound = _FakeSound(path)
        cls.loaded.append(sound)
        return sound


_real_loader = am.SoundLoader
am.SoundLoader = _FakeLoader
cwd_before = os.getcwd()
tmp_cwd = tempfile.mkdtemp(prefix='lr_cwd_')
_tmp_dirs.append(tmp_cwd)
os.chdir(tmp_cwd)   # cwd عمداً جای دیگر: قبلاً مسیر نسبی بی‌صدا شکست می‌خورد
try:
    am.AudioManager._reset_instance_for_testing()
    mgr = am.AudioManager()
    for sfx in am.SFX_VARIANTS:
        mgr.play_sfx(sfx)
    played = [s for s in _FakeLoader.loaded if s.plays]
    check("برای هر ۹ افکت یک فایل واقعی بارگذاری و پخش شد (حتی با cwd متفاوت)",
          len(played) == len(am.SFX_VARIANTS), f"{len(played)} از {len(am.SFX_VARIANTS)}")
    mgr.play_music('menu')
    music = [s for s in _FakeLoader.loaded if s.path.endswith('menu_theme.ogg')]
    check("موسیقی‌ی منو بارگذاری، حلقه و پخش شد", music and music[0].loop is True and music[0].plays == 1)
finally:
    os.chdir(cwd_before)
    am.SoundLoader = _real_loader
    am.AudioManager._reset_instance_for_testing()

# --- خرابی ارائه‌دهنده‌ی صدا هرگز نباید بازی را بشکند ---
class _ExplodingLoader:
    @classmethod
    def load(cls, path):
        raise RuntimeError('SDL_mixer: cannot open audio device')


class _BrokenSound(_FakeSound):
    def play(self):
        raise RuntimeError('audio device lost')

    def stop(self):
        raise RuntimeError('audio device lost')


class _BrokenPlayLoader:
    @classmethod
    def load(cls, path):
        return _BrokenSound(path)


try:
    am.SoundLoader = _ExplodingLoader
    am.AudioManager._reset_instance_for_testing()
    mgr = am.AudioManager()
    try:
        mgr.play_sfx('mirror_hit')
        mgr.play_music('menu')
        check("SoundLoader.load استثنا بدهد => play_sfx/play_music بی‌صدا ادامه می‌دهند (بدون کرش)", True)
    except Exception as exc:  # noqa: BLE001
        check("SoundLoader.load استثنا بدهد => بدون کرش", False, repr(exc))

    am.SoundLoader = _BrokenPlayLoader
    am.AudioManager._reset_instance_for_testing()
    mgr = am.AudioManager()
    try:
        mgr.play_sfx('shot_fire')
        mgr.play_music('gameplay')
        mgr.stop_music()
        mgr.play_music('menu')
        check("sound.play/stop استثنا بدهند => بدون کرش", True)
    except Exception as exc:  # noqa: BLE001
        check("sound.play/stop استثنا بدهند => بدون کرش", False, repr(exc))
    check("موسیقی‌ای که play نشد به‌عنوان «در حال پخش» ثبت نمی‌شود", mgr._music_sound is None)
finally:
    am.SoundLoader = _real_loader
    am.AudioManager._reset_instance_for_testing()

# ====================================================================
section("۳) آیکن، presplash و buildozer.spec")


def png_size(path):
    with open(path, 'rb') as fh:
        head = fh.read(24)
    if head[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    return struct.unpack('>II', head[16:24])


for fname in ('icon.png', 'presplash.png'):
    path = os.path.join(ROOT, 'assets', fname)
    check(f"{fname} وجود دارد و PNG معتبر ۵۱۲×۵۱۲ است", os.path.isfile(path) and png_size(path) == (512, 512),
          str(png_size(path) if os.path.isfile(path) else 'missing'))

spec = open(os.path.join(ROOT, 'buildozer.spec'), encoding='utf-8').read()


def spec_value(key):
    m = re.search(r'^' + re.escape(key) + r'\s*=\s*(.+?)\s*$', spec, re.M)
    return m.group(1) if m else None


icon_value = spec_value('icon.filename')
check("spec: icon.filename تنظیم و فایلش موجود است",
      icon_value is not None and os.path.isfile(os.path.join(ROOT, icon_value.replace('%(source.dir)s/', ''))), str(icon_value))
pre_value = spec_value('presplash.filename')
check("spec: presplash.filename تنظیم و فایلش موجود است",
      pre_value is not None and os.path.isfile(os.path.join(ROOT, pre_value.replace('%(source.dir)s/', ''))), str(pre_value))
icons_src = open(os.path.join(ROOT, 'tools', 'generate_icons.py'), encoding='utf-8').read()
tool_color = re.search(r"PRESPLASH_COLOR\s*=\s*'(#[0-9A-Fa-f]{6})'", icons_src)
check("رنگ presplash در spec با ابزار تولید یکی است",
      tool_color is not None and spec_value('android.presplash_color') == tool_color.group(1),
      f"{spec_value('android.presplash_color')} vs {tool_color.group(1) if tool_color else None}")
exts = (spec_value('source.include_exts') or '').split(',')
check("پسوندهای png و ogg در بسته‌ی APK هستند", 'png' in exts and 'ogg' in exts, str(exts))

# ====================================================================
section("۴) HUD: پیام بلند بریده نمی‌شود + راهنمای مرحله")

from ui.screens import game_screen as gs  # noqa: E402
from ui.widgets.persian_widgets import PersianButton, PersianLabel  # noqa: E402
from utils.persian_text import shape  # noqa: E402


def hud_and_hints():
    a = fresh_app()
    ctx, mgr = a.ctx, a.ctx.screen_manager
    mgr.get_screen('level_select')._start_level(1)
    gw = mgr.get_screen('game').game_widget
    gw.size = (405, 720)
    Clock.tick(frames=3)
    label = gw._status_label

    reserved = dp(gs.HUD_RESERVED_RIGHT_DP)
    check("HUD: عرض برچسب وضعیت در فضای چپِ دکمه‌ی «خروج» می‌ماند", label.right <= gw.right - reserved + 1e-6,
          f"{label.right} > {gw.right - reserved}")
    check("HUD: text_size عرض دارد (پیام بلند می‌شکند، بریده نمی‌شود)",
          label.text_size and label.text_size[0] and label.text_size[0] <= label.width, str(label.text_size))
    check("HUD: وسط‌چین و مرکز عمودی", label.halign == 'center' and label.valign == 'middle')

    exit_btn = mgr.get_screen('game').exit_button
    exit_left = exit_btn.x if hasattr(exit_btn, 'x') else gw.right - dp(96)
    check("HUD: دکمه‌ی خروج با برچسب وضعیت همپوشانی ندارد (عرض صفحه ۴۰۵dp)",
          label.right <= gw.width * 0.985 - dp(96) + 1e-6 or label.right <= exit_left + 1e-6,
          f"label.right={label.right} exit_left≈{gw.width * 0.985 - dp(96)}")

    short = 'مرحله ۱'
    mid = 'ا' * 60
    long_ = 'ا' * 120
    f_short, f_mid, f_long = (gs.GameWidget._hud_font_for(x) for x in (short, mid, long_))
    check("اندازه‌ی فونت با طول متن کوچک می‌شود (۱۶ > ۱۴ > ۱۲)",
          (f_short, f_mid, f_long) == ('16sp', '14sp', '12sp'), str((f_short, f_mid, f_long)))
    gw._say('ا' * 120)
    check("_say: متن بلند => فونت ۱۲sp روی برچسب ست شد", label.font_size == '12sp', str(label.font_size))

    # همه‌ی پیام‌های واقعی بازی باید در ۳ خط با ۱۲sp جا شوند: تقریب محافظه‌کارانه ۰٫۶ × font_px برای هر حرف
    messages = [
        "تبریک! هر ۱۰۰ مرحله‌ی کمپین رو کامل کردی -- لمس کن تا برگردی به لیست مراحل.",
        "انرژی تمام شد! تا انرژی بعدی: 12:34 -- یا از فروشگاه بخر.",
        "مرحله تمام شد! -- بی‌نقص! (امتیاز: ۳/۳)  +46 سکه -- لمس کن تا ادامه بدی",
        "زمان تمام شد! لمس کن تا دوباره امتحان کنی.",
    ]
    worst = 0
    for msg in messages:
        px = float(gs.GameWidget._hud_font_for(msg).replace('sp', '')) * 1.0
        per_line = (label.text_size[0]) / (0.6 * px)
        worst = max(worst, -(-len(msg) // int(per_line)))
    check("بلندترین پیام‌های واقعی بازی در ≤ ۳ خط (ارتفاع ۶۰dp) جا می‌شوند", worst <= 3, str(worst))

    # --- راهنما ---
    level1 = ctx.level_manager.load_level(1)
    hint_text = level1.hints[0]
    check("راهنمای مرحله‌ی ۱ (از JSON) روی صفحه است", gw._hint_label.raw_text == hint_text, repr(gw._hint_label.raw_text))
    check("برچسب راهنما پایین صفحه است (نه روی HUD بالا)", gw._hint_label.y < gw.height * 0.2, str(gw._hint_label.y))
    Clock.tick(dt=1.0, frames=3)
    check("راهنما بعد از ۳ ثانیه هنوز هست", gw._hint_label.raw_text == hint_text)
    Clock.tick(dt=1.0, frames=6)
    check(f"راهنما بعد از {gs.HINT_SECONDS:.0f} ثانیه محو شد", gw._hint_label.raw_text == '', repr(gw._hint_label.raw_text))

    # با اولین شلیک محو می‌شود
    gw._start_level(1, practice=True)
    Clock.tick(frames=2)
    check("شروع دوباره: راهنما دوباره نمایش داده می‌شود", gw._hint_label.raw_text == hint_text)
    gw.on_touch_down(TOUCH)
    Clock.tick(frames=30)
    gw.on_touch_up(TOUCH)
    check("اولین شلیک راهنما را پنهان می‌کند", gw._hint_label.raw_text == '' and gw._hint_remaining == 0.0)

    # مرحله‌ی تولیدی هم راهنمای خودش را دارد (فایل ۶ تا ۱۰۰)
    level6 = ctx.level_manager.load_level(6)
    gw._start_level(6, practice=True)
    Clock.tick(frames=2)
    check("مرحله‌ی ۶ (تولیدی): راهنمای فارسی نمایش داده می‌شود",
          level6.hints and gw._hint_label.raw_text == level6.hints[0], repr(gw._hint_label.raw_text))

    # مرحله‌ی بدون راهنما => برچسب خالی، بدون خطا
    level6.hints = []
    gw._show_hint(level6)
    check("مرحله‌ی بدون hint: برچسب خالی و تایمر صفر", gw._hint_label.raw_text == '' and gw._hint_remaining == 0.0)
    level6.hints = [123]
    gw._show_hint(level6)
    check("hint غیررشته‌ای (فایل خراب) کرش نمی‌کند", gw._hint_label.raw_text == '')


guarded("HUD/hints", hud_and_hints)


def label_dedupe():
    kivy_stub.reset(density=1.0, user_data_dir=tempfile.mkdtemp(prefix='lr_p10_'))
    lab = PersianLabel(text='سلام', size_hint=(None, None))
    calls = []
    original = lab._reflow
    lab._reflow = lambda *a: (calls.append(1), original(*a))[1]
    lab.set_text('سلام')
    lab.set_text('سلام')
    check("PersianLabel.set_text: همان متن => بدون بازچینش (۶۰ بار در ثانیه در HUD)", not calls, str(len(calls)))
    lab.set_text('خداحافظ')
    check("متن جدید => بازچینش و متن shape شده", len(calls) == 1 and lab.text == shape('خداحافظ'))
    empty = PersianLabel(text='')
    check("برچسب با متن خالیِ اولیه هم مقداردهی می‌شود", empty._applied and empty.text == '')


guarded("label dedupe", label_dedupe)

# ====================================================================
section("۵) لرزش واقعی صحنه (Translate) به‌جای جابه‌جایی pos")

from ui.effects.screen_shake import AdvancedScreenShake  # noqa: E402


def real_shake():
    a = fresh_app()
    mgr = a.ctx.screen_manager
    mgr.get_screen('level_select')._start_level(1)
    gw = mgr.get_screen('game').game_widget
    gw.size = (405, 720)
    Clock.tick(frames=3)
    check("GameWidget یک shake_translate دارد", hasattr(gw, 'shake_translate'))
    before = [type(c).__name__ for c in gw.canvas.before.children]
    after = [type(c).__name__ for c in gw.canvas.after.children]
    check("canvas.before: PushMatrix + Translate + canvas صحنه؛ canvas.after: PopMatrix",
          before == ['PushMatrix', 'Translate', '_Canvas'] and after == ['PopMatrix']
          and gw.canvas.before.children[2] is gw._scene_canvas, f"{before} {after}")

    rebuilds = []
    original_build = gw._build_static_canvas
    gw._build_static_canvas = lambda *a, **k: (rebuilds.append(1), original_build(*a, **k))[1]
    pos_before = tuple(gw.pos)
    seen = []
    gw.screen_shake.shake(amplitude=20.0, duration=0.2)
    for _ in range(14):
        Clock.tick(dt=1 / 60.0, frames=1)
        seen.append(gw.shake_translate.xy)
    check("لرزش: translate واقعاً غیرصفر می‌شود", any(abs(x) > 1e-6 or abs(y) > 1e-6 for x, y in seen), str(seen[:3]))
    check("لرزش: دامنه از amplitude بیشتر نمی‌شود",
          all(abs(x) <= 20.0 + 1e-6 and abs(y) <= 20.0 + 1e-6 for x, y in seen))
    check("لرزش: pos ویجت دست نمی‌خورد", tuple(gw.pos) == pos_before)
    check("لرزش: هیچ بازسازی کامل canvas رخ نمی‌دهد (قبلاً هر فریم)", not rebuilds, str(len(rebuilds)))
    Clock.tick(dt=1 / 60.0, frames=30)
    check("پایان لرزش: translate دقیقاً (۰،۰) و اسکجول متوقف", gw.shake_translate.xy == (0.0, 0.0)
          and not gw.screen_shake.active)

    # شروع دوباره وسط لرزش قبلی: نباید نشتی/ریشه‌ی دوم بسازد
    gw.screen_shake.shake(amplitude=10.0, duration=0.5)
    Clock.tick(dt=1 / 60.0, frames=5)
    gw.screen_shake.shake(amplitude=10.0, duration=0.1)
    Clock.tick(dt=1 / 60.0, frames=30)
    check("شروع دوباره‌ی لرزش وسط لرزش: در نهایت دوباره صفر", gw.shake_translate.xy == (0.0, 0.0))

    # رفتار قبلی برای ویجتی بدون translate (سازگار با گذشته)
    plain = types.SimpleNamespace(pos=(10.0, 20.0))
    shaker = AdvancedScreenShake(plain)
    shaker.shake(amplitude=5.0, duration=0.1)
    Clock.tick(dt=1 / 60.0, frames=3)
    moved = tuple(plain.pos) != (10.0, 20.0)
    Clock.tick(dt=1 / 60.0, frames=20)
    check("ویجت بدون translate: هنوز با pos می‌لرزد و در پایان برمی‌گردد", moved and tuple(plain.pos) == (10.0, 20.0),
          str(plain.pos))

    # هشدار کم‌بودن زمان (۲۰٪ آخر) از همین مسیر Translate می‌لرزاند
    gw._start_level(1, practice=True)
    Clock.tick(frames=2)
    shakes = []
    original_shake = gw.screen_shake.shake
    gw.screen_shake.shake = lambda *a, **k: (shakes.append(k), original_shake(*a, **k))[1]
    Clock.tick(dt=10.0, frames=25)          # ۲۵۰ از ۳۰۰ ثانیه => ۱۶٪ باقی (< ۲۰٪)
    check("هشدار کم‌بودن زمان: یک‌بار لرزش (نه هر فریم)", gw._warning_played and len(shakes) == 1, str(len(shakes)))


guarded("real shake", real_shake)

# ====================================================================
section("۵.۵) ساختار canvas: HUD با بازسازی صحنه از درخت رسم حذف نمی‌شود")


def hud_survives_rebuild():
    a = fresh_app()
    mgr = a.ctx.screen_manager
    mgr.get_screen('level_select')._start_level(1)
    gw = mgr.get_screen('game').game_widget
    gw.size = (405, 720)
    Clock.tick(frames=3)

    def orphans():
        # Kivy واقعی: canvas هر فرزند داخل canvas والد است؛ اگر نباشد، فرزند رسم نمی‌شود.
        return [type(c).__name__ for c in gw.children if c.canvas not in gw.canvas.children]

    check("HUD: حداقل ۴ فرزند (وضعیت، اقتصاد، راهنما، حلقه‌ی تایمر)", len(gw.children) >= 4, str(len(gw.children)))
    check("بعد از بارگذاری مرحله: canvas همه‌ی فرزندان HUD هنوز در درخت رسم است", not orphans(), str(orphans()))
    gw._build_static_canvas()
    check("بعد از بازسازی مستقیم صحنه هم HUD سر جایش است", not orphans(), str(orphans()))
    gw.size = (500, 900)
    Clock.tick(frames=2)
    check("بعد از تغییر اندازه (چرخش/تغییر پنجره) هم HUD سر جایش است", not orphans(), str(orphans()))
    gw._start_level(2, practice=True)
    Clock.tick(frames=2)
    check("بعد از شروع مرحله‌ی دیگر هم HUD سر جایش است", not orphans(), str(orphans()))
    check("صحنه در canvas اختصاصی رسم می‌شود (instructionهای مرحله داخل آن‌اند)",
          len(gw._scene_canvas.children) > 5, str(len(gw._scene_canvas.children)))
    check("canvas اصلی فقط canvas فرزندان را دارد (هیچ Line/Ellipse مرحله‌ای در آن نیست)",
          all(c in [ch.canvas for ch in gw.children] for c in gw.canvas.children),
          str([type(c).__name__ for c in gw.canvas.children]))
    check("ذرات و پرتو داخل canvas صحنه‌اند (زیر HUD)",
          gw._particle_group in gw._scene_canvas.children and gw._beam_group in gw._scene_canvas.children)
    check("canvas صحنه با rebuild خالی/دوباره‌پر می‌شود، نه انباشته",
          (lambda n1: (gw._build_static_canvas(), len(gw._scene_canvas.children) == n1)[1])(len(gw._scene_canvas.children)))


guarded("HUD survives rebuild", hud_survives_rebuild)

# ====================================================================
section("۶) صدای لمس دکمه‌ها")


def tap_sound():
    a = fresh_app()
    check("main.py هوک tap_sound را ست کرده است", PersianButton.tap_sound is not None)
    played = []
    a.ctx.audio_manager.play_sfx = lambda name: played.append(name)
    btn = PersianButton(text='آزمون')
    btn.on_press()
    check("on_press دکمه => button_tap پخش می‌شود", played == ['button_tap'], str(played))

    def boom():
        raise RuntimeError('sound backend exploded')

    old = PersianButton.tap_sound
    PersianButton.tap_sound = boom
    try:
        btn.on_press()
        check("خرابی صدا لمس را نمی‌شکند (استثنا بلعیده و لاگ می‌شود)", True)
    except Exception as exc:  # noqa: BLE001
        check("خرابی صدا لمس را نمی‌شکند", False, repr(exc))
    finally:
        PersianButton.tap_sound = old
    PersianButton.tap_sound = None
    btn.on_press()
    check("بدون هوک (None) هم on_press امن است", True)
    PersianButton.tap_sound = old


guarded("tap sound", tap_sound)

# ====================================================================
section("۷) اقتصاد: بازتوازن با ۱۰۰ مرحله‌ی واقعی")

from game_logic import economy_manager as em  # noqa: E402

coins = [json.load(open(p, encoding='utf-8'))['rewards']['coins']
         for p in sorted(glob.glob(os.path.join(ROOT, 'assets', 'levels', 'level_*.json')))]
real_avg = sum(coins) / len(coins)
check(f"۱۰۰ فایل مرحله ({len(coins)})", len(coins) == 100)
check(f"AVG_COINS_PER_LEVEL ({em.AVG_COINS_PER_LEVEL}) با میانگین واقعی فایل‌ها ({real_avg:.2f}) هم‌خوان است",
      abs(em.AVG_COINS_PER_LEVEL - real_avg) <= 1.0, f"{em.AVG_COINS_PER_LEVEL} vs {real_avg}")

shop = {i['id']: i for i in json.load(open(os.path.join(ROOT, 'data', 'shop_items.json'), encoding='utf-8'))}
bal = em.EconomyBalance()
avg_daily = bal.calculate_daily_income('average')['coins']
active_daily = bal.calculate_daily_income('active')['coins']
casual_daily = bal.calculate_daily_income('casual')['coins']
days_to_gun = shop['gun_precision']['cost_coins'] / avg_daily
check(f"بازیکن معمولی گران‌ترین سلاح را در ۲ تا ۸ روز می‌خرد ({days_to_gun:.1f} روز)", 2.0 <= days_to_gun <= 8.0)
check("بازیکن فعال همان را در ≥ ۱ روز (نه همان‌روز بی‌دردسر)",
      shop['gun_precision']['cost_coins'] / active_daily >= 1.0)
check("بازیکن کم‌بازی (casual) هم در ≤ ۲۰ روز می‌خرد", shop['gun_precision']['cost_coins'] / casual_daily <= 20.0,
      str(shop['gun_precision']['cost_coins'] / casual_daily))
check("قیمت‌ها: تندشلیک < دقیق (ترتیب قیمت حفظ شد)", shop['gun_rapid']['cost_coins'] < shop['gun_precision']['cost_coins'])
check("قیمت جواهری آیتم‌ها دست‌نخورده (۳۰/۴۵/۲۰/۶۰/۶۰)",
      [shop[k]['cost_gems'] for k in ('shot_piercing', 'shot_splitting', 'helper_skip_level',
                                       'upgrade_regen_speed', 'upgrade_coin_bonus')] == [30, 45, 20, 60, 60])

# ====================================================================
section("۸) آمادگی برای GitHub: workflow، .gitignore، مسیرها")

import subprocess  # noqa: E402

wf_path = os.path.join(ROOT, '.github', 'workflows', 'build-apk.yml')
check("workflow در مسیر درست ریپو است (.github/workflows/، در ریشه)", os.path.isfile(wf_path))
wf_text = open(wf_path, encoding='utf-8').read()

# هر دستور `python <path>` داخل workflow باید به فایل واقعی اشاره کند
run_paths = set(re.findall(r'run:\s*python\s+(\S+\.py)', wf_text))
missing_refs = sorted(p for p in run_paths if not os.path.isfile(os.path.join(ROOT, p)))
check(f"همه‌ی مسیرهای python داخل workflow وجود دارند ({len(run_paths)})", run_paths and not missing_refs, str(missing_refs))
bundle_ref = re.search(r'python\s+tools/preflight\.py\s+--bundle', wf_text)
check("گام cross-check باندل از ‎--bundle پشتیبانی می‌کند", bundle_ref is not None and '--bundle' in open(
    os.path.join(ROOT, 'tools', 'preflight.py'), encoding='utf-8').read())

# هیچ فایل tests/test_*.py نباید از CI جا بیفتد
all_tests = sorted(glob.glob(os.path.join(ROOT, 'tests', 'test_*.py')))
unreferenced = [os.path.basename(t) for t in all_tests if 'tests/' + os.path.basename(t) not in run_paths]
check(f"هر {len(all_tests)} فایل تست در workflow اجرا می‌شود (هیچ‌کدام جا نیفتاده)", not unreferenced, str(unreferenced))

try:
    import yaml
except Exception:  # noqa: BLE001 -- در CI ممکن است نصب نباشد؛ بررسی regex پایین کفایت می‌کند
    yaml = None
if yaml is not None:
    doc = yaml.safe_load(wf_text)
    triggers = doc.get('on', doc.get(True))
    check("push روی main و master فعال است", set(triggers['push']['branches']) >= {'main', 'master'}, str(triggers['push']))
    check("tag های v* و اجرای دستی (workflow_dispatch) فعال‌اند",
          'v*' in triggers['push'].get('tags', []) and 'workflow_dispatch' in triggers)
    jobs = doc['jobs']
    check("job ها: preflight -> build -> release", list(jobs) == ['preflight', 'build', 'release'], str(list(jobs)))
    check("build منتظر preflight است و روی PR اجرا نمی‌شود",
          jobs['build']['needs'] == 'preflight' and "pull_request" in jobs['build']['if'])
    check("پایتون preflight همان ۳٫۱۱ داخل APK است",
          any(st.get('with', {}).get('python-version') == '3.11' for st in jobs['preflight']['steps']))
    uses = [st.get('uses', '') for j in jobs.values() for st in j['steps'] if st.get('uses')]
    check("همه‌ی actionها نسخه‌ی مشخص دارند (@vN)", all('@' in u for u in uses), str([u for u in uses if '@' not in u]))
else:
    check("push روی main و master فعال است (بررسی متنی)", re.search(r'branches:\s*\[main,\s*master\]', wf_text) is not None)
    check("workflow_dispatch فعال است (بررسی متنی)", 'workflow_dispatch' in wf_text)

# .gitignore نباید هیچ فایلِ لازمِ پروژه را کنار بگذارد (مثلاً *.log یا bin/ که روی آسیب بزند)
git_bin = shutil.which('git')
if git_bin:
    tmp_repo = tempfile.mkdtemp(prefix='lr_git_')
    _tmp_dirs.append(tmp_repo)
    subprocess.run([git_bin, 'init', '-q', tmp_repo], check=True)
    shutil.copy(os.path.join(ROOT, '.gitignore'), os.path.join(tmp_repo, '.gitignore'))
    project_files = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git')]
        for fname in files:
            project_files.append(os.path.relpath(os.path.join(base, fname), ROOT).replace(os.sep, '/'))
    res = subprocess.run([git_bin, '-C', tmp_repo, 'check-ignore', '--stdin'], input='\n'.join(project_files),
                         capture_output=True, text=True)
    ignored = [line for line in res.stdout.splitlines() if line.strip()]
    allowed = [f for f in ignored if os.path.basename(f).startswith('save.db') or f.endswith('.pyc')]
    unexpected = sorted(set(ignored) - set(allowed))
    check(f"هیچ فایل لازم پروژه توسط .gitignore حذف نمی‌شود ({len(project_files)} فایل بررسی شد)", not unexpected,
          str(unexpected[:5]))
    must = ['.github/workflows/build-apk.yml', 'buildozer.spec', 'main.py', 'requirements.txt', 'assets/icon.png',
            'assets/presplash.png', 'assets/fonts/DejaVuSans.ttf'] + ['assets/audio/' + n for n in sorted(expected)]
    absent = [m for m in must if m not in project_files]
    check("فایل‌های حیاتی (workflow, spec, آیکن, فونت, ۱۵ صدا) روی دیسک هستند", not absent, str(absent))
else:
    print("  SKIP بررسی .gitignore (git نصب نیست)")

# =========================================================================

# ====================================================================
for directory in _tmp_dirs:
    shutil.rmtree(directory, ignore_errors=True)

print(f"\n=== نتیجه: {passed} OK, {failed} FAIL ===")
sys.exit(1 if failed else 0)
