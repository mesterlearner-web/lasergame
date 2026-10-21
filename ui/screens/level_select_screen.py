"""
ui/screens/level_select_screen.py  (فاز ۵)
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp

from ui.widgets.common import (
    COLOR_BG, COLOR_BAR_BG, COLOR_LOCKED, COLOR_PRIMARY, COLOR_TEXT, COLOR_MUTED,
    EconomyBar, SolidBox, TopBar,
)
from ui.widgets.persian_widgets import PersianButton, PersianLabel


class LevelSelectScreen(Screen):
    def __init__(self, ctx, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

        root = BoxLayout(orientation='vertical')
        root_bg = SolidBox(bg_color=COLOR_BG, orientation='vertical')
        root_bg.add_widget(TopBar('انتخاب مرحله', on_back=self._go_back))
        self.economy_bar = EconomyBar()
        root_bg.add_widget(self.economy_bar)

        scroll = ScrollView()
        self.level_list = GridLayout(cols=1, size_hint_y=None, spacing=dp(12), padding=dp(16))
        self.level_list.bind(minimum_height=self.level_list.setter('height'))
        scroll.add_widget(self.level_list)
        root_bg.add_widget(scroll)

        self.add_widget(root_bg)

    def on_pre_enter(self, *args):
        self.economy_bar.update(self.ctx.profile)
        self._refresh_levels()

    def _refresh_levels(self):
        self.level_list.clear_widgets()
        lm = self.ctx.level_manager
        for level_id in lm.get_all_level_ids():
            self.level_list.add_widget(self._build_level_row(level_id))

    def _build_level_row(self, level_id):
        lm = self.ctx.level_manager
        unlocked = lm.is_unlocked(level_id)
        phase = self.ctx.difficulty_manager.get_phase_for_level(level_id)
        result = lm.get_level_result(level_id)
        stars = result['stars'] if result else 0

        row = SolidBox(bg_color=COLOR_BAR_BG if unlocked else COLOR_LOCKED,
                        size_hint_y=None, height=dp(78), spacing=dp(12), padding=dp(12))

        info_col = BoxLayout(orientation='vertical')
        name_text = f"مرحله {level_id}"
        if not unlocked:
            name_text += '  (قفل)'
        name_label = PersianLabel(text=name_text, font_size='19sp', bold=True,
                                   color=COLOR_TEXT if unlocked else COLOR_MUTED,
                                   halign='left', valign='middle')
        name_label.bind(size=lambda w, s: setattr(w, 'text_size', s))
        info_col.add_widget(name_label)

        sub_text = phase['name_fa'] if unlocked else 'برای باز شدن، مرحله‌ی قبل رو کامل کن'
        if unlocked and result is not None:
            sub_text += f"    امتیاز: {stars}/3"
        sub_label = PersianLabel(text=sub_text, font_size='14sp', color=COLOR_MUTED,
                                  halign='left', valign='middle')
        sub_label.bind(size=lambda w, s: setattr(w, 'text_size', s))
        info_col.add_widget(sub_label)
        row.add_widget(info_col)

        if unlocked:
            start_btn = PersianButton(text='شروع', size_hint=(None, 1), width=dp(110),
                                       background_color=COLOR_PRIMARY, color=COLOR_TEXT)
            start_btn.bind(on_release=lambda *_a, lid=level_id: self._start_level(lid))
            row.add_widget(start_btn)

        return row

    def _start_level(self, level_id):
        game_screen = self.ctx.screen_manager.get_screen('game')
        game_screen.prepare_level(level_id, practice=False)
        self.ctx.screen_manager.goto('game')

    def _go_back(self):
        self.ctx.screen_manager.go_back(default_screen='main_menu')
