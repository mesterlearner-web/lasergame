"""
ui/screens/profile_screen.py  (فاز ۵)
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.metrics import dp

from game_logic.battle_pass_manager import MAX_LEVEL
from game_logic.special_shot_manager import SHOT_TYPES
from ui.widgets.common import COLOR_BG, COLOR_BAR_BG, COLOR_TEXT, COLOR_MUTED, SolidBox, TopBar
from ui.widgets.persian_widgets import PersianLabel


class ProfileScreen(Screen):
    def __init__(self, ctx, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

        root_bg = SolidBox(bg_color=COLOR_BG, orientation='vertical')
        root_bg.add_widget(TopBar('پروفایل', on_back=self._go_back))

        self.body = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(24))
        root_bg.add_widget(self.body)
        self.add_widget(root_bg)

    def on_pre_enter(self, *args):
        self._refresh()

    def _row(self, label_text, value_text):
        row = SolidBox(bg_color=COLOR_BAR_BG, size_hint_y=None, height=dp(52), padding=dp(14))
        left = PersianLabel(text=label_text, font_size='16sp', color=COLOR_MUTED,
                             halign='left', valign='middle')
        left.bind(size=lambda w, s: setattr(w, 'text_size', s))
        right = PersianLabel(text=value_text, font_size='17sp', bold=True, color=COLOR_TEXT,
                              halign='right', valign='middle', size_hint_x=None, width=dp(220))
        right.bind(size=lambda w, s: setattr(w, 'text_size', s))
        row.add_widget(left)
        row.add_widget(right)
        return row

    def _refresh(self):
        self.body.clear_widgets()
        lm = self.ctx.level_manager
        profile = self.ctx.profile

        total_stars = lm.get_total_stars()
        max_stars = lm.level_count * 3
        completed = len(lm.level_results)

        unlocked_shots = [SHOT_TYPES[sid]['name_fa'] for sid in profile.special_shots.get_available_shots()]
        gun_id = profile.equipment.equipped_gun_id or '(هیچ -- اسلحه‌ی پیش‌فرض)'

        self.body.add_widget(self._row('سکه', str(profile.economy.coins)))
        self.body.add_widget(self._row('جواهر', str(profile.economy.gems)))
        self.body.add_widget(self._row('مراحل تکمیل‌شده', f"{completed} از {lm.level_count}"))
        self.body.add_widget(self._row('مجموع ستاره', f"{total_stars} از {max_stars}"))
        self.body.add_widget(self._row('سطح Battle Pass', f"{profile.battle_pass.get_current_level()} از {MAX_LEVEL}"))
        self.body.add_widget(self._row('اسلحه‌ی مجهز', gun_id))
        self.body.add_widget(self._row('شلیک‌های ویژه‌ی باز‌شده', '، '.join(unlocked_shots) if unlocked_shots else '—'))

    def _go_back(self):
        self.ctx.screen_manager.go_back(default_screen='main_menu')
