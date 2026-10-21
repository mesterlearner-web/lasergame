"""
ui/screens/missions_screen.py  (فاز ۷)

یک صفحه‌ی تجمیعی برای هر ۴ سیستم نگه‌داشت (بخش۵.۱۳ تا ۵.۱۵): جایزه‌ی
ورود روزانه، ماموریت‌های روزانه، ماموریت‌های هفتگی، چالش هفتگی --
به‌جای ۴ صفحه‌ی جدا، دقیقاً مثل خیلی از بازی‌های واقعی که این‌ها رو
زیر یک تب/صفحه جمع می‌کنن.
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp

from ui.widgets.common import (
    COLOR_BG, COLOR_BAR_BG, COLOR_PRIMARY, COLOR_GEM, COLOR_COIN, COLOR_TEXT, COLOR_MUTED,
    EconomyBar, SolidBox, TopBar,
)
from ui.widgets.persian_widgets import PersianButton, PersianLabel


class MissionsScreen(Screen):
    def __init__(self, ctx, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx

        root_bg = SolidBox(bg_color=COLOR_BG, orientation='vertical')
        root_bg.add_widget(TopBar('ماموریت‌ها', on_back=self._go_back))
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

    def on_pre_enter(self, *args):
        self.economy_bar.update(self.ctx.profile)
        self.feedback_label.set_text('')
        self._refresh()

    def _section_header(self, text):
        lbl = PersianLabel(text=text, font_size='17sp', bold=True, color=COLOR_TEXT,
                            size_hint_y=None, height=dp(32), halign='left', valign='middle')
        lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        return lbl

    def _refresh(self):
        self.content.clear_widgets()
        profile = self.ctx.profile

        # ---- جایزه‌ی ورود روزانه ----
        self.content.add_widget(self._section_header('جایزه‌ی ورود روزانه'))
        self.content.add_widget(self._build_daily_reward_row(profile.daily_rewards))

        # ---- ماموریت‌های روزانه ----
        self.content.add_widget(self._section_header('ماموریت‌های روزانه'))
        for m in profile.missions.daily_missions:
            self.content.add_widget(self._build_mission_row(m))

        # ---- ماموریت‌های هفتگی ----
        self.content.add_widget(self._section_header('ماموریت‌های هفتگی'))
        for m in profile.missions.weekly_missions:
            self.content.add_widget(self._build_mission_row(m))

        # ---- چالش هفتگی ----
        self.content.add_widget(self._section_header('چالش هفتگی'))
        self.content.add_widget(self._build_weekly_challenge_row(profile.weekly_challenge))

    def _build_daily_reward_row(self, daily_rewards):
        row = SolidBox(bg_color=COLOR_BAR_BG, size_hint_y=None, height=dp(84), spacing=dp(10), padding=dp(12))
        info_col = BoxLayout(orientation='vertical')
        can_claim = daily_rewards.can_claim_today()
        preview = daily_rewards.preview_next_reward()
        streak_text = f"استریک فعلی: {daily_rewards.current_streak} روز (رکورد: {daily_rewards.longest_streak})"
        streak_label = PersianLabel(text=streak_text, font_size='14sp', color=COLOR_MUTED,
                                     halign='left', valign='middle')
        streak_label.bind(size=lambda w, s: setattr(w, 'text_size', s))
        info_col.add_widget(streak_label)

        reward_bits = [f"{preview.get('coins', 0)} سکه"]
        if preview.get('gems'):
            reward_bits.append(f"{preview['gems']} جواهر")
        reward_label = PersianLabel(text='پاداش امروز: ' + ' + '.join(reward_bits), font_size='14sp',
                                     color=COLOR_COIN, halign='left', valign='middle')
        reward_label.bind(size=lambda w, s: setattr(w, 'text_size', s))
        info_col.add_widget(reward_label)
        row.add_widget(info_col)

        action_col = BoxLayout(size_hint=(None, 1), width=dp(110))
        if can_claim:
            claim_btn = PersianButton(text='دریافت', background_color=COLOR_PRIMARY, color=COLOR_TEXT)
            claim_btn.bind(on_release=lambda *_a: self._claim_daily_reward())
            action_col.add_widget(claim_btn)
        else:
            action_col.add_widget(PersianLabel(text='دریافت‌شده', font_size='12sp', color=COLOR_MUTED))
        row.add_widget(action_col)
        return row

    def _build_mission_row(self, mission):
        row = SolidBox(bg_color=COLOR_BAR_BG, size_hint_y=None, height=dp(76), spacing=dp(10), padding=dp(12))
        info_col = BoxLayout(orientation='vertical')
        name_label = PersianLabel(text=mission.name_fa, font_size='15sp', bold=True, color=COLOR_TEXT,
                                   halign='left', valign='middle')
        name_label.bind(size=lambda w, s: setattr(w, 'text_size', s))
        info_col.add_widget(name_label)

        desc_text = f"{mission.description_fa}   ({mission.progress}/{mission.target_value})"
        desc_label = PersianLabel(text=desc_text, font_size='12sp', color=COLOR_MUTED,
                                   halign='left', valign='middle')
        desc_label.bind(size=lambda w, s: setattr(w, 'text_size', s))
        info_col.add_widget(desc_label)
        row.add_widget(info_col)

        action_col = BoxLayout(size_hint=(None, 1), width=dp(110))
        if mission.claimed:
            action_col.add_widget(PersianLabel(text='گرفته‌شده', font_size='12sp', color=COLOR_MUTED))
        elif mission.is_complete:
            claim_btn = PersianButton(text='دریافت', background_color=COLOR_PRIMARY, color=COLOR_TEXT)
            claim_btn.bind(on_release=lambda *_a, mid=mission.mission_id: self._claim_mission(mid))
            action_col.add_widget(claim_btn)
        else:
            action_col.add_widget(PersianLabel(text='در جریان', font_size='12sp', color=COLOR_MUTED))
        row.add_widget(action_col)
        return row

    def _build_weekly_challenge_row(self, challenge):
        row = SolidBox(bg_color=COLOR_BAR_BG, size_hint_y=None, height=dp(84), spacing=dp(10), padding=dp(12))
        info_col = BoxLayout(orientation='vertical')
        progress_text = f"پیشرفت: {challenge.progress}/{challenge.target}"
        progress_label = PersianLabel(text=progress_text, font_size='14sp', color=COLOR_TEXT,
                                       halign='left', valign='middle')
        progress_label.bind(size=lambda w, s: setattr(w, 'text_size', s))
        info_col.add_widget(progress_label)

        # طبق بخش۵.۱۵ -- رتبه‌بندی فعلاً وجود نداره (نیازمند بک‌اند
        # واقعی)؛ فقط پاداش شرکت نشون داده می‌شه، نه یک «N/A» گیج‌کننده.
        note_label = PersianLabel(
            text='پاداش شرکت در دسترسه -- رتبه‌بندی جهانی به‌زودی',
            font_size='12sp', color=COLOR_GEM, halign='left', valign='middle')
        note_label.bind(size=lambda w, s: setattr(w, 'text_size', s))
        info_col.add_widget(note_label)
        row.add_widget(info_col)

        action_col = BoxLayout(size_hint=(None, 1), width=dp(110))
        if challenge.claimed:
            action_col.add_widget(PersianLabel(text='گرفته‌شده', font_size='12sp', color=COLOR_MUTED))
        elif challenge.is_complete:
            claim_btn = PersianButton(text='دریافت', background_color=COLOR_PRIMARY, color=COLOR_TEXT)
            claim_btn.bind(on_release=lambda *_a: self._claim_weekly_challenge())
            action_col.add_widget(claim_btn)
        else:
            action_col.add_widget(PersianLabel(text='در جریان', font_size='12sp', color=COLOR_MUTED))
        row.add_widget(action_col)
        return row

    def _claim_daily_reward(self):
        profile = self.ctx.profile
        reward = profile.daily_rewards.claim()
        profile.economy.apply_level_rewards(reward)
        # فاز۹ (فایل مرجع بخش ۶): دستاورد streak_25 -- استریک جایزه‌ی ورود روزانه به ۲۵ روز برسد.
        unlocked = profile.achievements.check_streak(profile.daily_rewards.current_streak, profile.economy)
        self.ctx.audio_manager.play_sfx('purchase')
        self.ctx.save()
        message = f"جایزه‌ی روز {profile.daily_rewards.current_streak} دریافت شد."
        if unlocked:
            message += ' دستاورد: ' + '، '.join(a['title'] for a in unlocked)
        self.feedback_label.set_text(message)
        self.economy_bar.update(self.ctx.profile)
        self._refresh()

    def _claim_mission(self, mission_id):
        reward = self.ctx.profile.missions.claim(mission_id)
        self.ctx.profile.economy.apply_level_rewards(reward)
        self.ctx.audio_manager.play_sfx('purchase')
        self.ctx.save()
        self.feedback_label.set_text('پاداش ماموریت دریافت شد.')
        self.economy_bar.update(self.ctx.profile)
        self._refresh()

    def _claim_weekly_challenge(self):
        reward = self.ctx.profile.weekly_challenge.claim_rewards()
        self.ctx.profile.economy.apply_level_rewards(reward)
        self.ctx.audio_manager.play_sfx('purchase')
        self.ctx.save()
        self.feedback_label.set_text('پاداش چالش هفتگی دریافت شد.')
        self.economy_bar.update(self.ctx.profile)
        self._refresh()

    def _go_back(self):
        self.ctx.screen_manager.go_back(default_screen='main_menu')
