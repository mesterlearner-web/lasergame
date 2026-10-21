"""
utils/pool.py -- Object Pooling عمومی

استفاده‌ی مجدد از اشیاء به‌جای ساخت مکرر، برای جلوگیری از GC Pause
(طبق فلسفه‌ی بهینه‌سازی فایل مرجع، بخش ۵.۱). این نسخه عمومی است و
هم برای LaserBeam (BeamPool) و هم بعداً برای Particle استفاده می‌شود.
"""


class ObjectPool:
    """مدیریت استفاده‌ی مجدد از اشیاء."""

    def __init__(self, factory, reset_func, initial_size=10, max_size=100):
        self.factory = factory
        self.reset_func = reset_func
        self.max_size = max_size
        self.pool = []
        self.active = []

        for _ in range(initial_size):
            self.pool.append(self.factory())

    def acquire(self):
        """گرفتن یک شیء از استخر (یا ساخت یکی جدید اگر استخر خالی باشد)."""
        if self.pool:
            obj = self.pool.pop()
        else:
            obj = self.factory()
        self.active.append(obj)
        return obj

    def release(self, obj):
        """بازگرداندن شیء به استخر."""
        if obj in self.active:
            self.active.remove(obj)
        if len(self.pool) < self.max_size:
            self.reset_func(obj)
            self.pool.append(obj)

    def release_all(self):
        for obj in list(self.active):
            self.release(obj)
