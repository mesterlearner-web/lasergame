"""
ui/screens/challenge_screen.py  (فاز ۹)

صفحه‌ی تجمیعی «چالش‌ها» (مثل MissionsScreen): چالش روزانه + حالت بی‌نهایت + دستاوردها.
منطق در game_logic/{daily_challenge,endless_mode,achievements}.py است؛ اینجا فقط نمایش و اتصال به بازی.

اتصال به GameScreen: `prepare_generated(level, label, on_result, next_level)`؛ نتیجه‌ی هر مرحله را
GameWidget به `on_result(success)` می‌دهد و این صفحه پاداش/آمار را همان‌جا اعمال و ذخیره می‌کند.
"""
import time
from datetime import date

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen

from game_logic.daily_challenge import equivalent_level_for, reward_for
from game_logic.endless_mode import RUN_ENERGY_COST, equivalent_level
from ui.widgets.common import (
    COLOR_BAR_BG, COLOR_BG, COLOR_COIN, COLOR_MUTED, COLOR_PRIMARY, COLOR_TEXT,
    EconomyBar, SolidBox, TopBar,
)
from ui.widgets.persian_widgets import PersianButton, PersianLabel

#: date.weekday(): دوشنبه=۰ ... یکشنبه=۶
WEEKDAY_NAMES_FA = ('دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه', 'شنبه', 'یکشنبه')


class ChallengeScreen(Screen):
    def __init__(self, ctx, today_fn=date.today, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx
        self._today_fn = today_fn          # برای تست قابل‌تزریق است

        root_bg = SolidBox(bg_color=COLOR_BG, orientation='vertical')
        root_bg.add_widget(TopBar('چالش‌ها', on_back=self._go_back))
        self.economy_bar = EconomyBar()
        root_bg.add_widget(self.economy_bar)
        self.feedback_label = PersianLabel(text='', font_size='13sp', color=COLOR_MUTED,
                                           size_hint_y=None, height=dp(26))
        root_bg.add_widget(self.feedback_label)

        scroll = ScrollView()
        self.content = GridLayout(cols=1, size_hint_y=None, spacing=dp(14), padding=dp(16))
        self.content.bind(minimum_height=self.content.setter('height'))
        scroll.add_widget(self.content)
        root_bg.add_widget(scroll)
        self.add_widget(root_bg)

    # ---------------------------------------------------------------- چرخه‌ی صفحه
    def on_pre_enter(self, *args):
        endless = self.ctx.profile.endless
        if endless.is_running:
            # بازیکن وسط اجرای بی‌نهایت از بازی بیرون آمد (دکمه‌ی خروج/Back): اجرا تمام می‌شود.
            endless.finish_run()
            self.ctx.save()
        self.economy_bar.update(self.ctx.profile)
        self.feedback_label.set_text('')
        self._refresh()

    def _today(self):
        return self._today_fn()

    # ---------------------------------------------------------------- ساخت UI
    def _section_header(self, text):
        label = PersianLabel(text=text, font_size='17sp', bold=True, color=COLOR_TEXT,
                             size_hint_y=None, height=dp(32), halign='left', valign='middle')
        label.bind(size=lambda w, s: setattr(w, 'text_size', s))
        return label

    @staticmethod
    def _line(text, size='14sp', color=COLOR_MUTED, bold=False):
        label = PersianLabel(text=text, font_size=size, color=color, bold=bold, halign='left', valign='middle')
        label.bind(size=lambda w, s: setattr(w, 'text_size', s))
        return label

    def _refresh(self):
        self.content.clear_widgets()
        profile = self.ctx.profile
        self.content.add_widget(self._section_header('چالش روزانه'))
        self.content.add_widget(self._build_daily_row(profile.daily_challenge))
        self.content.add_widget(self._section_header('حالت بی‌نهایت'))
        self.content.add_widget(self._build_endless_row(profile))
        self.content.add_widget(self._section_header('دستاوردها'))
        for entry in profile.achievements.summary():
            self.content.add_widget(self._build_achievement_row(entry))

    def _build_daily_row(self, challenge):
        today = self._today()
        done = challenge.is_completed(today)
        row = SolidBox(bg_color=COLOR_BAR_BG, size_hint_y=None, height=dp(96), spacing=dp(10), padding=dp(12))
        info = BoxLayout(orientation='vertical')
        info.add_widget(self._line(
            f"{WEEKDAY_NAMES_FA[today.weekday()]} -- سختی ≈ مرحله‌ی {equivalent_level_for(today)}",
            '15sp', COLOR_TEXT, bold=True))
        streak = challenge.display_streak(today)
        if done:
            info.add_widget(self._line(f"امروز انجام شد ✓   استریک: {streak} روز", '14sp', COLOR_MUTED))
        else:
            reward = reward_for(streak + 1)
            bits = [f"{reward['coins']} سکه"] + ([f"{reward['gems']} جواهر"] if reward['gems'] else [])
            info.add_widget(self._line('پاداش: ' + ' + '.join(bits), '14sp', COLOR_COIN))
        info.add_widget(self._line(f"رکورد استریک: {challenge.best_streak}   کل: {challenge.total_completed}",
                                   '12sp', COLOR_MUTED))
        row.add_widget(info)
        action = BoxLayout(size_hint=(None, 1), width=dp(110))
        button = PersianButton(text='دوباره' if done else 'شروع', background_color=COLOR_PRIMARY, color=COLOR_TEXT)
        button.bind(on_release=lambda *_a: self._start_daily())
        action.add_widget(button)
        row.add_widget(action)
        return row

    def _build_endless_row(self, profile):
        endless = profile.endless
        row = SolidBox(bg_color=COLOR_BAR_BG, size_hint_y=None, height=dp(96), spacing=dp(10), padding=dp(12))
        info = BoxLayout(orientation='vertical')
        info.add_widget(self._line('تا کجا می‌توانی بروی؟', '15sp', COLOR_TEXT, bold=True))
        info.add_widget(self._line(f"رکورد: مرحله‌ی {endless.best_stage}   اجراها: {endless.total_runs}",
                                   '14sp', COLOR_MUTED))
        info.add_widget(self._line(f"هزینه‌ی هر اجرا: {RUN_ENERGY_COST} انرژی   (سختی از مرحله‌ی "
                                   f"{equivalent_level(1)} شروع و بالا می‌رود)", '12sp', COLOR_MUTED))
        row.add_widget(info)
        action = BoxLayout(size_hint=(None, 1), width=dp(110))
        button = PersianButton(text='شروع', background_color=COLOR_PRIMARY, color=COLOR_TEXT)
        button.bind(on_release=lambda *_a: self._start_endless())
        action.add_widget(button)
        row.add_widget(action)
        return row

    def _build_achievement_row(self, entry):
        row = SolidBox(bg_color=COLOR_BAR_BG, size_hint_y=None, height=dp(68), spacing=dp(10), padding=dp(12))
        info = BoxLayout(orientation='vertical')
        info.add_widget(self._line(entry['title'], '15sp', COLOR_TEXT if entry['unlocked'] else COLOR_MUTED, bold=True))
        info.add_widget(self._line(entry['description'], '12sp', COLOR_MUTED))
        row.add_widget(info)
        status = f"باز شد ✓" if entry['unlocked'] else f"{entry['reward_gems']} جواهر"
        row.add_widget(PersianLabel(text=status, font_size='12sp', size_hint=(None, 1), width=dp(84),
                                    color=COLOR_COIN if entry['unlocked'] else COLOR_MUTED))
        return row

    # ---------------------------------------------------------------- شروع بازی
    def _game(self):
        return self.ctx.screen_manager.get_screen('game')

    def _start_daily(self):
        today = self._today()
        level = self.ctx.profile.daily_challenge.build_level(today)
        self._game().prepare_generated(level, 'چالش روزانه',
                                       on_result=lambda success: self._daily_result(success, today))
        self.ctx.screen_manager.goto('game')

    def _start_endless(self):
        profile = self.ctx.profile
        now = time.time()
        profile.energy.update(now)
        if profile.energy.current_energy < RUN_ENERGY_COST:
            self.feedback_label.set_text('انرژی کافی نیست -- از فروشگاه بخر یا صبر کن.')
            return
        profile.energy.consume(RUN_ENERGY_COST, now=now)
        profile.endless.start_run()
        self.ctx.save()                    # مصرف انرژی فوراً ذخیره شود (مثل شروع مرحله‌ی کمپین)
        self._game().prepare_generated(profile.endless.build_level(), self._endless_label(),
                                       on_result=self._endless_result, next_level=self._next_endless_level)
        self.ctx.screen_manager.goto('game')

    # ---------------------------------------------------------------- نتیجه‌ی مرحله
    @staticmethod
    def _achievement_text(unlocked):
        if not unlocked:
            return ''
        return ' -- دستاورد: ' + '، '.join(f"{a['title']} (+{a['reward_gems']} جواهر)" for a in unlocked)

    def _daily_result(self, success, today):
        if not success:
            return {'message': 'زمان تمام شد!', 'next': 'retry'}
        profile = self.ctx.profile
        reward = profile.daily_challenge.complete(today, profile.economy, profile.achievements)
        self.ctx.save()
        if reward is None:
            return {'message': 'چالش دوباره انجام شد (پاداش امروز را قبلاً گرفته‌ای)', 'next': 'exit'}
        bits = [f"{reward['coins']} سکه"] + ([f"{reward['gems']} جواهر"] if reward['gems'] else [])
        return {'message': f"چالش روزانه انجام شد! +{' + '.join(bits)} -- استریک {reward['streak']}"
                           + self._achievement_text(reward['achievements']), 'next': 'exit'}

    def _endless_label(self):
        return f"بی‌نهایت -- مرحله‌ی {self.ctx.profile.endless.current_stage}"

    def _endless_result(self, success):
        profile = self.ctx.profile
        if success:
            summary = profile.endless.on_level_complete(profile.achievements, profile.economy)
            self.ctx.save()
            message = f"مرحله‌ی {summary['stage_cleared']} تمام شد! +{summary['coins']} سکه"
            if summary['new_best']:
                message += ' (رکورد جدید!)'
            return {'message': message + self._achievement_text(summary['achievements']), 'next': 'next'}
        summary = profile.endless.on_level_failed()
        self.ctx.save()
        return {'message': f"پایان اجرا! {summary['stages_cleared']} مرحله تمام کردی (رکورد: {summary['best_stage']})",
                'next': 'exit'}

    def _next_endless_level(self):
        return self.ctx.profile.endless.build_level(), self._endless_label()

    def _go_back(self):
        self.ctx.screen_manager.go_back(default_screen='main_menu')
