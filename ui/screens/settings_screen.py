"""
ui/screens/settings_screen.py  (فاز ۵)
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.metrics import dp

from game_logic.settings_manager import COLOR_BLIND_MODES
from ui.widgets.common import COLOR_BG, COLOR_SECONDARY, COLOR_TEXT, COLOR_MUTED, SolidBox, TopBar
from ui.widgets.persian_widgets import PersianButton, PersianLabel

_COLORBLIND_NAMES = {
    None: 'خاموش (پیش‌فرض)',
    'protanopia': 'کوررنگی نوع اول (Protanopia)',
    'deuteranopia': 'کوررنگی نوع دوم (Deuteranopia)',
    'tritanopia': 'کوررنگی نوع سوم (Tritanopia)',
}


class SettingsScreen(Screen):
    def __init__(self, ctx, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx
        self._reset_armed = False

        root_bg = SolidBox(bg_color=COLOR_BG, orientation='vertical')
        root_bg.add_widget(TopBar('تنظیمات', on_back=self._go_back))

        body = BoxLayout(orientation='vertical', spacing=dp(16), padding=dp(24))

        body.add_widget(self._section_label('حالت رنگ‌کوری'))
        self._note_label = PersianLabel(
            text='', font_size='12sp', color=COLOR_MUTED, size_hint_y=None, height=dp(24))
        body.add_widget(self._note_label)
        self.colorblind_btn = PersianButton(text='', background_color=COLOR_SECONDARY, color=COLOR_TEXT)
        self.colorblind_btn.bind(on_release=lambda *_a: self._cycle_colorblind())
        body.add_widget(self.colorblind_btn)

        body.add_widget(self._section_label('صدا و موسیقی'))
        sound_row = BoxLayout(spacing=dp(12))
        self.sound_btn = PersianButton(background_color=COLOR_SECONDARY, color=COLOR_TEXT)
        self.sound_btn.bind(on_release=lambda *_a: self._toggle_sound())
        self.music_btn = PersianButton(background_color=COLOR_SECONDARY, color=COLOR_TEXT)
        self.music_btn.bind(on_release=lambda *_a: self._toggle_music())
        sound_row.add_widget(self.sound_btn)
        sound_row.add_widget(self.music_btn)
        body.add_widget(sound_row)

        body.add_widget(BoxLayout())  # فاصله‌ی خالی -- دکمه‌ی ریست پایین بمونه

        body.add_widget(self._section_label('منطقه‌ی خطر'))
        self.reset_btn = PersianButton(background_color=(0.7, 0.2, 0.25, 1.0), color=COLOR_TEXT)
        self.reset_btn.bind(on_release=lambda *_a: self._on_reset_pressed())
        body.add_widget(self.reset_btn)

        root_bg.add_widget(body)
        self.add_widget(root_bg)

    def _section_label(self, text):
        lbl = PersianLabel(text=text, font_size='16sp', bold=True, color=COLOR_TEXT,
                            size_hint_y=None, height=dp(30), halign='left', valign='middle')
        lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        return lbl

    def on_pre_enter(self, *args):
        self._reset_armed = False
        self._refresh()

    def _refresh(self):
        settings = self.ctx.profile.settings
        self.colorblind_btn.set_text(_COLORBLIND_NAMES.get(settings.colorblind_mode, 'نامشخص'))
        self._note_label.set_text(
            'رنگ لیزر، هدف و آینه در صحنه‌ی بازی طبق این انتخاب تغییر می‌کنه '
            '(از دفعه‌ی بعدی که وارد مرحله می‌شی).')
        self.sound_btn.set_text('صدا: ' + ('روشن' if settings.sound_enabled else 'خاموش'))
        self.music_btn.set_text('موسیقی: ' + ('روشن' if settings.music_enabled else 'خاموش'))
        self.reset_btn.set_text(
            'مطمئنی؟ یک‌بار دیگه لمس کن تا کامل پاک بشه' if self._reset_armed
            else 'شروع از نو (پاک‌کردن کامل پیشرفت)')

    def _cycle_colorblind(self):
        settings = self.ctx.profile.settings
        idx = COLOR_BLIND_MODES.index(settings.colorblind_mode)
        next_mode = COLOR_BLIND_MODES[(idx + 1) % len(COLOR_BLIND_MODES)]
        settings.set_colorblind_mode(next_mode)
        self.ctx.save()
        self._refresh()

    def _toggle_sound(self):
        self.ctx.profile.settings.toggle_sound()
        self.ctx.save()
        self._refresh()

    def _toggle_music(self):
        self.ctx.profile.settings.toggle_music()
        self.ctx.save()
        # فاز۶: SettingsManager.music_enabled (که فاز۵ فقط ذخیره می‌کرد)
        # حالا واقعاً به AudioManager می‌رسه و بلافاصله اثر می‌کنه.
        self.ctx.audio_manager.on_music_setting_changed()
        self._refresh()

    def _on_reset_pressed(self):
        if not self._reset_armed:
            self._reset_armed = True
            self._refresh()
            return
        self.ctx.reset_profile()
        self._reset_armed = False
        self.ctx.screen_manager.goto('main_menu', push=False)

    def _go_back(self):
        self.ctx.screen_manager.go_back(default_screen='main_menu')
