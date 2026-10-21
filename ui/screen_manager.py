"""
ui/screen_manager.py  (فاز ۵)

طبق فایل مرجع بخش ۵.۱۹: «GameScreenManager.go_back() دیگه از goto()
استفاده نمی‌کنه؛ مستقیماً self.current = self.navigation_history.pop()
رو ست می‌کنه (بدون push دوباره).»

منطق خودِ پشته (کجا باگ بود، چرا رفع شد) در
game_logic/navigation_history.py مستند و تست شده؛ این فایل فقط یک
پوشش نازک Kivy دورش می‌کشه -- بدون منطق تصمیم‌گیری اضافه اینجا.
"""
from kivy.uix.screenmanager import ScreenManager, NoTransition

from game_logic.navigation_history import NavigationHistory


class GameScreenManager(ScreenManager):
    def __init__(self, **kwargs):
        kwargs.setdefault('transition', NoTransition())
        super().__init__(**kwargs)
        self.navigation_history = NavigationHistory()

    def goto(self, screen_name, push=True, on_pre_enter=None):
        """می‌ره به screen_name. push=True (پیش‌فرض) یعنی مسیر برگشت
        حفظ می‌شه؛ push=False یعنی کل تاریخچه پاک و از این صفحه از نو
        شروع می‌شه (مثلاً «برگرد به منو» نباید بذاره کاربر با دکمه‌ی
        برگشت به عمق مراحل قبلی برگرده).

        on_pre_enter (اختیاری): تابعی که *قبل* از عوض‌شدن self.current
        صدا زده می‌شه -- برای مقداردهی صفحه‌ی مقصد (مثلاً «این مرحله
        رو بارگذاری کن») پیش از این‌که واقعاً دیده بشه."""
        if push:
            self.navigation_history.push(screen_name)
        else:
            self.navigation_history.clear(screen_name)
        if on_pre_enter is not None:
            on_pre_enter(self.get_screen(screen_name))
        self.current = screen_name

    def go_back(self, default_screen=None):
        """طبق بخش ۵.۱۹: مستقیماً pop می‌کنه، goto() صدا زده نمی‌شه.
        اگه جایی برای برگشتن نبود (روی اولین صفحه‌ایم)، به default_screen
        می‌ره (بدون push -- چون این یک goto نیست، فقط یک fallback
        امنه) یا اگه داده نشده بود، هیچ کاری نمی‌کنه."""
        previous = self.navigation_history.pop()
        if previous is not None:
            self.current = previous
            return previous
        if default_screen is not None and default_screen != self.current:
            self.current = default_screen
        return None
