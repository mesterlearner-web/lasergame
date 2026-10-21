"""
game_logic/back_navigation.py  (فاز ۸)

منطق خالص «دکمه‌ی Back سخت‌افزاری اندروید چه کار کند؟» -- بدون وابستگی به Kivy، مطابق
الگوی تکرارشده‌ی پروژه (NavigationHistory، shake_offset، ...): منطق تصمیم‌گیری جدا و
قابل‌تست؛ main.py فقط آن را به رویداد کلید Kivy وصل می‌کند.

⚠️ باگی که در بازبینی فاز۸ پیدا شد: تا قبل از این، Back اندروید اصلاً مدیریت
نمی‌شد. رفتار پیش‌فرض Kivy برای کلید Back (کد ۲۷، همان Esc) *بستن کامل برنامه*
است -- یعنی بازیکن داخل «فروشگاه» یا «تنظیمات» Back می‌زد و به‌جای رسیدن به منوی
اصلی، کل بازی بسته می‌شد. هر برنامه‌ی اندرویدی انتظار دارد Back یک سطح برگردد و
فقط از صفحه‌ی ریشه خارج شود.

مقصد پیش‌فرض (وقتی تاریخچه‌ی ناوبری خالی است) همان default_screen‌ای است که دکمه‌های
«بازگشت/خروج» خودِ UI هر صفحه استفاده می‌کنند، تا Back سخت‌افزاری و دکمه‌ی روی صفحه
همیشه یک مقصد بدهند.
"""

#: Kivy کلید Back اندروید را با همان کد Esc گزارش می‌کند.
ANDROID_BACK_KEY = 27

#: Back از این صفحه یعنی خروج از برنامه (رفتار استاندارد اندروید).
ROOT_SCREEN = 'main_menu'

#: صفحه‌هایی که مقصد پیش‌فرض‌شان main_menu نیست (مثل دکمه‌ی «خروج» GameScreen).
_FALLBACK_SCREEN = {
    'game': 'level_select',
}


def decide_back_action(current_screen):
    """('exit_app', None) یا ('go_back', default_screen).

    exit_app یعنی رویداد را مصرف نکن تا Kivy برنامه را ببندد؛ go_back یعنی
    screen_manager.go_back(default_screen=...) را صدا بزن و رویداد را مصرف کن."""
    if current_screen is None or current_screen == ROOT_SCREEN:
        return 'exit_app', None
    return 'go_back', _FALLBACK_SCREEN.get(current_screen, ROOT_SCREEN)
