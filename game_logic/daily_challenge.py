"""
game_logic/daily_challenge.py  (فاز ۹)

«چالش روزانه»: هر روز تقویمی یک مرحله‌ی رویه‌ای، که از روی *تاریخ* ساخته می‌شود (همه‌ی بازیکن‌ها در یک
روز مرحله‌ی یکسان می‌گیرند، بدون هیچ بک‌اند). فایل مرجع جزئیات را نمی‌دهد؛ تصمیم‌های من:

* سختی با روز هفته می‌رود: دوشنبه ≈ مرحله‌ی ۲۰ کمپین ... یکشنبه ≈ ۶۴ (WEEKDAY_LEVELS)، پس همه‌ی مکانیک‌ها
  به‌تدریج در هفته دیده می‌شوند. معرفی‌اجباری خاموش است.
* زمان: max(90, 200 − 2·سطح) ثانیه.
* پاداش اولین موفقیتِ هر روز: 50 + 10·min(استریک،10) سکه و ۱ جواهر هر ۷ روز استریک. دوباره‌بازی‌کردن آزاد
  است ولی پاداش ندارد. شکست آزاد است (دوباره امتحان کن).
* استریک = روزهای متوالیِ تکمیل‌شده؛ یک روز جاافتاده آن را به ۱ برمی‌گرداند.
* ضدتقلب ساده: فقط تاریخ *بعد از* آخرین تکمیل پاداش می‌دهد -- عقب‌بردن ساعت گوشی نمی‌تواند پاداش
  همان روز را دوباره بدهد. (جلو‌بردن ساعت هنوز روزی یک‌بار می‌دهد؛ مثل EnergyManager، بدون بک‌اند
  راه‌حل کامل ندارد.)
"""
from datetime import date, timedelta

from game_logic.level import Level
from game_logic.level_generator import generate_level

#: دوشنبه (۰) تا یکشنبه (۶): مرحله‌ی کمپین معادل برای سختی.
WEEKDAY_LEVELS = (20, 24, 28, 34, 42, 52, 64)


def date_seed(day):
    return int(day.strftime('%Y%m%d')) * 31 + 7


def equivalent_level_for(day):
    return WEEKDAY_LEVELS[day.weekday()]


def time_limit_for(level):
    return max(90, 200 - 2 * level)


def reward_for(streak):
    return {'coins': 50 + 10 * min(int(streak), 10), 'gems': 1 if streak and streak % 7 == 0 else 0, 'xp': 0}


def _safe_int(value, default=0):
    """مقدار خراب در دیتابیس (رشته‌ی نامعتبر، None، منفی) نباید بارگذاری کل ذخیره را بشکند."""
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _to_date(value):
    return value if isinstance(value, date) else date.fromisoformat(value)


class DailyChallenge:
    def __init__(self, last_completed=None, streak=0, best_streak=0, total_completed=0):
        self.last_completed = last_completed        # رشته‌ی ISO یا None
        self.streak = streak
        self.best_streak = best_streak
        self.total_completed = total_completed

    @staticmethod
    def _today(today):
        return _to_date(today) if today is not None else date.today()

    def build_level(self, today=None):
        day = self._today(today)
        eq = equivalent_level_for(day)
        data = generate_level(eq, seed=date_seed(day), equivalent_level=eq,
                              rewards={'coins': 0, 'gems': 0, 'xp': 0})
        data['time_limit'] = time_limit_for(eq)
        return Level(data)

    def is_completed(self, today=None):
        return self.last_completed == self._today(today).isoformat()

    def can_claim(self, today=None):
        """فقط تاریخِ *بعد از* آخرین تکمیل (عقب‌بردن ساعت پاداش دوباره نمی‌دهد)."""
        return self.last_completed is None or self._today(today) > _to_date(self.last_completed)

    def display_streak(self, today=None):
        """استریک قابل‌نمایش: فقط اگر دیروز یا امروز تکمیل شده، وگرنه ۰ (رشته پاره شده)."""
        if self.last_completed is None:
            return 0
        day = self._today(today)
        last = _to_date(self.last_completed)
        return self.streak if last in (day, day - timedelta(days=1)) else 0

    def complete(self, today=None, economy=None, achievement_manager=None):
        """موفقیت چالش امروز. دیکشنری پاداش، یا None اگر پاداشی نیست (امروز قبلاً گرفته یا ساعت عقب رفته)."""
        day = self._today(today)
        if not self.can_claim(day):
            return None
        yesterday = (day - timedelta(days=1)).isoformat()
        self.streak = self.streak + 1 if self.last_completed == yesterday else 1
        self.best_streak = max(self.best_streak, self.streak)
        self.total_completed += 1
        self.last_completed = day.isoformat()
        reward = reward_for(self.streak)
        if economy is not None:
            economy.apply_level_rewards(reward)
        achievements = achievement_manager.check_daily_challenge(self.streak, economy) if achievement_manager else []
        return dict(reward, streak=self.streak, achievements=achievements)

    def to_dict(self):
        return {'last_completed': self.last_completed, 'streak': self.streak,
                'best_streak': self.best_streak, 'total_completed': self.total_completed}

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        last = data.get('last_completed')
        try:
            if last is not None:
                date.fromisoformat(last)
        except (TypeError, ValueError):
            last = None             # تاریخ خراب -> نادیده؛ ذخیره‌ی خراب بازی را نمی‌شکند
        return cls(last_completed=last, streak=_safe_int(data.get('streak')),
                   best_streak=_safe_int(data.get('best_streak')), total_completed=_safe_int(data.get('total_completed')))
