"""
main.py -- نقطه‌ی ورود بازی Laser Ricochet

فاز ۱ تا ۸: مرحله‌ی واقعی از JSON (۵ مرحله، فاز آموزشی کامل)،
اهداف متحرک، آینه‌ی چرخان، تایمر، شرط برد/باخت، منحنی سختی، پیشروی
واقعی بین مراحل، اقتصاد کامل (سکه/جواهر/انرژی/فروشگاه/Battle Pass) با
ذخیره‌سازی واقعی SQLite، ناوبری کامل بین ۸ صفحه با GameScreenManager
که باگ go_back (فایل مرجع بخش۵.۱۹) نداره، و لایه‌ی Juice فاز۶
(پالت رنگ حساس به رنگ‌کوری، ذرات انفجار، لرزش صفحه، حلقه‌ی تایمر،
انیمیشن ورود منو، AudioManager)، و فاز۸ (آماده‌سازی برای اندروید واقعی: فونت فارسی‌دار،
ابعاد dp، دکمه‌ی Back سخت‌افزاری، چرخه‌ی عمر اعلان‌ها).

⚠️ این فایل در sandbox تحلیل قابل‌اجرا نیست (Kivy قابل‌نصب نبود)، پس
فقط با دقت نوشته شده، نه اجرا‌شده. تست واقعی‌اش باید محلی یا از طریق
GitHub Actions باشد. تمام منطق مستقل از Kivy (ecs/, game_logic/,
utils/, core/) کامل تست شده است (`python tests/test_core.py`).

معماری: خودِ main.py دیگه هیچ منطق بازی نداره -- فقط AppContext رو
می‌سازه (یک‌بار، با همه‌ی managerها) و ۸ صفحه رو با همون ctx به
GameScreenManager اضافه می‌کنه. هر صفحه (ui/screens/) مسئول خودشه؛
main.py فقط orchestration می‌کنه.

سیستم مختصات (فقط برای صفحه‌ی بازی معتبره): تمام منطق بازی (ECS،
Raycasting، فایل‌های JSON مراحل) در «فضای طراحی» ثابت ۱۰۸۰×۱۹۲۰ کار
می‌کند. تبدیل به پیکسل‌های واقعی صفحه فقط در ui/screens/game_screen.py
(GameWidget._to_screen/_to_design) انجام می‌شود.
"""
import os

from kivy.app import App
from kivy.core.window import Window
from kivy.logger import Logger
from kivy.utils import platform

from core.app_context import AppContext
from core.audio_manager import AudioManager
from core.game import AnimationManager
from core.notification_manager import NotificationManager
from game_logic.back_navigation import ANDROID_BACK_KEY, decide_back_action
from game_logic.difficulty_manager import DifficultyManager
from game_logic.level_manager import LevelManager
from game_logic.save_manager import SaveManager
from ui.screen_manager import GameScreenManager
from ui.screens.battle_pass_screen import BattlePassScreen
from ui.screens.game_screen import GameScreen
from ui.screens.level_select_screen import LevelSelectScreen
from ui.screens.main_menu_screen import MainMenuScreen
from ui.screens.challenge_screen import ChallengeScreen
from ui.screens.missions_screen import MissionsScreen
from ui.screens.profile_screen import ProfileScreen
from ui.screens.sandbox_screen import SandboxScreen
from ui.screens.settings_screen import SettingsScreen
from ui.screens.shop_screen import ShopScreen
from ui.widgets.persian_widgets import PersianButton
from utils.fonts import register_default_font
from utils.persian_text import is_shaping_available


class LaserRicochetApp(App):
    title = 'Laser Ricochet'

    def build(self):
        # باید قبل از ساخته‌شدن/رسم هر ویجتی باشد (فونت پیش‌فرض Kivy فارسی ندارد).
        self._prepare_text_rendering()

        if platform not in ('android', 'ios'):
            # فقط برای تست دسکتاپ -- روی موبایل، پنجره خودش تمام‌صفحه است
            Window.size = (405, 720)

        # فاز۸: Back سخت‌افزاری -- بدون این، Kivy با زدن Back کل برنامه را می‌بندد.
        Window.bind(on_keyboard=self._on_keyboard)

        level_manager = LevelManager(levels_dir=self._levels_dir())
        difficulty_manager = DifficultyManager()
        save_manager = SaveManager(db_path=self._save_db_path())
        profile = save_manager.load(level_manager)

        # فاز۶/۷ -- هر سه Singleton هستن (یک نمونه‌ی سراسری، نه ساخت
        # تازه در هر تابع)؛ همین‌جا فقط یک‌بار ساخته می‌شن.
        animation_manager = AnimationManager()
        audio_manager = AudioManager()
        notification_manager = NotificationManager()
        # فاز۱۰: صدای لمس برای هر PersianButton (قبلاً 'button_tap' تعریف بود ولی هیچ‌جا پخش نمی‌شد).
        PersianButton.tap_sound = lambda: audio_manager.play_sfx('button_tap')

        screen_manager = GameScreenManager()
        self.ctx = AppContext(screen_manager, save_manager, level_manager,
                               difficulty_manager, profile,
                               animation_manager=animation_manager, audio_manager=audio_manager,
                               notification_manager=notification_manager)

        for screen_cls, name in (
            (MainMenuScreen, 'main_menu'),
            (LevelSelectScreen, 'level_select'),
            (GameScreen, 'game'),
            (ShopScreen, 'shop'),
            (SettingsScreen, 'settings'),
            (ProfileScreen, 'profile'),
            (SandboxScreen, 'sandbox'),
            (BattlePassScreen, 'battle_pass'),
            (MissionsScreen, 'missions'),
            (ChallengeScreen, 'challenges'),
        ):
            screen_manager.add_widget(screen_cls(self.ctx, name=name))

        screen_manager.goto('main_menu', push=True)
        return screen_manager

    @staticmethod
    def _prepare_text_rendering():
        """فاز۸ -- فونت فارسی‌دار + بررسی کتابخانه‌های shaping. هیچ‌کدام کرش نمی‌دهند
        (برنامه بالا می‌آید) ولی خرابی‌شان یعنی متن فارسی خراب نمایش داده می‌شود؛ پس
        باید *بلند* لاگ شوند تا در `adb logcat` دیده شوند (پیام‌ها عمداً ASCII‌اند)."""
        family = register_default_font()
        if family is None:
            Logger.error('LaserRicochet: no Persian-capable font found in assets/fonts '
                         '-> all Persian text will render as empty boxes')
        else:
            Logger.info('LaserRicochet: default font registered: %s', os.path.basename(family[0]))
        if not is_shaping_available():
            Logger.error('LaserRicochet: arabic_reshaper/python-bidi failed to import '
                         '-> Persian letters will be disconnected and reversed')

    def _on_keyboard(self, window, key, scancode=None, codepoint=None, modifier=None):
        """Back اندروید (کد ۲۷). True یعنی رویداد مصرف شد؛ False یعنی Kivy کارِ پیش‌فرضش
        (بستن برنامه) را بکند -- فقط از صفحه‌ی ریشه."""
        if key != ANDROID_BACK_KEY:
            return False
        ctx = getattr(self, 'ctx', None)
        if ctx is None:
            return False
        action, default_screen = decide_back_action(ctx.screen_manager.current)
        if action == 'go_back':
            ctx.screen_manager.go_back(default_screen=default_screen)
            return True
        return False

    @staticmethod
    def _levels_dir():
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'levels')

    @staticmethod
    def _save_db_path():
        """روی اندروید، پوشه‌ی نصب برنامه قابل‌نوشتن نیست -- باید از
        user_data_dir خودِ Kivy (فضای مخصوص داده‌ی این اپ) استفاده بشه.
        روی دسکتاپ (برای تست محلی)، اگه App هنوز آماده نبود، یک مسیر
        محلی جایگزین می‌شه."""
        app = App.get_running_app()
        if app is not None:
            return os.path.join(app.user_data_dir, 'save.db')
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'save.db')

    def on_start(self):
        # بازیکن برگشته: اعلان‌های زمان‌بندی‌شده‌ی قبلی کهنه‌اند («انرژیت پر شد» وقتی
        # دارد بازی می‌کند). هنگام خروج دوباره زمان‌بندی می‌شوند.
        notifications = self.ctx.notification_manager
        notifications.cancel_all()
        notifications.request_permission()

    def on_resume(self):
        self.ctx.notification_manager.cancel_all()

    def on_pause(self):
        # طبق چرخه‌ی حیات اندروید: هر لحظه ممکنه اپ پس‌زمینه بشه و پروسه‌اش
        # بدون هشدار کشته بشه -- ذخیره‌ی نقطه‌ای (بعد از هر مرحله/مصرف
        # انرژی/خرید) کافی نیست، اینجا هم باید صریحاً ذخیره بشه. True یعنی
        # اپ متوقف نمی‌شه، فقط مکث می‌کنه (رفتار استاندارد Kivy/Android).
        self.ctx.save()
        self._schedule_comeback_notification()
        return True

    def on_stop(self):
        self.ctx.save()
        self._schedule_comeback_notification()

    def _schedule_comeback_notification(self):
        """فاز۷ -- وقتی بازیکن می‌ره، دقیقاً بگو کِی برگرده: اگه انرژی
        پر نیست، «وقتی پر شد» بهتر از یک یادآوری ژنریکه؛ وگرنه یادآوری
        عمومی ۲۰ساعته (بخش۵.۲۰). روی غیر-اندروید همیشه امن no-op است
        (NotificationManager خودش این رو مدیریت می‌کنه)."""
        result = self.ctx.notification_manager.schedule_energy_full(self.ctx.profile.energy)
        # فقط وقتی انرژی همین الان پر است «انرژی پر شد» معنا ندارد و به یادآوری عمومی
        # برمی‌گردیم. (خطاهای پلتفرم -- not_android/receiver_missing/android_error --
        # برای یادآوری عمومی هم صادق‌اند؛ دوباره امتحان‌کردنشان فقط تکرار همان خطاست.)
        if result.get('reason') == 'already_full':
            self.ctx.notification_manager.schedule_comeback_reminder()


if __name__ == '__main__':
    LaserRicochetApp().run()
