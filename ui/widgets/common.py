"""
ui/widgets/common.py  (فاز ۵)

ویجت‌های مشترک بین همه‌ی صفحات -- به‌جای این‌که هر ۸ صفحه دوباره کد
نوار بالا/نوار اقتصاد رو بنویسه (و به‌طور بالقوه یک‌جا shape() رو یادش
بره)، یک‌بار اینجا نوشته و همه‌جا استفاده می‌شه.
"""
import time

from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

from ui.widgets.persian_widgets import PersianLabel, PersianButton

# طبق فایل مرجع بخش ۵.۱۶ (پالت اصلاح‌شده) -- استفاده‌ی محدود همین‌جا؛
# اعمال کامل پالت/حالت رنگ‌کوری در فاز۶ (طراحی بصری نهایی) انجام می‌شه.
COLOR_BG = (0.09, 0.09, 0.13, 1.0)
COLOR_BAR_BG = (0.14, 0.14, 0.20, 1.0)
COLOR_PRIMARY = (0.20, 0.87, 0.67, 1.0)    # #33DDAA
COLOR_SECONDARY = (0.53, 0.33, 0.87, 1.0)  # #8855DD
COLOR_GEM = (0.72, 0.30, 1.0, 1.0)         # #B84DFF
COLOR_COIN = (1.0, 0.85, 0.3, 1.0)
COLOR_TEXT = (0.95, 0.95, 0.97, 1.0)
COLOR_MUTED = (0.6, 0.6, 0.68, 1.0)
COLOR_LOCKED = (0.35, 0.35, 0.4, 1.0)


class SolidBox(BoxLayout):
    """BoxLayout با یک رنگ پس‌زمینه‌ی صاف -- چون Kivy پیش‌فرض شفافه و
    این پروژه بدون KivyMD کار می‌کنه (بخش۳: KivyMD اختیاریه)."""

    def __init__(self, bg_color=COLOR_BG, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*bg_color)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size


class TopBar(SolidBox):
    """نوار بالای هر صفحه: دکمه‌ی برگشت (اختیاری) + عنوان.

    فاز۸ -- چینش با اندازه‌ی واقعی فونت اصلاح شد: قبلاً دکمه‌ی برگشت *و* یک فاصله‌ی خالی
    هم‌اندازه‌اش (برای وسط‌ماندن عنوان) هرکدام ۱۱۰dp بودند؛ روی گوشی ۳۶۰dp فقط ≈۹۶dp برای
    عنوان می‌ماند و با متریک واقعی DejaVu Bold در ۲۲sp، ۵ از ۷ عنوان صفحه سرریز می‌کردند
    (به ۲ تا ۳ خط می‌شکستند داخل نوار ۶۴dp). الان دکمه ۸۴dp است (متن «بازگشت» ≈۵۱dp جا می‌شود)
    و فاصله‌ی خالی حذف شده (الگوی استاندارد Toolbar اندروید: دکمه و عنوانِ کنارش) -- شکاف عنوان
    روی ۳۶۰dp ≈۲۴۲dp می‌شود و بلندترین عنوان («تمرین (Sandbox)» ≈۲۰۰dp، کران بالا) هم جا می‌شود."""

    def __init__(self, title, on_back=None, **kwargs):
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', dp(64))
        kwargs.setdefault('padding', (dp(12), dp(8)))
        kwargs.setdefault('spacing', dp(10))
        super().__init__(bg_color=COLOR_BAR_BG, **kwargs)

        if on_back is not None:
            back_btn = PersianButton(
                text='بازگشت', size_hint=(None, 1), width=dp(84),
                background_color=COLOR_SECONDARY, color=COLOR_TEXT)
            back_btn.bind(on_release=lambda *_a: on_back())
            self.add_widget(back_btn)

        self.title_label = PersianLabel(
            text=title, font_size='22sp', bold=True, color=COLOR_TEXT,
            halign='center', valign='middle')
        self.title_label.bind(size=lambda w, s: setattr(w, 'text_size', s))
        self.add_widget(self.title_label)


class EconomyBar(SolidBox):
    """سکه/جواهر/انرژی -- روی هر صفحه‌ای که اقتصاد بازیکن مرتبطه. باید
    update() در on_pre_enter صفحه صدا زده بشه (چون انرژی پیوسته
    بازآفرینی می‌شه -- بخش۵.۱۱ -- و ممکنه از آخرین بار که این صفحه
    دیده شده تغییر کرده باشه)."""

    def __init__(self, **kwargs):
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', dp(44))
        kwargs.setdefault('padding', (dp(12), dp(4)))
        super().__init__(bg_color=COLOR_BAR_BG, **kwargs)
        self.label = PersianLabel(text='', font_size='16sp', color=COLOR_TEXT)
        self.add_widget(self.label)

    def update(self, profile, now=None):
        energy = profile.energy
        energy.update(now if now is not None else time.time())
        economy = profile.economy
        self.label.set_text(
            f"سکه: {economy.coins}    جواهر: {economy.gems}    "
            f"انرژی: {energy.current_energy}/{energy.max_energy}")
