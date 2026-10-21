"""
ui/screens/main_menu_screen.py  (فاز ۵، بسط فاز۶: انیمیشن ورود + موسیقی)
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.metrics import dp

from ui.widgets.common import COLOR_BG, COLOR_PRIMARY, COLOR_SECONDARY, COLOR_TEXT, EconomyBar, SolidBox
from ui.widgets.persian_widgets import PersianButton, PersianLabel


class MainMenuScreen(Screen):
    def __init__(self, ctx, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

        root = SolidBox(bg_color=COLOR_BG, orientation='vertical')

        self.economy_bar = EconomyBar()
        root.add_widget(self.economy_bar)

        title_box = BoxLayout(size_hint_y=0.2)
        title = PersianLabel(text='Laser Ricochet', font_size='40sp', bold=True, color=COLOR_TEXT)
        title_box.add_widget(title)
        root.add_widget(title_box)

        menu = BoxLayout(orientation='vertical', spacing=dp(8), padding=(dp(40), dp(8), dp(40), dp(20)))
        self.menu_buttons = [
            self._menu_button('بازی', COLOR_PRIMARY, self._go_play),
            self._menu_button('انتخاب مرحله', COLOR_SECONDARY, self._go_level_select),
            self._menu_button('چالش‌ها', COLOR_SECONDARY, self._go_challenges),
            self._menu_button('تمرین (Sandbox)', COLOR_SECONDARY, self._go_sandbox),
            self._menu_button('ماموریت‌ها', COLOR_SECONDARY, self._go_missions),
            self._menu_button('فروشگاه', COLOR_SECONDARY, self._go_shop),
            self._menu_button('Battle Pass', COLOR_SECONDARY, self._go_battle_pass),
            self._menu_button('پروفایل', COLOR_SECONDARY, self._go_profile),
            self._menu_button('تنظیمات', COLOR_SECONDARY, self._go_settings),
        ]
        for btn in self.menu_buttons:
            menu.add_widget(btn)
        root.add_widget(menu)

        self.add_widget(root)

    def _menu_button(self, text, color, handler):
        btn = PersianButton(text=text, font_size='20sp', background_color=color, color=COLOR_TEXT)
        btn.bind(on_release=lambda *_a: handler())
        return btn

    def on_pre_enter(self, *args):
        self.economy_bar.update(self.ctx.profile)
        self.ctx.audio_manager.play_music('menu')

    def on_enter(self, *args):
        # طبق بخش۵.۱۸ -- استگرِ پلکانی؛ on_enter (نه on_pre_enter) چون
        # ویجت‌ها باید واقعاً روی صفحه باشن تا opacity/Animation دیده بشه.
        self.ctx.animation_manager.play_entry_animations(list(self.menu_buttons))

    # ---- ناوبری -- طبق قرارداد بخش۵.۱۹: از منو رفتن یعنی تاریخچه از نو
    # شروع می‌شه (push=False)، تا دکمه‌ی برگشت از صفحه‌ی بعدی به جای
    # برگشتن اینجا، بی‌نهایت تو تاریخچه‌ی قبلی گم نشه. ----

    def _go_play(self):
        resume_id = self.ctx.level_manager.current_level_id
        if resume_id is None or not self.ctx.level_manager.is_unlocked(resume_id):
            resume_id = max(self.ctx.level_manager.get_unlocked_level_ids(), default=1)
        game_screen = self.ctx.screen_manager.get_screen('game')
        game_screen.prepare_level(resume_id, practice=False)
        self.ctx.screen_manager.goto('game', push=False)

    def _go_level_select(self):
        self.ctx.screen_manager.goto('level_select', push=False)

    def _go_sandbox(self):
        self.ctx.screen_manager.goto('sandbox', push=False)

    def _go_challenges(self):
        self.ctx.screen_manager.goto('challenges', push=False)

    def _go_missions(self):
        self.ctx.screen_manager.goto('missions', push=False)

    def _go_shop(self):
        self.ctx.screen_manager.goto('shop', push=False)

    def _go_battle_pass(self):
        self.ctx.screen_manager.goto('battle_pass', push=False)

    def _go_profile(self):
        self.ctx.screen_manager.goto('profile', push=False)

    def _go_settings(self):
        self.ctx.screen_manager.goto('settings', push=False)
