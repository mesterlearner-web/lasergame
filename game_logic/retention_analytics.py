"""
game_logic/retention_analytics.py  (فاز ۷)

طبق فایل مرجع بخش ۵.۲۰: «RetentionAnalytics: get_d3_retention،
get_d14_retention، get_d30_retention باید دقیقاً به الگوی
get_d1_retention/get_d7_retention (فقط با timedelta متفاوت) اضافه
بشن.»

⚠️ پیاده‌سازی اصلی get_d1_retention/get_d7_retention («بخش۷» پرامپت
خام) در دسترس نیست -- فقط این‌که ۳ متد باقی‌مانده باید *همون الگو* رو
دنبال کنن. چون این پروژه بک‌اند/سرور چندکاربره نداره (بازی محلی
تک‌کاربره‌ست)، «نگه‌داشت» اینجا به معنای معمول صنعت (چند درصد از کل
نصب‌کننده‌ها روز N برگشتن) نیست -- به معنای «آیا *همین* بازیکن دقیقاً
N روز بعد از اولین جلسه‌اش هم بازی رو باز کرده؟» تعریف شده؛ هر ۵ متد
از همون یک الگوی پایه (_was_active_on_day_n) با timedelta متفاوت
می‌سازن -- دقیقاً همون تکرار الگویی که فایل مرجع می‌خواد.
"""
from datetime import date, timedelta


class RetentionAnalytics:
    def __init__(self, first_session_date=None, session_dates=None):
        self.first_session_date = first_session_date  # رشته‌ی ISO یا None
        self.session_dates = session_dates if session_dates is not None else []

    def record_session(self, today=None):
        """باید یک‌بار در شروع هر اجرای اپ صدا زده بشه (طبق فاز۴/۵:
        همون‌جایی که SaveManager.load صدا زده می‌شه). برمی‌گردونه: True
        اگه امروز *اولین* جلسه بود (برای این‌که فراخوان -- مثلاً
        MissionManager.report_event('session_started') -- بتونه فرق
        «اولین بازِ امروز» رو از «دوباره باز کردن همون روز» تشخیص بده؛
        وگرنه ماموریت‌های «N روز مختلف» با باز-و-بسته‌کردن مکرر همون
        یک روز به‌اشتباه پیش می‌رفتن)."""
        today = today or date.today()
        today_str = today.isoformat()
        if self.first_session_date is None:
            self.first_session_date = today_str
        if today_str not in self.session_dates:
            self.session_dates.append(today_str)
            self.session_dates.sort()
            return True
        return False

    def _was_active_on_day_n(self, n):
        """الگوی پایه‌ای که هر ۵ متد get_dN_retention زیر ازش می‌سازن."""
        if self.first_session_date is None:
            return False
        first = date.fromisoformat(self.first_session_date)
        target_date = first + timedelta(days=n)
        return target_date.isoformat() in self.session_dates

    def get_d1_retention(self):
        return self._was_active_on_day_n(1)

    def get_d3_retention(self):
        return self._was_active_on_day_n(3)

    def get_d7_retention(self):
        return self._was_active_on_day_n(7)

    def get_d14_retention(self):
        return self._was_active_on_day_n(14)

    def get_d30_retention(self):
        return self._was_active_on_day_n(30)

    def get_current_session_count(self):
        return len(self.session_dates)

    def to_dict(self):
        return {'first_session_date': self.first_session_date, 'session_dates': list(self.session_dates)}

    @classmethod
    def from_dict(cls, data):
        return cls(first_session_date=data.get('first_session_date'),
                    session_dates=list(data.get('session_dates', [])))
