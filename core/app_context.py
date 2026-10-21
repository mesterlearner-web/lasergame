"""
core/app_context.py  (فاز ۵، بسط فاز۶)

یک باندل ساده از منابع مشترک بین همه‌ی صفحات -- طبق همون منطقی که
`PlayerProfile` (فاز۴) پشت مدیرهای مجزا رو جمع کرد: به‌جای این‌که هر
صفحه پارامترهای جدا (level_manager, save_manager, profile, ...) بگیره
و از نو بسازه، یک AppContext واحد در main.py ساخته و بین همه‌ی صفحات
به‌اشتراک گذاشته می‌شه.

⚠️ AppContext خودش هیچ منطق بازی‌ای نداره -- فقط نگه‌دارنده‌ست، دقیقاً
هم‌راستا با اصل تکرارشده‌ی پروژه («Kivy فقط orchestration می‌کنه،
منطق واقعی جای دیگه‌ست»).

⚠️ animation_manager/audio_manager عمداً اختیاری‌ان (پیش‌فرض None) و
اینجا import نمی‌شن -- AnimationManager (core/game.py) در سطح ماژول
از kivy.animation استفاده می‌کنه، پس اگه بی‌قیدوشرط اینجا import می‌شد،
خودِ AppContext (که تست‌های فاز۵/۶ بدون Kivy مستقیم import می‌کنن)
دیگه بدون نصب واقعی Kivy قابل‌import نبود. main.py (جایی که Kivy واقعاً
در دسترسه) این دو رو می‌سازه و پاس می‌ده.
"""


class AppContext:
    def __init__(self, screen_manager, save_manager, level_manager, difficulty_manager, profile,
                 animation_manager=None, audio_manager=None, notification_manager=None):
        self.screen_manager = screen_manager
        self.save_manager = save_manager
        self.level_manager = level_manager
        self.difficulty_manager = difficulty_manager
        # طبق save_manager.py: profile.settings هم بخشی از همون
        # PlayerProfile ذخیره‌شونده‌ست -- یک SettingsManager جدا اینجا
        # نگه نمی‌داریم تا دو نسخه از تنظیمات هیچ‌وقت ناهم‌خوان نشن.
        self.profile = profile
        self.animation_manager = animation_manager
        self.audio_manager = audio_manager
        self.notification_manager = notification_manager
        if self.audio_manager is not None:
            self.audio_manager.bind_settings(self.profile.settings)

    def save(self):
        """ذخیره‌ی فوری -- بعد از هر تغییر مهم (خرید، پایان مرحله، ...)
        صدا زده می‌شه، دقیقاً هم‌راستا با نقاط ذخیره‌ی فاز۴."""
        self.save_manager.save(self.profile)

    def get_color_palette(self):
        """طبق فاز۶ (بخش۵.۱۶) -- پالت رنگ صحنه‌ی بازی، همیشه بر پایه‌ی
        ترجیح فعلی بازیکن (نه یک نسخه‌ی کش‌شده که ممکنه بعد از تغییر
        در SettingsScreen قدیمی بمونه)."""
        from core.color_palette import ColorPalette
        return ColorPalette(self.profile.settings.colorblind_mode)

    def reset_profile(self):
        """طبق SettingsScreen (فاز۵) -- «شروع از نو». چون همه‌ی صفحات
        همیشه از روی self.ctx.level_manager/self.ctx.profile (نه یک
        کپی محلی) می‌خونن، جایگزین‌کردن این دو مرجع همین‌جا برای همه‌ی
        صفحات از دفعه‌ی بعد که دیده می‌شن کافیه."""
        from game_logic.level_manager import LevelManager
        self.save_manager.reset()
        self.level_manager = LevelManager(levels_dir=self.level_manager.levels_dir)
        self.profile = self.save_manager.load(self.level_manager)
        if self.audio_manager is not None:
            self.audio_manager.bind_settings(self.profile.settings)
