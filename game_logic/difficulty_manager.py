"""
game_logic/difficulty_manager.py  (فاز ۳)

مدیریت منحنی سختی ۵ فاز کل بازی -- طبق فایل مرجع بخش ۵.۸ ("منحنی
سختی، ۵ فاز، DifficultyManager بدون تغییر از بخش۳") و نقشه‌راه بخش۸
(کل بازی ۱۰۰ مرحله: ۱ تا ۵ دستی در همین فاز، ۶ تا ۱۰۰ رویه‌ای در فاز۹).

⚠️ نکته‌ی مستندسازی مهم (باید در PROGRESS.md هم ثبت شود):
فایل مرجع می‌گوید این کلاس «بدون تغییر از بخش۳» است -- یعنی قبلاً در
یکی از ۸ پرامپت خام اصلی (بخش۳، نه خودِ فایل مرجع) به‌طور کامل طراحی
شده بود. آن متن خام در این جلسه در دسترس نیست؛ فقط فایل مرجعِ
تصمیم‌گیری‌شده در دسترس است، که تنها دو منبع مشخص برای این کلاس
می‌دهد: (۱) جدول سطح معرفی مکانیک‌ها (بخش ۵.۵ -- دقیقاً و کامل استفاده
شده)، (۲) نیاز به ۵ فاز روی کل ۱۰۰ مرحله (بخش۸). بازه‌های هر فاز و
فرمول سختی/زمان زیر از همین دو منبع، با این اصل بازسازی شدند: هر ۷
مکانیکی که در بخش۵.۵ معرفی می‌شوند (۱۶، ۲۰، ۲۲، ۳۳، ۳۸، ۴۳) باید همگی
داخل مرز فاز مربوط به خودشان بیفتند، نه لب مرز دو فاز. اگر بعداً متن
اصلی بخش۳ در دسترس قرار گرفت، این بازه‌ها/فرمول باید با آن تطبیق داده
شوند.

فرمول سختی/زمان عمداً «ease-in» (توان ۱.۵) انتخاب شد، نه خطی: شروع
بسیار ملایم (سازگار با اینکه سطوح ۱ تا ۵ دستی، طبق خودِ این فرمول،
عملاً همان بازه‌ی زمانی ۳۰۰ ثانیه‌ی سطوح ۱/۲ را توصیه می‌کنند) و شیب
تندتر رو به پایان بازی -- الگوی رایج طراحی سختی در بازی‌های پازل موبایل.
"""

# طبق فایل مرجع بخش ۵.۵ -- جدول سطح معرفی نهایی مکانیک‌ها (دقیقاً کپی).
# 'normal' از سطح ۱ همیشه در دسترس است (خط پایه، نه یک "قفل" جداگانه).
MECHANIC_UNLOCK_LEVEL = {
    'normal': 1,
    'semi_mirror': 16,
    'rotating_mirror': 20,
    'prism': 22,
    'portal': 33,
    'black_hole': 38,
    'broken_mirror': 43,
}

#: نام‌های نمایشی فارسی مکانیک‌ها -- برای پیام‌های UI (فاز۵) و HUD فعلی.
MECHANIC_NAME_FA = {
    'normal': 'آینه‌ی عادی',
    'semi_mirror': 'آینه‌ی نیمه‌شفاف',
    'rotating_mirror': 'آینه‌ی چرخان',
    'prism': 'منشور',
    'portal': 'پورتال',
    'black_hole': 'سیاه‌چاله',
    'broken_mirror': 'آینه‌ی شکسته',
}

TOTAL_LEVELS = 100  # طبق نقشه‌راه فایل مرجع، بخش۸ (مراحل ۱ تا ۱۰۰)

# ۵ فاز روی کل ۱۰۰ مرحله -- بازه‌ها طوری انتخاب شدند که هر مکانیک جدید
# (بخش ۵.۵) کاملاً داخل فاز مربوطه‌اش بیفتد، نه لب مرز.
PHASES = (
    {'index': 1, 'key': 'training', 'name_fa': 'آموزش',
     'level_start': 1, 'level_end': 15},
    {'index': 2, 'key': 'intermediate', 'name_fa': 'میانی',
     'level_start': 16, 'level_end': 32},
    {'index': 3, 'key': 'advanced', 'name_fa': 'پیشرفته',
     'level_start': 33, 'level_end': 50},
    {'index': 4, 'key': 'expert', 'name_fa': 'خبره',
     'level_start': 51, 'level_end': 75},
    {'index': 5, 'key': 'master', 'name_fa': 'استاد',
     'level_start': 76, 'level_end': 100},
)

# طبق فایل مرجع بخش ۵.۹ -- سطوح ۳ هدفی به‌عنوان الگوی معمول در نظر
# گرفته شده‌اند؛ این بازه‌ها راهنمای طراح مرحله (دستی یا رویه‌ای فاز۹)
# هستند، نه یک قانون سخت‌گیرانه -- دقیقاً مثل بقیه‌ی خروجی‌های این کلاس.
_TARGET_COUNT_RANGE_BY_PHASE = {
    'training': (1, 2),
    'intermediate': (1, 3),
    'advanced': (2, 3),
    'expert': (2, 4),
    'master': (3, 4),
}

_MIN_TIME_LIMIT = 60.0   # کف زمانی -- حتی سخت‌ترین مرحله نباید غیرمنصفانه کوتاه باشد
_MAX_TIME_LIMIT = 300.0  # زمان سطح ۱ -- طبق level_001/002 (فاز۲) که همین عدد را دارند
_MIN_DIFFICULTY = 1.0
_MAX_DIFFICULTY = 10.0


def _clamp_level_id(level_id):
    """سطح‌های خارج از بازه‌ی ۱..۱۰۰ (که فعلاً نباید پیش بیاید ولی محض
    ایمنی) را به نزدیک‌ترین انتهای بازه می‌چسباند، به‌جای کرش کردن."""
    return max(1, min(TOTAL_LEVELS, level_id))


def _eased_progress(level_id):
    """۰.۰ در سطح ۱، ۱.۰ در سطح ۱۰۰ -- با شیب ease-in (توان ۱.۵)."""
    level_id = _clamp_level_id(level_id)
    t = (level_id - 1) / float(TOTAL_LEVELS - 1)
    return t ** 1.5


class DifficultyManager:
    """تنها منبع حقیقت برای «این مرحله در کدام فاز است» و «چه
    مکانیک‌هایی تا این مرحله باز شده‌اند» -- بدون وابستگی به Kivy یا
    به LevelManager (عمداً جدا نگه داشته شده، هم‌راستا با تفکیک
    مسئولیت‌های باقی پروژه، مثل جدایی scene_builder از raycast)."""

    def get_phase_for_level(self, level_id):
        """دیکشنری فاز (index/key/name_fa/level_start/level_end) که
        این level_id در آن قرار می‌گیرد."""
        level_id = _clamp_level_id(level_id)
        for phase in PHASES:
            if phase['level_start'] <= level_id <= phase['level_end']:
                return phase
        return PHASES[-1]  # محض ایمنی؛ عملاً هرگز به اینجا نمی‌رسد

    def unlocked_mechanics_at(self, level_id):
        """مجموعه‌ی همه‌ی کلیدهای مکانیکی که تا این سطح باز شده‌اند
        (شامل 'normal')."""
        level_id = _clamp_level_id(level_id)
        return {key for key, unlock_lvl in MECHANIC_UNLOCK_LEVEL.items()
                if unlock_lvl <= level_id}

    def next_mechanic_unlock(self, level_id):
        """(کلید_مکانیک, سطح) بعدی‌ای که هنوز باز نشده، یا None اگر
        همه چیز تا این سطح باز شده باشد -- برای «مکانیک بعدی در سطح
        N» در UI (فاز۵)."""
        level_id = _clamp_level_id(level_id)
        upcoming = [(lvl, key) for key, lvl in MECHANIC_UNLOCK_LEVEL.items()
                    if lvl > level_id]
        if not upcoming:
            return None
        upcoming.sort()
        lvl, key = upcoming[0]
        return key, lvl

    def get_recommended_params(self, level_id):
        """پارامترهای پیشنهادی منحنی سختی برای این سطح -- راهنمای
        طراح مرحله (دستی، همین‌جا) و پایه‌ی تولید رویه‌ای فاز۹."""
        level_id = _clamp_level_id(level_id)
        eased = _eased_progress(level_id)
        phase = self.get_phase_for_level(level_id)
        difficulty_value = round(
            _MIN_DIFFICULTY + (_MAX_DIFFICULTY - _MIN_DIFFICULTY) * eased, 2)
        time_limit = round(_MAX_TIME_LIMIT - (_MAX_TIME_LIMIT - _MIN_TIME_LIMIT) * eased)
        target_min, target_max = _TARGET_COUNT_RANGE_BY_PHASE[phase['key']]
        return {
            'level_id': level_id,
            'phase_key': phase['key'],
            'phase_name_fa': phase['name_fa'],
            'difficulty_value': difficulty_value,
            'time_limit_seconds': time_limit,
            'target_count_range': (target_min, target_max),
            'unlocked_mechanics': sorted(self.unlocked_mechanics_at(level_id)),
        }

    def validate_level_conformance(self, level):
        """برمی‌گرداند لیست تخلف‌ها (رشته‌ای قابل‌خواندن)، یا لیست خالی
        اگر مرحله فقط از مکانیک‌هایی استفاده کند که تا level_id خودش
        باز شده‌اند (طبق جدول بخش ۵.۵). برای دفاع در برابر مرحله‌ای که
        زودتر از موعد از یک مکانیک پیشرفته استفاده کرده -- مثلاً پورتال
        در سطح ۵."""
        from game_logic.level_validator import used_mechanic_types

        unlocked = self.unlocked_mechanics_at(level.level_id)
        violations = []
        for mechanic in sorted(used_mechanic_types(level)):
            if mechanic not in unlocked:
                unlock_lvl = MECHANIC_UNLOCK_LEVEL.get(mechanic)
                name = MECHANIC_NAME_FA.get(mechanic, mechanic)
                violations.append(
                    f"مرحله {level.level_id} از «{name}» ({mechanic}) استفاده کرده، "
                    f"ولی این مکانیک تا سطح {unlock_lvl} باز نمی‌شود.")
        return violations
