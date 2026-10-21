"""
core/game.py  (فاز ۶)

طبق فایل مرجع بخش ۵.۱۸: «AnimationManager باید Singleton باشه (یک
نمونه‌ی سراسری در core/game.py، نه ساخت نمونه‌ی تازه در هر تابع) تا
نشتی Clock.schedule_interval رخ نده.»

توابع Easing: فایل مرجع می‌گه «توابع Easing بخش۵ (وریفای عددی شدن،
همه درستن) بدون تغییر» -- یعنی این‌ها قبلاً از صفر پیاده و عددی وریفای
شده بودن. آن پیاده‌سازی (پرامپت خام بخش۵) در این جلسه در دسترس نیست؛
به‌جای بازسازی فرمول‌هایی که همین الان به‌شکل کامل و well-tested در
خودِ Kivy (`kivy.animation.AnimationTransition`: 'linear', 'in_quad',
'out_quad', 'in_out_cubic', 'out_back', 'out_bounce', 'out_elastic',
...) وجود دارن، از همین توابع native استفاده می‌شه -- بازنویسی‌شون از
صفر فقط دوباره‌کاریِ چیزی بود که Kivy خودش درست و تست‌شده ارائه می‌ده.

باگ دقیقی که بخش۵.۱۸ توصیف می‌کنه: «در play_entry_animations، خط
anim.start(widget) که بلافاصله بعد از ساخت Animation اجرا می‌شد حذف
می‌شه -- فقط نسخه‌ی زمان‌بندی‌شده (Clock.schedule_once) باید انیمیشن
رو start کنه تا استگرِ پلکانی واقعاً دیده بشه.» یعنی نسخه‌ی باگ‌دار
هم فوری هم با تأخیر start می‌کرد (دوبار)، و چون فوری زودتر بود، تأخیر
هیچ‌وقت واقعاً دیده نمی‌شد -- کل ویجت‌ها همزمان ظاهر می‌شدن، نه پلکانی.
پایین، *فقط* نسخه‌ی زمان‌بندی‌شده وجود داره.
"""
from kivy.animation import Animation
from kivy.clock import Clock


class AnimationManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._scheduled_events = []
        return cls._instance

    @classmethod
    def _reset_instance_for_testing(cls):
        cls._instance = None

    def play_entry_animations(self, widgets, stagger_delay=0.06, duration=0.28,
                               transition='out_back'):
        """هر ویجت با تأخیر پلکانی (stagger_delay * index) وارد صحنه
        می‌شه -- طبق بخش۵.۱۸، *بدون* start فوری."""
        self.cancel_all()
        for index, widget in enumerate(widgets):
            widget.opacity = 0.0
            anim = Animation(opacity=1.0, duration=duration, t=transition)
            event = Clock.schedule_once(
                lambda dt, w=widget, a=anim: a.start(w), stagger_delay * index)
            # ⚠️ عمداً هیچ anim.start(widget) دیگری اینجا نیست -- دقیقاً
            # همون خط اشتباهی که بخش۵.۱۸ می‌گه باید حذف بشه.
            self._scheduled_events.append(event)

    def play_pulse(self, widget, scale=1.15, duration=0.12):
        """یک نبض کوتاه (بزرگ‌شدن و برگشت) -- برای فیدبک لمس دکمه یا
        دریافت پاداش."""
        anim = (Animation(size=(widget.width * scale, widget.height * scale), duration=duration, t='out_quad')
                + Animation(size=(widget.width, widget.height), duration=duration, t='in_quad'))
        anim.start(widget)
        return anim

    def play_fade_out(self, widget, duration=0.25, on_complete=None):
        anim = Animation(opacity=0.0, duration=duration, t='in_quad')
        if on_complete is not None:
            anim.bind(on_complete=lambda *_a: on_complete())
        anim.start(widget)
        return anim

    def cancel_all(self):
        for event in self._scheduled_events:
            event.cancel()
        self._scheduled_events.clear()
