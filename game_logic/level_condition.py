"""
game_logic/level_condition.py

بررسی شرط پیروزی/شکست یک مرحله: هر ۳ هدف باید نابود بشن قبل از
اتمام زمان. طبق تصمیم فایل مرجع بخش ۵.۸، پیام تشویقی/پاداش سریع
بر اساس remaining_fraction (نسبت به duration خودِ مرحله) تعیین
می‌شه، نه ثانیه‌ی مطلق.
"""
from utils.timer import performance_tier


class LevelCondition:
    def __init__(self, total_targets=3):
        self.total_targets = total_targets
        self.targets_destroyed = 0
        self.shots_used = 0

    def on_target_destroyed(self):
        self.targets_destroyed += 1

    def on_shot_fired(self):
        self.shots_used += 1

    def is_success(self):
        return self.targets_destroyed >= self.total_targets

    def is_failure(self, timer):
        return (not self.is_success()) and timer.remaining <= 0.0

    def get_result(self, timer):
        if self.is_success():
            is_perfect = self.shots_used <= self.total_targets
            return {
                'success': True,
                'time_remaining': timer.remaining,
                'remaining_fraction': timer.remaining_fraction,
                'shots_used': self.shots_used,
                'is_perfect': is_perfect,
                'tier': performance_tier(timer.remaining_fraction),
            }
        return {
            'success': False,
            'targets_destroyed': self.targets_destroyed,
            'targets_remaining': self.total_targets - self.targets_destroyed,
            'shots_used': self.shots_used,
        }


#: تبدیل تایر -> تعداد ستاره. طبق فایل مرجع بخش ۵.۱۹: «ستاره‌دهی
#: _calculate_stars طبق فرمول درصدی بند ۵.۸ بالا (نه آستانه‌ی مطلق)»
#: -- یعنی باید مستقیماً از همون تایرهای performance_tier (که خودش
#: بر پایه‌ی remaining_fraction درصدیه) مشتق بشه، نه یک آستانه‌ی
#: ثانیه‌ی جدا و جداگانه.
_STAR_BY_TIER = {
    'legendary': 3,
    'excellent': 3,
    'great': 2,
    'good': 2,
    'close': 1,
}


def calculate_stars(result):
    """result همون دیکشنریه که LevelCondition.get_result() برمی‌گردونه.
    ۰ ستاره برای باخت؛ در غیر این صورت مستقیماً از روی tier."""
    if not result.get('success'):
        return 0
    return _STAR_BY_TIER.get(result.get('tier'), 1)
