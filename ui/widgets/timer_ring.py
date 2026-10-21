"""
ui/widgets/timer_ring.py  (فاز ۶)

طبق فایل مرجع بخش ۵.۷: «TimerRing: منطق رنگ‌بندی بخش۲ (update_progress
که واقعاً progress رو محاسبه می‌کنه) + پرداخت بصری بخش۵ انتخاب شد --
نسخه‌ی بخش۶ (update_time که کاری نمی‌کرد) کاملاً کنار گذاشته می‌شه.»

یعنی این ویجت باید یک متد update_progress(fraction, tier) داشته باشه
که *واقعاً* هندسه/رنگ رو دوباره می‌کشه -- نه یک متد بی‌اثر. رنگ حلقه
از ColorPalette.get_timer_ring_color می‌آد (فاز۶، حساس به رنگ‌کوری).
"""
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line

from core.color_palette import ColorPalette

RING_WIDTH = 6
BG_ALPHA = 0.35
#: از کجا شروع بشه (۹۰=بالا) و در کدوم جهت -- طبق قرارداد Kivy، زاویه
#: مثبت پادساعت‌گرده؛ برای حس «تخلیه‌شدن ساعت‌گرد» علامت را منفی می‌کنیم.
START_ANGLE_DEG = 90


class TimerRing(Widget):
    def __init__(self, palette=None, **kwargs):
        super().__init__(**kwargs)
        self.palette = palette or ColorPalette()
        self.progress = 1.0
        self.tier = 'legendary'

        with self.canvas:
            Color(0.3, 0.3, 0.35, BG_ALPHA)
            self._bg_line = Line(width=RING_WIDTH)
            self._fg_color = Color(*self.palette.get_timer_ring_color(self.tier))
            self._fg_line = Line(width=RING_WIDTH, cap='round')

        self.bind(pos=self._redraw, size=self._redraw)
        self._redraw()

    def set_palette(self, palette):
        """وقتی بازیکن حالت رنگ‌کوری رو در SettingsScreen عوض می‌کنه."""
        self.palette = palette
        self._fg_color.rgba = self.palette.get_timer_ring_color(self.tier)

    def update_progress(self, fraction, tier):
        """طبق بخش۵.۷ -- این متد *واقعاً* progress رو اعمال می‌کنه."""
        self.progress = max(0.0, min(1.0, fraction))
        self.tier = tier
        self._fg_color.rgba = self.palette.get_timer_ring_color(tier)
        self._redraw()

    def _redraw(self, *args):
        cx, cy = self.center_x, self.center_y
        radius = max(0.0, min(self.width, self.height) / 2.0 - RING_WIDTH)
        if radius <= 0:
            self._bg_line.circle = (cx, cy, 0)
            self._fg_line.circle = (cx, cy, 0)
            return
        self._bg_line.circle = (cx, cy, radius, 0, 360)
        sweep = 360.0 * self.progress
        if sweep <= 0.0:
            self._fg_line.circle = (cx, cy, radius, START_ANGLE_DEG, START_ANGLE_DEG)
        else:
            # ساعت‌گرد: زاویه‌ی پایانی از شروع کم می‌شه (نه اضافه)
            self._fg_line.circle = (cx, cy, radius, START_ANGLE_DEG - sweep, START_ANGLE_DEG)
