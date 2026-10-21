"""
game_logic/daily_rewards.py  (فاز ۷)

طبق فایل مرجع بخش ۵.۱۴: «DailyRewardsManager، با پاداش استریک تا ۱۰۰
روز.»

⚠️ جدول دقیق پاداش هر روز («بخش۷» پرامپت خام) در دسترس نیست. طبق
همون الگوی فرمولی که Battle Pass (فاز۴، بخش۵.۱۲) استفاده کرد -- به‌جای
یک دیکشنری دستی ۱۰۰تایی -- یک فرمول صعودی با جهش هفتگی (هر ۷ روز
جواهر اضافه) و یک پاداش ویژه در نقطه‌ی پایانی (روز۱۰۰) طراحی شد.
"""
from datetime import date

MAX_STREAK_DAYS = 100


def reward_for_streak_day(day):
    """day: ۱..۱۰۰ (خارج از بازه‌ها clamp می‌شن). سکه به‌آرامی صعودی؛
    هر ۷ روز (هفتگی) یک جواهر اضافه؛ روز۱۰۰ یک پاداش ویژه‌ی بزرگ‌تر."""
    day = max(1, min(MAX_STREAK_DAYS, day))
    reward = {'coins': 10 + day * 2}
    if day % 7 == 0:
        reward['gems'] = 1
    if day == MAX_STREAK_DAYS:
        reward['gems'] = reward.get('gems', 0) + 10
        reward['special_items'] = ['skin_streak_master']
    return reward


class DailyRewardsManager:
    def __init__(self, current_streak=0, longest_streak=0, last_claim_date=None):
        self.current_streak = current_streak
        self.longest_streak = longest_streak
        self.last_claim_date = last_claim_date  # رشته‌ی ISO یا None

    def can_claim_today(self, today=None):
        today = today or date.today()
        return self.last_claim_date != today.isoformat()

    def preview_next_reward(self, today=None):
        """پاداشی که *اگه* همین امروز claim بشه گرفته می‌شه -- برای
        نمایش در UI پیش از کلیک."""
        today = today or date.today()
        next_day = self._streak_if_claimed_now(today)
        return reward_for_streak_day(next_day)

    def _streak_if_claimed_now(self, today):
        if self.last_claim_date is None:
            return 1
        last = date.fromisoformat(self.last_claim_date)
        gap_days = (today - last).days
        if gap_days == 1:
            return min(MAX_STREAK_DAYS, self.current_streak + 1)
        if gap_days == 0:
            return self.current_streak  # امروز قبلاً claim شده (can_claim_today جلوش رو می‌گیره)
        return 1  # یک یا چند روز از دست رفته -- استریک از نو شروع می‌شه

    def claim(self, today=None):
        today = today or date.today()
        if not self.can_claim_today(today):
            raise ValueError("جایزه‌ی امروز قبلاً دریافت شده.")
        self.current_streak = self._streak_if_claimed_now(today)
        self.longest_streak = max(self.longest_streak, self.current_streak)
        self.last_claim_date = today.isoformat()
        return reward_for_streak_day(self.current_streak)

    def to_dict(self):
        return {
            'current_streak': self.current_streak,
            'longest_streak': self.longest_streak,
            'last_claim_date': self.last_claim_date,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            current_streak=data.get('current_streak', 0),
            longest_streak=data.get('longest_streak', 0),
            last_claim_date=data.get('last_claim_date'),
        )
