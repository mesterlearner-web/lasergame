"""
ui/screens/sandbox_screen.py  (فاز ۵)

طبق فایل مرجع بخش۵.۱۹: «Sandbox Screen» فقط با اسم در بخش۶ (پرامپت
خام) اشاره شده بود، بدون طراحی -- اینجا برای اولین‌بار طراحی و پیاده
شد: تمرین آزاد روی هر مرحله‌ای (حتی هنوز باز‌نشده)، بدون مصرف انرژی و
بدون تأثیر روی پیشرفت واقعی (ستاره/سکه/باز‌شدن مرحله‌ی بعد) -- طبق
همون practice=True که GameWidget (فاز۵) پیاده می‌کند.
"""
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp

from ui.widgets.common import COLOR_BG, COLOR_BAR_BG, COLOR_PRIMARY, COLOR_TEXT, COLOR_MUTED, SolidBox, TopBar
from ui.widgets.persian_widgets import PersianButton, PersianLabel


class SandboxScreen(Screen):
    def __init__(self, ctx, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

        root_bg = SolidBox(bg_color=COLOR_BG, orientation='vertical')
        root_bg.add_widget(TopBar('تمرین (Sandbox)', on_back=self._go_back))

        note = PersianLabel(
            text='هر مرحله‌ای رو (حتی هنوز باز‌نشده) بدون مصرف انرژی امتحان کن -- '
                 'نتیجه‌اش ستاره/سکه نمی‌ده و پیشرفت واقعی رو عوض نمی‌کنه.',
            font_size='13sp', color=COLOR_MUTED, size_hint_y=None, height=dp(50),
            halign='center', valign='middle')
        note.bind(size=lambda w, s: setattr(w, 'text_size', (s[0] - dp(24), s[1])))
        root_bg.add_widget(note)

        scroll = ScrollView()
        self.level_list = GridLayout(cols=1, size_hint_y=None, spacing=dp(10), padding=dp(16))
        self.level_list.bind(minimum_height=self.level_list.setter('height'))
        scroll.add_widget(self.level_list)
        root_bg.add_widget(scroll)

        self.add_widget(root_bg)

    def on_pre_enter(self, *args):
        self._refresh()

    def _refresh(self):
        self.level_list.clear_widgets()
        for level_id in self.ctx.level_manager.get_all_level_ids():
            phase = self.ctx.difficulty_manager.get_phase_for_level(level_id)
            row = SolidBox(bg_color=COLOR_BAR_BG, size_hint_y=None, height=dp(68),
                            spacing=dp(10), padding=dp(12))
            label = PersianLabel(text=f"مرحله {level_id} -- {phase['name_fa']}",
                                  font_size='17sp', color=COLOR_TEXT,
                                  halign='left', valign='middle')
            label.bind(size=lambda w, s: setattr(w, 'text_size', s))
            row.add_widget(label)
            btn = PersianButton(text='تمرین', size_hint=(None, 1), width=dp(100),
                                 background_color=COLOR_PRIMARY, color=COLOR_TEXT)
            btn.bind(on_release=lambda *_a, lid=level_id: self._practice(lid))
            row.add_widget(btn)
            self.level_list.add_widget(row)

    def _practice(self, level_id):
        game_screen = self.ctx.screen_manager.get_screen('game')
        game_screen.prepare_level(level_id, practice=True)
        self.ctx.screen_manager.goto('game')

    def _go_back(self):
        self.ctx.screen_manager.go_back(default_screen='main_menu')
