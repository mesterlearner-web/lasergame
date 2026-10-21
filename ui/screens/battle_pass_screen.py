"""
ui/screens/battle_pass_screen.py  (فاز ۵)
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.gridlayout import GridLayout
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

from game_logic.battle_pass_manager import MAX_LEVEL
from ui.widgets.common import (
    COLOR_BG, COLOR_BAR_BG, COLOR_PRIMARY, COLOR_GEM, COLOR_COIN, COLOR_TEXT, COLOR_MUTED,
    SolidBox, TopBar,
)
from ui.widgets.persian_widgets import PersianButton, PersianLabel


class ProgressBar(SolidBox):
    """نوار پیشرفت ساده -- بدون وابستگی به هیچ آیکون/فونتی، فقط دو
    مستطیل (پس‌زمینه + پرشده)."""

    def __init__(self, **kwargs):
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', dp(22))
        super().__init__(bg_color=(0.25, 0.25, 0.32, 1.0), **kwargs)
        self.fraction = 0.0
        with self.canvas.after:
            Color(*COLOR_PRIMARY)
            self._fill_rect = Rectangle(pos=self.pos, size=(0, self.height))
        self.bind(pos=self._redraw, size=self._redraw)

    def set_fraction(self, fraction):
        self.fraction = max(0.0, min(1.0, fraction))
        self._redraw()

    def _redraw(self, *args):
        self._fill_rect.pos = self.pos
        self._fill_rect.size = (self.width * self.fraction, self.height)


class BattlePassScreen(Screen):
    def __init__(self, ctx, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

        root_bg = SolidBox(bg_color=COLOR_BG, orientation='vertical')
        root_bg.add_widget(TopBar('Battle Pass', on_back=self._go_back))

        summary = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(90),
                             padding=(dp(16), dp(8)), spacing=dp(6))
        self.level_label = PersianLabel(text='', font_size='18sp', bold=True, color=COLOR_TEXT,
                                         size_hint_y=None, height=dp(28))
        summary.add_widget(self.level_label)
        self.progress_bar = ProgressBar()
        summary.add_widget(self.progress_bar)
        self.progress_label = PersianLabel(text='', font_size='13sp', color=COLOR_MUTED,
                                            size_hint_y=None, height=dp(22))
        summary.add_widget(self.progress_label)
        root_bg.add_widget(summary)

        self.feedback_label = PersianLabel(text='', font_size='13sp', color=COLOR_MUTED,
                                            size_hint_y=None, height=dp(24))
        root_bg.add_widget(self.feedback_label)

        scroll = ScrollView()
        self.reward_list = GridLayout(cols=1, size_hint_y=None, spacing=dp(8), padding=dp(16))
        self.reward_list.bind(minimum_height=self.reward_list.setter('height'))
        scroll.add_widget(self.reward_list)
        root_bg.add_widget(scroll)

        self.add_widget(root_bg)

    def on_pre_enter(self, *args):
        self.feedback_label.set_text('')
        self._refresh()

    def _refresh(self):
        bp = self.ctx.profile.battle_pass
        current = bp.get_current_level()
        self.level_label.set_text(f"سطح {current} از {MAX_LEVEL}"
                                   f"{'  (نسخه‌ی پولی فعال)' if bp.is_premium else ''}")

        progress = bp.get_progress_to_next_level()
        if progress is None:
            self.progress_bar.set_fraction(1.0)
            self.progress_label.set_text('به بالاترین سطح رسیدی!')
        else:
            have, need = progress
            self.progress_bar.set_fraction(have / need if need else 1.0)
            self.progress_label.set_text(f"{have} از {need} XP تا سطح بعد")

        self.reward_list.clear_widgets()
        for level in range(1, MAX_LEVEL + 1):
            self.reward_list.add_widget(self._build_reward_row(level, current))

    def _build_reward_row(self, level, current_level):
        bp = self.ctx.profile.battle_pass
        reached = level <= current_level
        claimed = level in bp.claimed_levels
        reward = bp.get_reward(level)

        row = SolidBox(bg_color=COLOR_BAR_BG, size_hint_y=None, height=dp(64),
                        spacing=dp(10), padding=dp(12))
        base_color = COLOR_TEXT if reached else COLOR_MUTED
        level_label = PersianLabel(text=f"سطح {level}:", font_size='15sp', color=base_color,
                                    size_hint_x=None, width=dp(70), halign='left', valign='middle')
        level_label.bind(size=lambda w, s: setattr(w, 'text_size', s))
        row.add_widget(level_label)

        reward_col = BoxLayout(orientation='vertical')
        coin_text = f"{reward.get('coins', 0)} سکه"
        coin_label = PersianLabel(text=coin_text, font_size='14sp',
                                   color=COLOR_COIN if reached else COLOR_MUTED,
                                   halign='left', valign='middle')
        coin_label.bind(size=lambda w, s: setattr(w, 'text_size', s))
        reward_col.add_widget(coin_label)
        if reward.get('gems') or reward.get('special_items'):
            extra_bits = []
            if reward.get('gems'):
                extra_bits.append(f"+{reward['gems']} جواهر")
            if reward.get('special_items'):
                extra_bits.append('+ آیتم ویژه')
            extra_label = PersianLabel(text='  '.join(extra_bits), font_size='13sp',
                                        color=COLOR_GEM if reached else COLOR_MUTED,
                                        halign='left', valign='middle')
            extra_label.bind(size=lambda w, s: setattr(w, 'text_size', s))
            reward_col.add_widget(extra_label)
        row.add_widget(reward_col)

        action_col = BoxLayout(size_hint=(None, 1), width=dp(110))
        if claimed:
            action_col.add_widget(PersianLabel(text='گرفته‌شده', font_size='12sp', color=COLOR_MUTED))
        elif reached:
            claim_btn = PersianButton(text='دریافت', background_color=COLOR_PRIMARY, color=COLOR_TEXT)
            claim_btn.bind(on_release=lambda *_a, lv=level: self._claim(lv))
            action_col.add_widget(claim_btn)
        else:
            action_col.add_widget(PersianLabel(text='قفل', font_size='12sp', color=COLOR_MUTED))
        row.add_widget(action_col)
        return row

    def _claim(self, level):
        bp = self.ctx.profile.battle_pass
        try:
            reward = bp.claim_reward(level)
        except ValueError as exc:
            self.feedback_label.set_text(str(exc))
            return
        self.ctx.profile.economy.apply_level_rewards(reward)
        self.ctx.save()
        self.feedback_label.set_text(f"پاداش سطح {level} دریافت شد.")
        self._refresh()

    def _go_back(self):
        self.ctx.screen_manager.go_back(default_screen='main_menu')
