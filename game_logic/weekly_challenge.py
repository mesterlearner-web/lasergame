"""
game_logic/weekly_challenge.py  (فاز ۷)

طبق فایل مرجع بخش ۵.۱۵: «منطق WeeklyChallenge بخش۷ می‌مونه، با این رفع
باگ: تا زمانی که یک بک‌اند واقعی برای جدول امتیازات جهانی نداریم،
self.rank قابل‌محاسبه نیست -- پس فعلاً فقط پاداش participation پرداخت
می‌شه (بدون رتبه‌بندی)، و claim_rewards این حالت رو به‌جای خطا دادن،
به‌صورت پیش‌فرض مدیریت می‌کنه.»

یعنی: rank همیشه None است (نه این‌که سعی کنه محاسبه کنه و خطا بده)،
و claim_rewards هیچ‌وقت روی نبود rank گیر نمی‌کنه -- همیشه فقط
پاداش شرکت (participation) می‌ده. وقتی یک بک‌اند واقعی اضافه شد،
rank/rank-based rewards می‌تونن جداگانه روش اضافه بشن، بدون این‌که
مسیر participation-only خراب بشه.
"""
from datetime import date

PARTICIPATION_REWARD = {'coins': 100, 'gems': 2}
DEFAULT_TARGET = 500


def _week_key(today):
    iso_year, iso_week, _ = today.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


class WeeklyChallenge:
    def __init__(self, progress=0, target=DEFAULT_TARGET, claimed=False, week_key=None):
        self.progress = progress
        self.target = target
        self.claimed = claimed
        self.week_key = week_key

    @property
    def rank(self):
        """طبق تصمیم صریح بخش۵.۱۵ -- تا وقتی بک‌اند واقعی جدول
        امتیازات جهانی نداریم، این همیشه None است، نه یک محاسبه‌ی
        شکست‌خورده."""
        return None

    @property
    def is_complete(self):
        return self.progress >= self.target

    @property
    def progress_fraction(self):
        return min(1.0, self.progress / self.target) if self.target > 0 else 1.0

    def add_progress(self, amount):
        if not self.claimed:
            self.progress += amount

    def claim_rewards(self):
        """طبق بخش۵.۱۵ -- بدون rank، فقط پاداش participation پرداخت
        می‌شه؛ این رفتار پیش‌فرضه، نه یک حالت استثنایی fallback."""
        if self.claimed:
            raise ValueError("پاداش این چالش قبلاً دریافت شده.")
        if not self.is_complete:
            raise ValueError("چالش هفتگی هنوز کامل نشده.")
        self.claimed = True
        return dict(PARTICIPATION_REWARD)

    def maybe_reset(self, today=None):
        today = today or date.today()
        key = _week_key(today)
        if self.week_key != key:
            self.progress = 0
            self.claimed = False
            self.week_key = key
            return True
        return False

    def to_dict(self):
        return {
            'progress': self.progress, 'target': self.target,
            'claimed': self.claimed, 'week_key': self.week_key,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            progress=data.get('progress', 0), target=data.get('target', DEFAULT_TARGET),
            claimed=data.get('claimed', False), week_key=data.get('week_key'),
        )
