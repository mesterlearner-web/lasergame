"""
ui/screens/game_screen.py  (فاز ۵، بسط فاز۶)

GameWidget همون منطق فاز۱ تا ۴ است (رسم/لمس/raycast/تایمر/اقتصاد)،
پورت‌شده به معماری AppContext (به‌جای ساختن LevelManager/
DifficultyManager/SaveManager مخصوص به خودش) + دو قابلیت تازه‌ی فاز۵:
حالت تمرین (practice، بدون مصرف انرژی/بدون تأثیر روی پیشرفت) و ثبت
ستاره (calculate_stars) برای LevelSelectScreen.

فاز۶ (لایه‌ی Juice، بخش ۵.۷): رنگ‌های صحنه از ColorPalette حساس به
رنگ‌کوری (بخش۵.۱۶)، انفجار هدف با AdvancedParticleSystem (نه Entity
دستی)، لرزش صفحه روی برخورد با مانع + هشدار کم‌بودن زمان، حلقه‌ی
تایمر (TimerRing)، و صدا برای شلیک/برخورد/انهدام/برد/باخت/هشدار (از
طریق AudioManager، که اگه فایل صوتی واقعی موجود نباشه سکوت می‌کنه).

⚠️ تصمیم معماری مهم: GameWidget همچنان یک Widget ساده‌ست (نه خودِ
Screen)، و GameScreen فقط یک پوشش نازک دورشه که آن را به‌عنوان فرزند
اضافه می‌کند. چرا: Screen از RelativeLayout ارث می‌بره که مختصات لمسی
فرزندهاش رو تبدیل می‌کنه؛ منطق لمسی GameWidget (on_touch_down/move/up)
از قبل کاملاً وریفای‌شده و به مختصات خام پنجره وابسته‌ست. اگه GameWidget
مستقیم Screen می‌شد، می‌بایست رفتار دقیق RelativeLayout روی on_touch_*
خودش (نه فرزندهاش) رو بدون امکان اجرای واقعی Kivy تضمین می‌کردیم --
ریسک غیرضروری. با نگه‌داشتن GameWidget به‌عنوان Widget ساده و اضافه‌
کردنش به‌عنوان فرزند GameScreen، از تبدیل مختصاتِ استاندارد و
well-tested والد->فرزند Kivy استفاده می‌کنیم (که دقیقاً برای همین
منظور طراحی شده) و صفر خط از منطق لمسی/رسم قبلی عوض نمی‌شه.
"""
import math
import time

from kivy.uix.widget import Widget
from kivy.uix.screenmanager import Screen
from kivy.graphics import Canvas, Color, Line, Ellipse, InstructionGroup, PushMatrix, PopMatrix, Translate
from kivy.clock import Clock
from kivy.metrics import dp

from ecs.world import World
from ecs.components.position import Position
from ecs.components.mirror import Mirror
from ecs.components.obstacle import Obstacle
from ecs.components.portal import Portal
from ecs.components.prism import Prism
from ecs.components.black_hole import BlackHole
from ecs.components.target import Target
from ecs.systems.movement_system import MovementSystem
from ecs.systems.rotation_system import RotationSystem
from game_logic.scene_builder import entities_to_surfaces
from game_logic.level_condition import LevelCondition, calculate_stars
from utils.timer import PreciseTimer, performance_tier
from utils.particles import AdvancedParticleSystem
from ui.effects.screen_shake import AdvancedScreenShake
from ui.widgets.common import COLOR_SECONDARY, COLOR_TEXT
from ui.widgets.persian_widgets import PersianButton, PersianLabel
from ui.widgets.timer_ring import TimerRing

CROSSHAIR_RADIUS = 30.0
LASER_THICKNESS = 6.0
SMOOTHING_K = 21.0  # معادل رفتار smoothing=0.3 در ۶۰fps، ولی مستقل از فریم‌ریت
DESIGN_WIDTH = 1080.0
DESIGN_HEIGHT = 1920.0
#: فاز۹: شناسه‌ی نگهبانِ «مرحله‌ی رویه‌ای» در _pending_level_id (پرچم «مرحله‌ای در انتظار» باید None نباشد).
GENERATED_LEVEL_ID = -1
#: طبق game_logic/raycast.py -- این ۴ رشته‌ی دقیق روی برخورد با آینه در
#: hit_types ثبت می‌شن؛ رشته‌ی عمومی 'mirror' هیچ‌وقت وجود نداره.
#: فاز۱۰: راهنمای مرحله (level.hints[0]) در پایین صفحه چند ثانیه دیده می‌شود (یا تا اولین شلیک).
HINT_SECONDS = 7.0
#: ناحیه‌ی رزرو‌شده‌ی دکمه‌ی «خروج» (۹۶dp + حاشیه) در بالا-راست؛ پیام HUD زیرش نمی‌رود.
HUD_RESERVED_RIGHT_DP = 118
MIRROR_HIT_TYPES = {'normal', 'semi_mirror', 'rotating_mirror', 'broken_mirror'}


class GameWidget(Widget):
    def __init__(self, ctx, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

        self.active_shot_id = 'normal'
        self.world = World()
        self.world.add_system(MovementSystem())
        self.world.add_system(RotationSystem())
        self.world.crosshair_x = 0.0
        self.world.crosshair_y = 0.0

        self.timer = None
        self.condition = None
        self.game_over = False
        self._last_result_success = None
        self._campaign_complete_shown = False
        self._practice_mode = False
        self._pending_level_id = None
        # فاز۹ -- مرحله‌ی رویه‌ای (بی‌نهایت/چالش روزانه): None یعنی کمپین/تمرین عادی.
        self._generated = None
        # طبق فایل مرجع بخش ۵.۱۹: «GameScreen.initialize() باید
        # self._warning_played = False رو هم مقداردهی کنه» -- هشدار
        # کم‌بودن زمان، یک‌بار در هر تلاش (نه هر فریم). فاز۶: هشدار
        # حالا شامل تغییر رنگ + صدا + لرزش خفیف صفحه‌ست؛ پرچم
        # جلوی تکرار هر فریم رو می‌گیره.
        self._warning_played = False

        self.gun_x, self.gun_y = 0.0, 0.0
        self.crosshair_x, self.crosshair_y = 0.0, 0.0
        self._touch_target_x, self._touch_target_y = 0.0, 0.0
        self.last_beams = []

        # مقیاس فضای طراحی (۱۰۸۰×۱۹۲۰) به پیکسل واقعی صفحه -- طبق
        # مستندسازی main.py، تنها جایی که این تبدیل انجام می‌شود.
        self.scale = 1.0
        self.offset_x, self.offset_y = 0.0, 0.0

        self._mirror_lines = {}     # entity_id -> Line
        self._target_ellipses = {}  # entity_id -> Ellipse
        self._crosshair_line = None
        self._beam_group = InstructionGroup()
        self._status_label = None
        self._economy_label = None
        self._hint_label = None
        self._hint_remaining = 0.0
        self._hud_font = '16sp'
        self.timer_ring = None

        # فاز۶ -- لایه‌ی Juice (بخش ۵.۷): ذرات با ObjectPool موجود از
        # فاز۱ (نه Entity-per-particle)، لرزش صفحه با پارامتر پایه‌ی
        # ۵px/۱۵۰ms.
        self.particle_system = AdvancedParticleSystem()
        self._particle_group = InstructionGroup()
        # فاز۱۰: ساختار رسم --
        #   canvas.before : PushMatrix, Translate(لرزش), _scene_canvas (مراحل/پرتو/ذره)
        #   canvas        : canvas فرزندان (برچسب‌های HUD، حلقه‌ی تایمر، راهنما) -- Kivy هنگام add_widget
        #                   canvas فرزند را *داخل canvas والد* می‌گذارد
        #   canvas.after  : PopMatrix
        # چرا صحنه جدا؟ `self.canvas.clear()` (در _build_static_canvas) همه‌ی instructionهای canvas
        # از جمله canvas فرزندان را پاک می‌کند (فقط before/after می‌مانند) => HUD بعد از اولین ساخت
        # صحنه از درخت رسم حذف می‌شد. حالا فقط _scene_canvas پاک می‌شود. صحنه زیر HUD رسم می‌شود.
        self._scene_canvas = Canvas()
        with self.canvas.before:
            PushMatrix()
            self.shake_translate = Translate(0, 0)
        self.canvas.before.add(self._scene_canvas)
        with self.canvas.after:
            PopMatrix()
        self.screen_shake = AdvancedScreenShake(self)

        self._scene_ready = False
        Clock.schedule_once(self._try_init_render, 0)
        Clock.schedule_interval(self._update, 1 / 60.0)

    # ---------- راه‌اندازی ----------

    def _try_init_render(self, dt):
        """فقط زیرساخت رسم (مقیاس، لیبل‌ها) رو آماده می‌کنه. برخلاف
        فاز۱ تا ۴، بارگذاری خودِ مرحله دیگه اینجا خودکار نیست -- چون
        این ویجت دیگه تنها صفحه‌ی اپ نیست؛ prepare_level() صریحاً از
        MainMenu/LevelSelect/Sandbox صدا زده می‌شه."""
        if self.width <= 0 or self.height <= 0:
            Clock.schedule_once(self._try_init_render, 0)
            return
        self._recalc_scale()
        self._build_status_label()
        self.bind(size=self._on_resize, pos=self._on_resize)
        self._scene_ready = True
        if self._pending_level_id is not None:
            self._consume_pending_level()

    def prepare_level(self, level_id, practice=False):
        """از صفحه‌ی مبدأ (LevelSelect/MainMenu/Sandbox) *قبل* از
        goto('game') صدا زده می‌شود. اگه رسم هنوز آماده نبود (اولین
        فریم اپ)، _try_init_render خودش وقتی آماده شد این را مصرف
        می‌کند."""
        self._generated = None
        self._pending_level_id = level_id
        self._practice_mode = practice
        if self._scene_ready:
            self._consume_pending_level()

    @property
    def is_generated(self):
        return self._generated is not None

    def prepare_generated(self, level, label, on_result, next_level=None):
        """فاز۹ -- مرحله‌ی رویه‌ای (حالت بی‌نهایت / چالش روزانه). Level آماده‌ی بازی است (از مولد).

        * هیچ‌چیز از پیشرفت کمپین دست نمی‌خورد (ستاره، قفل مرحله، نتیجه‌ی ثبت‌شده)، و انرژی به‌ازای هر
          مرحله مصرف نمی‌شود (هزینه‌ی اجرای بی‌نهایت را صفحه‌ی چالش‌ها یک‌بار می‌گیرد).
        * on_result(success) -> {'message': متن، 'next': 'retry'|'next'|'exit'} -- صفحه‌ی چالش‌ها پاداش و
          آمار را همان‌جا اعمال می‌کند؛ اینجا فقط نتیجه نمایش داده می‌شود و ضربه‌ی بعدی طبق 'next' عمل می‌کند.
        * next_level() -> (Level، برچسب) یا None -- برای 'next' (مرحله‌ی بعدی بی‌نهایت)."""
        self._generated = {'level': level, 'label': label, 'on_result': on_result,
                           'next_level': next_level, 'next_action': 'exit'}
        self._pending_level_id = GENERATED_LEVEL_ID
        self._practice_mode = False
        if self._scene_ready:
            self._consume_pending_level()

    def _finish_generated(self, success):
        generated = self._generated
        outcome = generated['on_result'](success) or {}
        generated['next_action'] = outcome.get('next', 'exit')
        default = 'مرحله تمام شد!' if success else 'زمان تمام شد!'
        self._say(f"{outcome.get('message', default)} -- لمس کن تا ادامه بدی")
        self.ctx.audio_manager.play_sfx('level_win' if success else 'level_lose')
        self._update_economy_text()

    def _handle_generated_tap(self):
        generated = self._generated
        action = generated.get('next_action', 'exit')
        if action == 'retry':
            self._start_level(GENERATED_LEVEL_ID, practice=False)
        elif action == 'next' and generated['next_level'] is not None:
            upcoming = generated['next_level']()
            if upcoming is None:
                self.ctx.screen_manager.go_back(default_screen='challenges')
            else:
                generated['level'], generated['label'] = upcoming
                self._start_level(GENERATED_LEVEL_ID, practice=False)
        else:
            self.ctx.screen_manager.go_back(default_screen='challenges')

    def _consume_pending_level(self):
        level_id = self._pending_level_id
        self._pending_level_id = None
        self._start_level(level_id, practice=self._practice_mode)

    def _recalc_scale(self):
        self.scale = min(self.width / DESIGN_WIDTH, self.height / DESIGN_HEIGHT)
        self.offset_x = (self.width - DESIGN_WIDTH * self.scale) / 2.0
        self.offset_y = (self.height - DESIGN_HEIGHT * self.scale) / 2.0

    def _on_resize(self, *args):
        self._recalc_scale()
        if self._scene_ready and self.condition is not None:
            self._build_static_canvas()
            self._build_status_label()

    def _load_level(self, level_id):
        self.world.cleanup()
        level = (self._generated['level'] if self._generated is not None
                 else self.ctx.level_manager.load_level(level_id))
        if level is None:
            return
        self.gun_x, self.gun_y = level.populate_world(self.world)
        self.crosshair_x = self.gun_x
        self.crosshair_y = self.gun_y + 300.0
        self._touch_target_x, self._touch_target_y = self.crosshair_x, self.crosshair_y

        self.condition = LevelCondition(total_targets=len(level.targets))
        self.timer = PreciseTimer(duration=level.time_limit, on_complete=self._on_timeout)
        self.timer.start()
        self.game_over = False
        if self._status_label is not None:
            self._status_label.color = (1, 1, 1, 1)
        if self.timer_ring is not None:
            self.timer_ring.set_palette(self.ctx.get_color_palette())

        self._build_static_canvas()
        self._show_hint(level)

    def _start_level(self, level_id, practice=False):
        """طبق بخش ۵.۱۱ فایل مرجع: شروع یک مرحله «تیر» (انرژی) مصرف
        می‌کنه -- مگر در حالت تمرین (Sandbox، فاز۵)، که نه انرژی مصرف
        می‌شه نه نتیجه‌اش روی پیشرفت واقعی اثر می‌ذاره."""
        self._practice_mode = practice
        self._campaign_complete_shown = False
        self._warning_played = False
        if not practice and self._generated is None:
            now = time.time()
            self.ctx.profile.energy.update(now)
            if self.ctx.profile.energy.current_energy <= 0:
                self._show_out_of_energy_message()
                return
            self.ctx.profile.energy.consume(1, now=now)
            # ذخیره‌ی فوری مصرف انرژی -- اگه اندروید پروسه رو وسط مرحله
            # ببنده (خیلی معمول موبایله)، این تیر نباید مجانی «برگرده».
            self.ctx.save()
        self._load_level(level_id)

    def _show_out_of_energy_message(self):
        self.game_over = True
        wait_s = self.ctx.profile.energy.seconds_until_next_unit(time.time())
        minutes, seconds = int(wait_s // 60), int(wait_s % 60)
        self._say(
            f"انرژی تمام شد! تا انرژی بعدی: {minutes}:{seconds:02d} -- یا از فروشگاه بخر.")
        self._update_economy_text()

    # ---------- تبدیل مختصات (تنها جایی که design<->screen انجام می‌شود) ----------

    def _to_screen(self, dx, dy):
        return self.offset_x + dx * self.scale, self.offset_y + dy * self.scale

    def _to_design(self, sx, sy):
        if self.scale <= 0:
            return sx, sy
        return (sx - self.offset_x) / self.scale, (sy - self.offset_y) / self.scale

    # ---------- رسم ----------

    def _build_static_canvas(self):
        self._scene_canvas.clear()
        self._mirror_lines.clear()
        self._target_ellipses.clear()
        palette = self.ctx.get_color_palette()

        with self._scene_canvas:
            Color(*palette.get_mirror_color())
            for e in self.world.get_entities_with(Mirror):
                m = e.get_component(Mirror)
                x1, y1 = self._to_screen(m.x1, m.y1)
                x2, y2 = self._to_screen(m.x2, m.y2)
                line = Line(points=[x1, y1, x2, y2], width=4)
                self._mirror_lines[e.id] = line

            # طبق کشف حین بازبینی فاز۶: مانع/پورتال/منشور/سیاه‌چاله از
            # فاز۲ در راه‌کست کاملاً شبیه‌سازی می‌شدن ولی هیچ‌وقت رسم
            # نمی‌شدن -- یعنی مانع level_004 (فاز۳) هیچ‌وقت برای بازیکن
            # قابل‌دیدن نبوده. همین‌جا رفع شد.
            Color(*palette.get_obstacle_color())
            for e in self.world.get_entities_with(Obstacle):
                o = e.get_component(Obstacle)
                x1, y1 = self._to_screen(o.x1, o.y1)
                x2, y2 = self._to_screen(o.x2, o.y2)
                Line(points=[x1, y1, x2, y2], width=8)

            Color(*palette.get_portal_color())
            for e in self.world.get_entities_with(Position, Portal):
                pos = e.get_component(Position)
                portal = e.get_component(Portal)
                sx, sy = self._to_screen(pos.x, pos.y)
                r = portal.radius * self.scale
                Line(circle=(sx, sy, r), width=4)

            Color(*palette.get_prism_color())
            for e in self.world.get_entities_with(Position, Prism):
                pos = e.get_component(Position)
                prism = e.get_component(Prism)
                sx, sy = self._to_screen(pos.x, pos.y)
                r = prism.radius * self.scale
                Ellipse(pos=(sx - r, sy - r), size=(r * 2, r * 2))

            Color(*palette.get_black_hole_color())
            for e in self.world.get_entities_with(Position, BlackHole):
                pos = e.get_component(Position)
                bh = e.get_component(BlackHole)
                sx, sy = self._to_screen(pos.x, pos.y)
                r = bh.radius * self.scale
                Ellipse(pos=(sx - r, sy - r), size=(r * 2, r * 2))

            Color(*palette.get_target_color())
            for e in self.world.get_entities_with(Position, Target):
                pos = e.get_component(Position)
                tgt = e.get_component(Target)
                sx, sy = self._to_screen(pos.x, pos.y)
                r = tgt.radius * self.scale
                ellipse = Ellipse(pos=(sx - r, sy - r), size=(r * 2, r * 2))
                self._target_ellipses[e.id] = ellipse

            Color(0.6, 0.6, 0.7, 1.0)
            gsx, gsy = self._to_screen(self.gun_x, self.gun_y)
            gr = 25 * self.scale
            Ellipse(pos=(gsx - gr, gsy - gr), size=(gr * 2, gr * 2))

            Color(*palette.get_laser_color(alpha=0.85))
            csx, csy = self._to_screen(self.crosshair_x, self.crosshair_y)
            self._crosshair_line = Line(
                circle=(csx, csy, CROSSHAIR_RADIUS * self.scale), width=2)

            self._scene_canvas.add(self._particle_group)
            self._scene_canvas.add(self._beam_group)

    def _build_status_label(self):
        if self._status_label is None:
            self._status_label = PersianLabel(
                text='', font_size='16sp', color=(1, 1, 1, 1),
                size_hint=(None, None), height=dp(60), halign='center', valign='middle')
            self.add_widget(self._status_label)
        if self._economy_label is None:
            self._economy_label = PersianLabel(
                text='', font_size='18sp', color=(1.0, 0.85, 0.3, 1),
                size_hint=(None, None), height=dp(40))
            self.add_widget(self._economy_label)
        if self._hint_label is None:
            self._hint_label = PersianLabel(
                text='', font_size='14sp', color=(0.78, 0.9, 1.0, 0.95),
                size_hint=(None, None), height=dp(48), halign='center', valign='middle')
            self.add_widget(self._hint_label)
        if self.timer_ring is None:
            self.timer_ring = TimerRing(palette=self.ctx.get_color_palette(),
                                         size_hint=(None, None), size=(dp(56), dp(56)))
            self.add_widget(self.timer_ring)
        # فاز۸: همه‌ی ابعاد/افست‌های HUD با dp() -- همان مقادیری که بالا (height=dp(60)،
        # height=dp(40)، size=dp(56)) به ویجت‌ها داده شده؛ باید دقیقاً هم‌خوان بمانند.
        # فاز۱۰ (مشکل شناخته‌شده #9): پیام HUD قبلاً text_size نداشت و روی گوشی باریک از دو طرف بریده
        # می‌شد (و زیر دکمه‌ی «خروج» می‌رفت). حالا عرضش محدود به فضای چپ دکمه‌ی خروج است و بین ۱ تا ۳ خط
        # می‌شکند؛ اندازه‌ی فونت با طول متن انتخاب می‌شود (_say).
        status_w = max(dp(120), self.width - dp(HUD_RESERVED_RIGHT_DP) - dp(8))
        self._status_label.width = status_w
        self._status_label.pos = (self.x + dp(8), self.top - dp(60))
        self._status_label.text_size = (status_w - dp(8), dp(60))
        self._economy_label.width = self.width
        self._economy_label.pos = (self.x, self.top - dp(60) - dp(40))
        self.timer_ring.pos = (self.right - dp(56) - dp(12), self.top - dp(60) - dp(40) - dp(56) - dp(8))
        self._hint_label.width = self.width
        self._hint_label.pos = (self.x, self.y + dp(6))
        self._hint_label.text_size = (self.width - dp(24), dp(48))

    @staticmethod
    def _hud_font_for(raw):
        """طول متن -> اندازه‌ی فونت (sp)؛ پیام‌های بلند کوچک‌تر تا در ≤۳ خط جا شوند."""
        n = len(raw)
        if n <= 46:
            return '16sp'
        if n <= 80:
            return '14sp'
        return '12sp'

    def _say(self, raw):
        """تنها مسیر نوشتن روی نوار HUD بالا (هم خط وضعیت، هم پیام‌های نتیجه)."""
        if self._status_label is None:
            return
        font = self._hud_font_for(raw)
        # در Kivy واقعی font_size همیشه عدد (px) است نه '16sp'؛ پس با آخرین مقدارِ *ست‌شده‌ی خودمان*
        # مقایسه می‌کنیم، نه با خواندن از برچسب.
        if font != self._hud_font:
            self._hud_font = font
            self._status_label.font_size = font
        self._status_label.set_text(raw)

    # ---------- راهنمای مرحله (فاز۱۰) ----------

    def _show_hint(self, level):
        hints = getattr(level, 'hints', None) or []
        text = hints[0] if hints and isinstance(hints[0], str) else ''
        self._hint_remaining = HINT_SECONDS if text else 0.0
        if self._hint_label is not None:
            self._hint_label.set_text(text)

    def _hide_hint(self):
        self._hint_remaining = 0.0
        if self._hint_label is not None and self._hint_label.raw_text:
            self._hint_label.set_text('')

    def _refresh_dynamic_positions(self):
        """هر فریم فقط موقعیت عناصر متحرک (هدف/آینه‌ی چرخان) به‌روز
        می‌شود -- نه بازسازی کامل canvas."""
        for e in self.world.get_entities_with(Position, Target):
            ellipse = self._target_ellipses.get(e.id)
            if ellipse is None:
                continue
            tgt = e.get_component(Target)
            if tgt.hp <= 0:
                continue
            pos = e.get_component(Position)
            sx, sy = self._to_screen(pos.x, pos.y)
            r = tgt.radius * self.scale
            ellipse.pos = (sx - r, sy - r)

        for e in self.world.get_entities_with(Mirror):
            m = e.get_component(Mirror)
            if m.mirror_type != 'rotating_mirror':
                continue
            line = self._mirror_lines.get(e.id)
            if line is None:
                continue
            x1, y1 = self._to_screen(m.x1, m.y1)
            x2, y2 = self._to_screen(m.x2, m.y2)
            line.points = [x1, y1, x2, y2]

    # ---------- ورودی لمسی ----------

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        self._touch_target_x, self._touch_target_y = self._to_design(touch.x, touch.y)
        return True

    def on_touch_move(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        self._touch_target_x, self._touch_target_y = self._to_design(touch.x, touch.y)
        return True

    def on_touch_up(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        if self.game_over:
            self._handle_post_game_tap()
        else:
            self._fire()
        return True

    # ---------- حلقه‌ی اصلی ----------

    def _update(self, dt):
        if not self._scene_ready or self.condition is None:
            return

        if not self.game_over:
            self.timer.update(dt)
        # ⚠️ باگ قدیمی فاز۵ (در بازبینی فاز۹ پیدا شد): PreciseTimer در on_complete همین‌جا (داخل
        # timer.update) _on_timeout را صدا می‌زند و پیام «زمان تمام شد! لمس کن...» را می‌نویسد؛ ولی
        # ادامه‌ی همان فریم _update_status_text را اجرا می‌کرد و پیام را با خط HUD («زمان: 00:00»)
        # رونویسی می‌کرد -- پس بازیکن بعد از باخت هیچ‌وقت پیام را نمی‌دید. حالا بعد از timer.update
        # دوباره game_over چک می‌شود.
        if not self.game_over:
            self.world.crosshair_x, self.world.crosshair_y = self.crosshair_x, self.crosshair_y
            self.world.update(dt)

            factor = 1.0 - math.exp(-SMOOTHING_K * dt)
            self.crosshair_x += (self._touch_target_x - self.crosshair_x) * factor
            self.crosshair_y += (self._touch_target_y - self.crosshair_y) * factor

            self._refresh_dynamic_positions()
            if self._hint_remaining > 0.0:
                self._hint_remaining -= dt
                if self._hint_remaining <= 0.0:
                    self._hide_hint()
            self._update_status_text()
            self._update_economy_text()

            if self.condition.is_failure(self.timer):
                self._on_timeout()

        # طبق بخش۵.۱ -- اولویت Particle=70، بعد از فیزیک/Raycast/Collision
        # (که همین بالا مشخص کردن چی منفجر شده)، مستقل از game_over (تا
        # افکت انفجار آخرین شلیک حتی بعد از پایان مرحله محو بشه، نه قطع).
        self.particle_system.update(dt)
        self._redraw_particles()

        if self._crosshair_line is not None:
            csx, csy = self._to_screen(self.crosshair_x, self.crosshair_y)
            self._crosshair_line.circle = (csx, csy, CROSSHAIR_RADIUS * self.scale)

    #: طبق تصمیم فایل مرجع بخش ۵.۸ -- همون آستانه‌ی درصدی 'close'/'good'
    #: (نه ثانیه‌ی مطلق) برای هشدار کم‌بودن زمان هم استفاده می‌شود.
    _WARNING_THRESHOLD_FRACTION = 0.20

    def _update_status_text(self):
        remaining = self.condition.total_targets - self.condition.targets_destroyed
        practice_tag = '  [تمرین]' if self._practice_mode else ''
        if self._generated is not None:
            head = self._generated['label']
        else:
            phase = self.ctx.difficulty_manager.get_phase_for_level(self.ctx.level_manager.current_level_id)
            head = f"مرحله {self.ctx.level_manager.current_level_id} ({phase['name_fa']})"
        raw = (f"{head}{practice_tag}    "
               f"زمان: {self.timer.get_display_time()}    "
               f"هدف: {remaining}/{self.condition.total_targets}")
        self._say(raw)

        tier = performance_tier(self.timer.remaining_fraction)
        if self.timer_ring is not None:
            self.timer_ring.update_progress(self.timer.remaining_fraction, tier)

        if not self._warning_played and self.timer.remaining_fraction <= self._WARNING_THRESHOLD_FRACTION:
            # هشدار یک‌باره‌ی کم‌بودن زمان (بخش ۵.۱۹) -- تغییر رنگ + صدا
            # + یک لرزش خفیف صفحه.
            self._status_label.color = (1.0, 0.35, 0.25, 1.0)
            self.ctx.audio_manager.play_sfx('low_time_warning')
            self.screen_shake.shake(amplitude=3.0, duration=0.2)
            self._warning_played = True

    def _update_economy_text(self):
        energy = self.ctx.profile.energy
        energy.update(time.time())
        economy = self.ctx.profile.economy
        raw = f"سکه: {economy.coins}    جواهر: {economy.gems}    انرژی: {energy.current_energy}/{energy.max_energy}"
        self._economy_label.set_text(raw)

    # ---------- شلیک ----------

    def _fire(self):
        if self.game_over:
            return

        dx, dy = self.crosshair_x - self.gun_x, self.crosshair_y - self.gun_y
        length = math.hypot(dx, dy)
        if length < 1e-3:
            dx, dy = 0.0, 1.0
        else:
            dx, dy = dx / length, dy / length

        surfaces = entities_to_surfaces(self.world)
        # طبق فایل مرجع بخش ۵.۶: شلیک همیشه از مسیر SpecialShotManager
        # رد می‌شود -- همون نمونه‌ای که profile نگه می‌داره و ShopManager
        # رویش unlock_shot صدا می‌زنه (فاز۴)، نه یک نمونه‌ی جدا.
        self.last_beams = self.ctx.profile.special_shots.execute_shot(
            self.active_shot_id, self.gun_x, self.gun_y, dx, dy, surfaces)
        self.condition.on_shot_fired()
        self._hide_hint()
        self.ctx.audio_manager.play_sfx('shot_fire')

        hit_type_set = {t for beam in self.last_beams for t in beam.hit_types}
        # طبق game_logic/raycast.py: هیچ‌وقت رشته‌ی 'mirror' عمومی وجود
        # نداره -- نوع دقیق آینه ('normal'/'semi_mirror'/'rotating_mirror'/
        # 'broken_mirror') در hit_types ثبت می‌شه.
        if hit_type_set & MIRROR_HIT_TYPES:
            self.ctx.audio_manager.play_sfx('mirror_hit')
        if 'obstacle' in hit_type_set:
            self.ctx.audio_manager.play_sfx('obstacle_hit')
            self.screen_shake.shake()

        if not self._practice_mode:
            # فاز۷ -- طبق همون اصل حالت تمرین (بدون تأثیر روی پیشرفت
            # واقعی)، شلیک‌های Sandbox به هیچ ماموریتی گزارش نمی‌شن.
            self.ctx.profile.missions.report_event('shots_fired', 1)
            bounce_count = sum(1 for beam in self.last_beams for t in beam.hit_types if t in MIRROR_HIT_TYPES)
            if bounce_count:
                self.ctx.profile.missions.report_event('mirror_bounces', bounce_count)
            if self.active_shot_id != 'normal':
                self.ctx.profile.missions.report_event('special_shots_used', 1)

        for beam in self.last_beams:
            if beam.hit_types and beam.hit_types[-1] == 'target' and beam.hit_ids:
                self._apply_target_hit(beam.hit_ids[-1])

        self._redraw_beams()

        if self.condition.is_success():
            self._on_success()

    def _apply_target_hit(self, entity_id):
        for e in self.world.get_entities_with(Target):
            if e.id != entity_id:
                continue
            tgt = e.get_component(Target)
            if tgt.hp <= 0:
                continue
            tgt.hp -= 1
            if tgt.hp <= 0:
                self.condition.on_target_destroyed()
                if not self._practice_mode:
                    self.ctx.profile.missions.report_event('targets_destroyed', 1)
                ellipse = self._target_ellipses.get(entity_id)
                if ellipse is not None:
                    pos = e.get_component(Position)
                    sx, sy = self._to_screen(pos.x, pos.y)
                    # طبق بخش۵.۷ -- _spawn_explosion باید particle_system.
                    # spawn_explosion رو صدا بزنه، نه یک Entity دستی بسازه.
                    self.particle_system.spawn_explosion(
                        sx, sy, self.ctx.get_color_palette().get_target_color())
                    ellipse.size = (0, 0)
                self.ctx.audio_manager.play_sfx('target_destroy')

    def _redraw_beams(self):
        self._beam_group.clear()
        self._beam_group.add(Color(*self.ctx.get_color_palette().get_laser_color()))
        for beam in self.last_beams:
            flat_points = []
            for (px, py) in beam.points:
                sx, sy = self._to_screen(px, py)
                flat_points.extend([sx, sy])
            if len(flat_points) >= 4:
                self._beam_group.add(Line(points=flat_points, width=LASER_THICKNESS / 2.0))

    def _redraw_particles(self):
        """طبق بخش۵.۷ -- خودِ AdvancedParticleSystem مستقل از Kivy است
        (utils/particles.py)؛ رسم واقعی (Ellipse) فقط اینجا، دقیقاً
        همون تقسیم مسئولیتی که کل پروژه رعایت می‌کنه."""
        self._particle_group.clear()
        for p in self.particle_system.get_active_particles():
            sx, sy = self._to_screen(p.x, p.y)
            r = max(0.5, p.radius * self.scale * p.life_fraction)
            fade_color = (p.color[0], p.color[1], p.color[2], p.color[3] * p.life_fraction)
            self._particle_group.add(Color(*fade_color))
            self._particle_group.add(Ellipse(pos=(sx - r, sy - r), size=(r * 2, r * 2)))

    # ---------- پایان مرحله ----------

    def _on_success(self):
        self.game_over = True
        self._last_result_success = True
        self.timer.pause()
        if self._generated is not None:
            # فاز۹: قبل از هر چیزی که به پیشرفت کمپین دست می‌زند منشعب می‌شویم.
            self._finish_generated(True)
            return
        result = self.condition.get_result(self.timer)
        stars = calculate_stars(result)
        level_id = self.ctx.level_manager.current_level_id

        if not self._practice_mode:
            # باگ واقعی فاز۲ (رفع‌شده در فاز۳): unlock_next() هیچ‌جا صدا
            # زده نمی‌شد.
            self.ctx.level_manager.unlock_next()
            self.ctx.level_manager.record_level_result(
                level_id, stars, shots_used=result['shots_used'],
                time_remaining=result['time_remaining'])

            # فاز۴ -- قلب چرخه‌ی «بازی کن -> سکه بگیر»: پاداش همین مرحله
            # واقعاً به اقتصاد و Battle Pass بازیکن اعمال می‌شه.
            level = self.ctx.level_manager.current_level
            rewards = level.rewards if level is not None else {}
            self.ctx.profile.economy.apply_level_rewards(rewards)
            self.ctx.profile.battle_pass.add_xp(rewards.get('xp', 0))
            coin_amount = round(rewards.get('coins', 0) * self.ctx.profile.economy.coin_bonus_multiplier)

            # فاز۷ -- پیشرفت ماموریت‌های روزانه/هفتگی و چالش هفتگی
            self.ctx.profile.missions.report_event('levels_completed', 1)
            self.ctx.profile.missions.report_event('stars_earned', stars)
            if coin_amount:
                self.ctx.profile.missions.report_event('coins_earned', coin_amount)
            if result['is_perfect']:
                self.ctx.profile.missions.report_event('perfect_levels', 1)
            self.ctx.profile.weekly_challenge.add_progress(stars * 10 + result['shots_used'])

            self.ctx.save()
            coin_txt = f"  +{coin_amount} سکه"
        else:
            coin_txt = '  (حالت تمرین -- بدون پاداش)'

        tag = ' -- بی‌نقص!' if result['is_perfect'] else ''
        msg = f"مرحله تمام شد!{tag} (امتیاز: {stars}/۳){coin_txt} -- لمس کن تا ادامه بدی"
        self._say(msg)
        self.ctx.audio_manager.play_sfx('level_win')

    def _on_timeout(self):
        if self.game_over:
            return
        self.game_over = True
        self._last_result_success = False
        if self._generated is not None:
            self._finish_generated(False)
            return
        self._say("زمان تمام شد! لمس کن تا دوباره امتحان کنی.")
        self.ctx.audio_manager.play_sfx('level_lose')

    def _handle_post_game_tap(self):
        if self._generated is not None:
            self._handle_generated_tap()
            return
        if self._practice_mode:
            # حالت تمرین: نه پیشروی نه انرژی درگیره -- یک تلاش دیگه یا
            # برگشت به Sandbox، تصمیمش با خودِ صفحه‌ی Sandbox نیست، فقط
            # برمی‌گردیم اونجا و بازیکن دوباره انتخاب می‌کنه.
            self.ctx.screen_manager.go_back(default_screen='sandbox')
            return

        if self._last_result_success:
            next_id = self.ctx.level_manager.get_next_level_id()
            if next_id is not None:
                self._start_level(next_id, practice=False)
            elif not self._campaign_complete_shown:
                self._show_campaign_complete()
            else:
                self.ctx.screen_manager.go_back(default_screen='level_select')
        else:
            retry_id = self.ctx.level_manager.current_level_id or 1
            self._start_level(retry_id, practice=False)

    def _show_campaign_complete(self):
        self._campaign_complete_shown = True
        self._say(
            "تبریک! هر ۱۰۰ مرحله‌ی کمپین رو کامل کردی -- لمس کن تا برگردی به لیست مراحل.")


class GameScreen(Screen):
    """پوشش نازک Kivy: GameWidget رو به‌عنوان فرزند اضافه می‌کند (تا
    تبدیل مختصات لمسی والد->فرزند Kivy، نه پیاده‌سازی دستی، مسئولش
    باشه -- توضیح کامل در docstring بالای فایل) + دکمه‌ی خروج."""

    def __init__(self, ctx, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx
        self.game_widget = GameWidget(ctx)
        self.add_widget(self.game_widget)

        self.exit_button = PersianButton(
            text='خروج', size_hint=(None, None), size=(dp(96), dp(44)),
            pos_hint={'right': 0.985, 'top': 0.985},
            background_color=COLOR_SECONDARY, color=COLOR_TEXT)
        self.exit_button.bind(on_release=lambda *_a: self._exit())
        self.add_widget(self.exit_button)

    def prepare_level(self, level_id, practice=False):
        self.game_widget.prepare_level(level_id, practice=practice)

    def prepare_generated(self, level, label, on_result, next_level=None):
        self.game_widget.prepare_generated(level, label, on_result, next_level)

    def on_pre_enter(self, *args):
        self.ctx.audio_manager.play_music('gameplay')
        # شبکه‌ی ایمنی: اگه prepare_level قبل از آماده‌شدن رسم صدا زده
        # شده بود (فریم اول اپ)، اینجا یک فرصت دیگه برای مصرفش هست.
        if self.game_widget._pending_level_id is not None and self.game_widget._scene_ready:
            self.game_widget._consume_pending_level()

    def _exit(self):
        # فاز۹: خروج از مرحله‌ی رویه‌ای به صفحه‌ی چالش‌ها برمی‌گردد (نه فهرست مراحل کمپین).
        default = 'challenges' if self.game_widget.is_generated else 'level_select'
        self.ctx.screen_manager.go_back(default_screen=default)
