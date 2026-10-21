"""
utils/timer.py -- تایمر دقیق مرحله

طبق اصلاح فایل مرجع (بخش ۵.۸): آستانه‌های هشدار/بحران و پاداش زمانی
باید نسبت به duration خودِ تایمر (درصدی) محاسبه بشن، نه عدد مطلق
ثانیه -- چون duration بین فازهای مختلف از ۳۰۰ به ۱۶۰ ثانیه کم می‌شه.
"""


class PreciseTimer:
    """تایمر شمارش معکوس با dt واقعی بازی (نه زمان سیستم) -- طوری که
    Pause/Resume و Hit Stop به‌سادگی روش اثر بگذارن."""

    def __init__(self, duration, on_complete=None):
        self.duration = duration
        self.elapsed = 0.0
        self.is_running = False
        self.is_paused = False
        self.on_complete = on_complete
        self._completed_fired = False

    def start(self):
        self.is_running = True
        self.is_paused = False
        self.elapsed = 0.0
        self._completed_fired = False

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def reset(self):
        self.elapsed = 0.0
        self.is_running = False
        self.is_paused = False
        self._completed_fired = False

    def update(self, dt):
        if not self.is_running or self.is_paused:
            return
        self.elapsed += dt
        if self.elapsed >= self.duration and not self._completed_fired:
            self.elapsed = self.duration
            self.is_running = False
            self._completed_fired = True
            if self.on_complete:
                self.on_complete()

    @property
    def remaining(self):
        return max(0.0, self.duration - self.elapsed)

    @property
    def progress(self):
        """۰ در شروع، ۱ در پایان -- برای پرکردن TimerRing استفاده می‌شود."""
        return min(1.0, self.elapsed / self.duration) if self.duration > 0 else 1.0

    @property
    def remaining_fraction(self):
        """۱ در شروع، ۰ در پایان -- طبق تصمیم فایل مرجع بخش ۵.۸، پایه‌ی
        آستانه‌های درصدی (پیام تشویقی، جواهر، ستاره) از همین مقدار است،
        نه ثانیه‌ی مطلق."""
        return 1.0 - self.progress

    def get_display_time(self):
        remaining = int(self.remaining)
        minutes, seconds = remaining // 60, remaining % 60
        return f"{minutes:02d}:{seconds:02d}"


def performance_tier(remaining_fraction):
    """آستانه‌ی درصدی مشترک برای پیام تشویقی/جواهر/ستاره -- طبق فایل
    مرجع بخش ۵.۸ (جایگزین آستانه‌های مطلق ثانیه‌ای سند اولیه)."""
    if remaining_fraction > 0.60:
        return 'legendary'
    elif remaining_fraction > 0.40:
        return 'excellent'
    elif remaining_fraction > 0.20:
        return 'great'
    elif remaining_fraction > 0.10:
        return 'good'
    return 'close'
