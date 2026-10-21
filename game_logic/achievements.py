"""
game_logic/achievements.py  (فاز ۹)

طبق فایل مرجع بخش ۶ (دفترچه‌ی باگ‌ها): «سه کلید streak_25 و endless_10 و endless_25 در
AchievementManager.ACHIEVEMENTS جا افتاده بود و باید اضافه شود؛ EndlessMode.on_level_complete باید
achievement_manager را صدا بزند.» -- فهرست کامل دستاوردهای پرامپت خام در دسترس نیست، پس فقط همین سه
کلید + یکی که خودِ فاز۹ لازم داشت (`daily_challenge_7`، تصمیم من) ساخته شد. پاداش‌ها (جواهر) هم تصمیم
خودم است چون فایل مرجع عددی نمی‌دهد: ۵، ۲، ۵، ۳ (جواهر ارز نادر است؛ ≈۱ جواهر به‌ازای ۱۰ مرحله).

منطق خالص (بدون Kivy)، مثل بقیه‌ی مدیرها: to_dict/from_dict برای ذخیره‌سازی، اقتصاد به‌صورت پارامتر
اختیاری تزریق می‌شود (جلوگیری از وابستگی مدیرها به هم).
"""

ACHIEVEMENTS = {
    'streak_25': {'title': 'استریک ۲۵ روزه',
                  'description': '۲۵ روز پشت‌سرهم جایزه‌ی روزانه را دریافت کن.', 'reward_gems': 5},
    'endless_10': {'title': 'ده مرحله بی‌وقفه',
                   'description': 'در حالت بی‌نهایت به مرحله‌ی ۱۰ برس.', 'reward_gems': 2},
    'endless_25': {'title': 'بیست‌وپنج مرحله بی‌وقفه',
                   'description': 'در حالت بی‌نهایت به مرحله‌ی ۲۵ برس.', 'reward_gems': 5},
    'daily_challenge_7': {'title': 'هفته‌ی چالش',
                          'description': '۷ روز پشت‌سرهم چالش روزانه را کامل کن.', 'reward_gems': 3},
}

#: (آستانه، کلید) -- هر مقدار برابر یا بیشتر از آستانه دستاورد را باز می‌کند.
STREAK_THRESHOLDS = ((25, 'streak_25'),)
ENDLESS_THRESHOLDS = ((10, 'endless_10'), (25, 'endless_25'))
DAILY_CHALLENGE_THRESHOLDS = ((7, 'daily_challenge_7'),)


class AchievementManager:
    ACHIEVEMENTS = ACHIEVEMENTS

    def __init__(self, unlocked=None):
        self.unlocked = set(unlocked or ())

    def is_unlocked(self, key):
        return key in self.unlocked

    def unlock(self, key, economy=None):
        """دستاورد را باز می‌کند. دیکشنری {'key','title','reward_gems'} برمی‌گرداند اگر *همین الان* باز
        شد، None اگر از قبل باز بود. کلید ناشناخته ValueError (خطای برنامه‌نویسی است). اگر economy داده شود،
        جواهر همان‌جا اعمال می‌شود."""
        if key not in self.ACHIEVEMENTS:
            raise ValueError(f"دستاورد ناشناخته: {key!r}")
        if key in self.unlocked:
            return None
        self.unlocked.add(key)
        info = self.ACHIEVEMENTS[key]
        if economy is not None and info['reward_gems']:
            economy.add_gems(info['reward_gems'])
        return {'key': key, 'title': info['title'], 'reward_gems': info['reward_gems']}

    def _check(self, value, thresholds, economy):
        newly = []
        for threshold, key in thresholds:
            if value >= threshold:
                result = self.unlock(key, economy)
                if result is not None:
                    newly.append(result)
        return newly

    def check_streak(self, streak_days, economy=None):
        return self._check(streak_days, STREAK_THRESHOLDS, economy)

    def check_endless(self, stage_reached, economy=None):
        return self._check(stage_reached, ENDLESS_THRESHOLDS, economy)

    def check_daily_challenge(self, streak_days, economy=None):
        return self._check(streak_days, DAILY_CHALLENGE_THRESHOLDS, economy)

    def summary(self):
        """برای نمایش در UI: همه‌ی دستاوردها با وضعیت باز/بسته، به ترتیب تعریف."""
        return [dict(info, key=key, unlocked=key in self.unlocked) for key, info in self.ACHIEVEMENTS.items()]

    def to_dict(self):
        return {'unlocked': sorted(self.unlocked)}

    @classmethod
    def from_dict(cls, data):
        # کلید ناشناخته (نسخه‌ی قدیمی/جدیدتر ذخیره) بی‌صدا نادیده گرفته می‌شود؛ ذخیره‌ی خراب نباید بازی را بشکند.
        return cls(k for k in (data or {}).get('unlocked', []) if k in ACHIEVEMENTS)
