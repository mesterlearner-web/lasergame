"""
game_logic/navigation_history.py  (فاز ۵)

منطق خالص پشته‌ی ناوبری بین صفحات -- بدون هیچ وابستگی به Kivy، دقیقاً
هم‌راستا با الگوی تکرارشده‌ی این پروژه (raycast/scene_builder/
level_validator): منطق حساس و باگ‌خیز همیشه اول به‌صورت Kivy-agnostic
نوشته و تست می‌شه؛ لایه‌ی نازک Kivy (ui/screen_manager.py) فقط دورش
رو می‌پوشونه.

باگ دقیقی که این معماری حلش می‌کنه (فایل مرجع بخش ۵.۱۹): اگه
`go_back()` از طریق `goto()` پیاده بشه، و `goto()` هر بار مقصد رو
push کنه، اون‌وقت خودِ عمل «برگشتن» هم یک ورودی تازه به پشته اضافه
می‌کنه -- یعنی برگشت از C به B، بعد یک‌بار دیگه برگشت، به‌جای رسیدن
به A، دوباره به B برمی‌گرده (چون پشته به‌جای [A, B, C] چیزی مثل
[A, B, C, B] شده). رفع درست: `go_back()` باید مستقیماً pop کنه و
نتیجه رو *بدون push دوباره* روی صفحه‌ی فعلی بگذاره -- دقیقاً همون‌کاری
که `pop()` پایین انجام می‌ده.
"""


class NavigationHistory:
    def __init__(self, initial_screen=None):
        self._stack = []
        if initial_screen is not None:
            self._stack.append(initial_screen)

    def push(self, screen_name):
        """صفحه‌ی تازه رو روی پشته می‌ذاره -- طبق قرارداد goto()."""
        self._stack.append(screen_name)

    def pop(self):
        """صفحه‌ی فعلی رو از پشته حذف می‌کنه و صفحه‌ی *قبلی* (تازه سرِ
        پشته) رو برمی‌گردونه، بدون این‌که دوباره push بشه -- این دقیقاً
        همون رفتاریه که فایل مرجع برای go_back() می‌خواد. اگه فقط یک
        صفحه (یا هیچی) روی پشته مونده باشه، کاری نمی‌کنه و None
        برمی‌گردونه (نمی‌شه از اولین صفحه هم عقب‌تر رفت)."""
        if len(self._stack) <= 1:
            return None
        self._stack.pop()
        return self._stack[-1]

    def current(self):
        return self._stack[-1] if self._stack else None

    def can_go_back(self):
        return len(self._stack) > 1

    def clear(self, screen_name=None):
        """کل پشته رو خالی می‌کنه -- برای «برگرد به منوی اصلی و
        تاریخچه رو فراموش کن» (وگرنه دکمه‌ی برگشت از منو می‌تونست تا
        ابد به عمق مراحل قبلی برگرده)."""
        self._stack = [screen_name] if screen_name is not None else []

    def __len__(self):
        return len(self._stack)

    def __repr__(self):
        return f"NavigationHistory({self._stack!r})"
