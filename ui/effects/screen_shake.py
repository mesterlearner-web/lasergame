"""
ui/effects/screen_shake.py  (فاز ۶)

طبق فایل مرجع بخش ۵.۷: «Screen Shake: AdvancedScreenShake بخش۵ --
پارامتر پایه‌ی یکسان (۵px/۱۵۰ms)، امکانات بیشتر.»

ریاضیات افت شدت لرزش (shake_offset) عمداً از خودِ کلاس Kivy-وابسته
جدا شده -- دقیقاً همون الگوی تکرارشده‌ی این پروژه (EnergyManager،
NavigationHistory، ...): منطق حساس همیشه یک تابع خالص و تست‌پذیره،
پوشش Kivy فقط دورش زمان‌بندی (Clock) می‌چینه.
"""
import random

try:
    from kivy.clock import Clock
except Exception:  # pragma: no cover -- در sandbox بدون Kivy نصب نمی‌شه؛
    # shake_offset (تابع خالص زیر) بدون این import هم کامل قابل‌تست است.
    Clock = None

BASE_AMPLITUDE_PX = 5.0
BASE_DURATION_S = 0.150


def shake_offset(elapsed, duration, amplitude, rand_x, rand_y):
    """جابه‌جایی (dx, dy) در لحظه‌ی elapsed از یک لرزش به طول duration
    و دامنه‌ی amplitude. rand_x/rand_y باید در بازه‌ی [-1, 1] باشن --
    از بیرون تزریق می‌شن (نه random.uniform مستقیم اینجا) تا این تابع
    بدون وابستگی به seed تصادفی، به‌طور قطعی قابل‌تست باشه. دامنه با
    گذر زمان به‌صورت خطی به صفر می‌رسه (کم‌شدن تدریجی شدت، نه قطع
    ناگهانی)."""
    if duration <= 0.0 or elapsed >= duration:
        return 0.0, 0.0
    remaining_fraction = 1.0 - (elapsed / duration)
    return rand_x * amplitude * remaining_fraction, rand_y * amplitude * remaining_fraction


class AdvancedScreenShake:
    """فاز۱۰ (مشکل شناخته‌شده #8): قبلاً `widget.pos` را جابه‌جا می‌کرد. ولی GameWidget با مختصات
    مطلق پنجره رسم می‌کند (pos را نادیده می‌گیرد) => صحنه نمی‌لرزید، فقط برچسب‌های HUD می‌لرزیدند، و
    هر فریمِ لرزش `bind(pos=...)` کل canvas را از نو می‌ساخت. حالا اگر ویجت هدف یک `shake_translate`
    (kivy.graphics.Translate داخل canvas.before/after) داشته باشد، همان جابه‌جا می‌شود -- کل صحنه +
    HUD با هم می‌لرزند و هیچ بازسازی‌ای رخ نمی‌دهد. ویجتی که translate ندارد به رفتار قبلی (pos) برمی‌گردد."""

    def __init__(self, target_widget):
        self.widget = target_widget
        self._original_pos = None
        self._event = None
        self._elapsed = 0.0
        self._duration = BASE_DURATION_S
        self._amplitude = BASE_AMPLITUDE_PX

    @property
    def active(self):
        return self._event is not None

    def _translate(self):
        return getattr(self.widget, 'shake_translate', None)

    def _apply(self, dx, dy):
        translate = self._translate()
        if translate is not None:
            translate.xy = (dx, dy)
        else:
            ox, oy = self._original_pos
            self.widget.pos = (ox + dx, oy + dy)

    def shake(self, amplitude=None, duration=None):
        if self._event is None:
            self._original_pos = self.widget.pos
        else:
            self._event.cancel()
        self._amplitude = amplitude if amplitude is not None else BASE_AMPLITUDE_PX
        self._duration = duration if duration is not None else BASE_DURATION_S
        self._elapsed = 0.0
        self._event = Clock.schedule_interval(self._update, 1.0 / 60.0)

    def _update(self, dt):
        self._elapsed += dt
        dx, dy = shake_offset(self._elapsed, self._duration, self._amplitude,
                               random.uniform(-1.0, 1.0), random.uniform(-1.0, 1.0))
        if self._elapsed >= self._duration:
            self._apply(0.0, 0.0)
            self._event.cancel()
            self._event = None
            return
        self._apply(dx, dy)
