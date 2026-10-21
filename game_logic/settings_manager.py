"""
game_logic/settings_manager.py  (فاز ۵، به‌روزرسانی‌شده در فاز۶)

ترجیحات بازیکن -- مستقل از Kivy، طبق همون الگوی بقیه‌ی managerها.

فاز۶: colorblind_mode حالا واقعاً توسط core/color_palette.ColorPalette
مصرف می‌شه (اعمال روی رنگ لیزر/آینه/هدف/پورتال/مانع/سیاه‌چاله در صحنه‌ی
بازی، طبق بخش۵.۱۶)؛ sound_enabled/music_enabled هم توسط
core/audio_manager.AudioManager خونده می‌شن (AppContext.audio_manager.
bind_settings). در فاز۵ این‌ها فقط ذخیره می‌شدن بدون هیچ مصرف‌کننده.
"""

COLOR_BLIND_MODES = (None, 'protanopia', 'deuteranopia', 'tritanopia')


class SettingsManager:
    def __init__(self, colorblind_mode=None, sound_enabled=True, music_enabled=True):
        if colorblind_mode not in COLOR_BLIND_MODES:
            raise ValueError(f"حالت رنگ‌کوری ناشناخته: {colorblind_mode!r}")
        self.colorblind_mode = colorblind_mode
        self.sound_enabled = sound_enabled
        self.music_enabled = music_enabled

    def set_colorblind_mode(self, mode):
        if mode not in COLOR_BLIND_MODES:
            raise ValueError(f"حالت رنگ‌کوری ناشناخته: {mode!r}")
        self.colorblind_mode = mode

    def toggle_sound(self):
        self.sound_enabled = not self.sound_enabled
        return self.sound_enabled

    def toggle_music(self):
        self.music_enabled = not self.music_enabled
        return self.music_enabled

    def to_dict(self):
        return {
            'colorblind_mode': self.colorblind_mode,
            'sound_enabled': self.sound_enabled,
            'music_enabled': self.music_enabled,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            colorblind_mode=data.get('colorblind_mode'),
            sound_enabled=data.get('sound_enabled', True),
            music_enabled=data.get('music_enabled', True),
        )
