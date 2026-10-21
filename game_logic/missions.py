"""
game_logic/missions.py  (فاز ۷)

طبق فایل مرجع بخش ۵.۱۳: «لیست ۱۰ روزانه + ۱۰ هفتگی بخش۷، با منطق
_load()ی که واقعاً از دیتابیس بازسازی می‌کنه (_find_mission_by_id +
copy.deepcopy).»

⚠️ نکته‌ی مستندسازی: لیست دقیق ۱۰+۱۰ ماموریت («بخش۷» -- یکی از ۸
پرامپت خام اصلی) در این جلسه در دسترس نیست؛ فقط الگوی معماری
(_find_mission_by_id + deepcopy) مشخص شده. لیست ۲۰ ماموریت زیر از صفر
طراحی شد، با این قید مهم: هر ماموریت باید روی metricـی باشه که همین
الان واقعاً در بازی رخ می‌ده و قابل‌گزارش‌شدنه (شلیک، هدف منهدم‌شده،
مرحله‌ی کامل‌شده، ستاره، سکه، ...) -- نه metric فرضی که چیزی گزارشش
نمی‌کنه.

الگوی _find_mission_by_id + deepcopy چرا لازمه: ماموریت‌ها یک‌بار
به‌صورت Template ثابت (DAILY/WEEKLY_MISSION_DEFINITIONS) تعریف می‌شن.
اگه نمونه‌ی *فعال* بازیکن مستقیماً همون شیء Template باشه (نه یک
deepcopy ازش)، تغییر progress بازیکن دائمی روی تعریف اصلی می‌شینه --
و همه‌ی بازیکن‌های بعدی (یا حتی reload بعدی همین بازیکن) با یک
Template خراب‌شده مواجه می‌شن. deepcopy این خطر رو کاملاً از بین
می‌بره.
"""
import copy
from datetime import date


class Mission:
    __slots__ = ('mission_id', 'name_fa', 'description_fa', 'kind', 'metric',
                 'target_value', 'reward', 'progress', 'claimed')

    def __init__(self, mission_id, name_fa, description_fa, kind, metric, target_value, reward):
        self.mission_id = mission_id
        self.name_fa = name_fa
        self.description_fa = description_fa
        self.kind = kind  # 'daily' | 'weekly'
        self.metric = metric
        self.target_value = target_value
        self.reward = reward
        self.progress = 0
        self.claimed = False

    @property
    def is_complete(self):
        return self.progress >= self.target_value

    def add_progress(self, metric, amount=1):
        if self.claimed or metric != self.metric:
            return
        self.progress = min(self.target_value, self.progress + amount)

    def to_state_dict(self):
        """فقط بخش قابل‌تغییر -- خودِ تعریف (نام/metric/target/reward)
        از Template بازسازی می‌شه، نه از دیتابیس خونده می‌شه."""
        return {'progress': self.progress, 'claimed': self.claimed}


# طبق بخش۵.۴ (جدول سرعت اهداف) و بقیه‌ی سیستم‌های موجود -- هر متریک
# پایین همین الان جایی در main.py/game_screen.py/shop_screen.py قابل‌
# گزارش‌شدنه (سیم‌کشی دقیق در بخش «قدم بعدی» PROGRESS.md مستند شده).
DAILY_MISSION_DEFINITIONS = [
    Mission('daily_login', 'ورود روزانه', 'امروز بازی رو باز کن', 'daily', 'session_started', 1, {'coins': 10}),
    Mission('daily_fire_10', 'شلیک‌گر', 'در طول امروز ۱۰ بار شلیک کن', 'daily', 'shots_fired', 10, {'coins': 20}),
    Mission('daily_fire_25', 'انگشت داغ', '۲۵ بار شلیک کن', 'daily', 'shots_fired', 25, {'coins': 35}),
    Mission('daily_destroy_5', 'شکارچی هدف', '۵ هدف نابود کن', 'daily', 'targets_destroyed', 5, {'coins': 25}),
    Mission('daily_win_1', 'برد امروز', 'یک مرحله رو کامل کن', 'daily', 'levels_completed', 1, {'coins': 15}),
    Mission('daily_win_3', 'پشتکار', '۳ مرحله رو کامل کن', 'daily', 'levels_completed', 3, {'coins': 40, 'gems': 1}),
    Mission('daily_perfect_1', 'بی‌نقص', 'یک مرحله رو بی‌نقص تمام کن', 'daily', 'perfect_levels', 1, {'coins': 30}),
    Mission('daily_star_3', 'درخشش', '۳ ستاره در مجموع بگیر', 'daily', 'stars_earned', 3, {'coins': 25}),
    Mission('daily_special_shot_1', 'شلیک ویژه', 'یک‌بار از شلیک ویژه استفاده کن', 'daily', 'special_shots_used', 1, {'coins': 20}),
    Mission('daily_coins_50', 'پس‌انداز', '۵۰ سکه جمع کن', 'daily', 'coins_earned', 50, {'gems': 1}),
]

WEEKLY_MISSION_DEFINITIONS = [
    Mission('weekly_login_5', 'وفاداری', '۵ روز از این هفته بازی رو باز کن', 'weekly', 'session_started', 5, {'coins': 180, 'gems': 2}),
    Mission('weekly_fire_100', 'تمرین هفتگی', 'در طول هفته ۱۰۰ بار شلیک کن', 'weekly', 'shots_fired', 100, {'coins': 120}),
    Mission('weekly_fire_250', 'تیرانداز حرفه‌ای', '۲۵۰ بار شلیک کن', 'weekly', 'shots_fired', 250, {'coins': 200, 'gems': 2}),
    Mission('weekly_destroy_40', 'نابودگر هفته', '۴۰ هدف نابود کن', 'weekly', 'targets_destroyed', 40, {'coins': 150}),
    Mission('weekly_win_10', 'ماراتن', '۱۰ مرحله کامل کن', 'weekly', 'levels_completed', 10, {'coins': 200, 'gems': 3}),
    Mission('weekly_perfect_5', 'استاد بی‌نقص', '۵ مرحله رو بی‌نقص تمام کن', 'weekly', 'perfect_levels', 5, {'coins': 180, 'gems': 2}),
    Mission('weekly_star_20', 'ستاره‌جمع‌کن', '۲۰ ستاره در مجموع بگیر', 'weekly', 'stars_earned', 20, {'coins': 150}),
    Mission('weekly_special_shot_10', 'زرادخانه', '۱۰ بار از شلیک‌های ویژه استفاده کن', 'weekly', 'special_shots_used', 10, {'coins': 130}),
    Mission('weekly_coins_400', 'سرمایه‌گذار', '۴۰۰ سکه جمع کن', 'weekly', 'coins_earned', 400, {'gems': 4}),
    Mission('weekly_shop_purchase_1', 'خریدار', 'یک آیتم از فروشگاه بخر', 'weekly', 'shop_purchases', 1, {'coins': 100}),
]


def _find_definition_by_id(mission_id):
    for m in DAILY_MISSION_DEFINITIONS + WEEKLY_MISSION_DEFINITIONS:
        if m.mission_id == mission_id:
            return m
    return None


def _week_key(today):
    iso_year, iso_week, _ = today.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


class MissionManager:
    def __init__(self, daily_missions=None, weekly_missions=None,
                 daily_reset_at=None, weekly_reset_at=None):
        self.daily_missions = daily_missions if daily_missions is not None else \
            [copy.deepcopy(m) for m in DAILY_MISSION_DEFINITIONS]
        self.weekly_missions = weekly_missions if weekly_missions is not None else \
            [copy.deepcopy(m) for m in WEEKLY_MISSION_DEFINITIONS]
        self.daily_reset_at = daily_reset_at
        self.weekly_reset_at = weekly_reset_at

    def _find_mission_by_id(self, mission_id):
        """طبق بخش۵.۱۳ -- نام متد عیناً از فایل مرجع."""
        for m in self.daily_missions + self.weekly_missions:
            if m.mission_id == mission_id:
                return m
        return None

    def report_event(self, metric, amount=1):
        """از GameWidget/ShopScreen صدا زده می‌شه (هر شلیک، هر خرید، ...).
        هر ماموریت فعالی که روی همین metric کار می‌کنه، پیش می‌ره."""
        for m in self.daily_missions + self.weekly_missions:
            m.add_progress(metric, amount)

    def claim(self, mission_id):
        m = self._find_mission_by_id(mission_id)
        if m is None:
            raise ValueError(f"ماموریت ناشناخته: {mission_id!r}")
        if not m.is_complete:
            raise ValueError("این ماموریت هنوز کامل نشده.")
        if m.claimed:
            raise ValueError("پاداش این ماموریت قبلاً دریافت شده.")
        m.claimed = True
        return dict(m.reward)

    def maybe_reset_daily(self, today=None):
        """طبق منطق _load() بخش۵.۱۳ -- اگه روز عوض شده، هر ۱۰ ماموریت
        روزانه از Template دوباره deepcopy و progress صفر می‌شن."""
        today = today or date.today()
        today_str = today.isoformat()
        if self.daily_reset_at != today_str:
            self.daily_missions = [copy.deepcopy(m) for m in DAILY_MISSION_DEFINITIONS]
            self.daily_reset_at = today_str
            return True
        return False

    def maybe_reset_weekly(self, today=None):
        today = today or date.today()
        key = _week_key(today)
        if self.weekly_reset_at != key:
            self.weekly_missions = [copy.deepcopy(m) for m in WEEKLY_MISSION_DEFINITIONS]
            self.weekly_reset_at = key
            return True
        return False

    def to_dict(self):
        return {
            'daily_reset_at': self.daily_reset_at,
            'weekly_reset_at': self.weekly_reset_at,
            'daily_state': {m.mission_id: m.to_state_dict() for m in self.daily_missions},
            'weekly_state': {m.mission_id: m.to_state_dict() for m in self.weekly_missions},
        }

    @classmethod
    def from_dict(cls, data):
        """طبق بخش۵.۱۳ -- این متد همون _load() توصیف‌شده است: هر
        mission_id ذخیره‌شده با _find_definition_by_id پیدا و deepcopy
        می‌شه، بعد progress/claimed ذخیره‌شده روش اعمال می‌شه. اگه یک
        mission_id دیگه در تعریف‌های فعلی وجود نداشت (مثلاً بعد از
        آپدیت لیست ماموریت‌ها)، بی‌صدا نادیده گرفته می‌شه -- نه خطا."""
        def _load_group(definitions, state):
            result = []
            for definition in definitions:
                mission = copy.deepcopy(definition)
                saved = state.get(mission.mission_id)
                if saved is not None:
                    mission.progress = saved.get('progress', 0)
                    mission.claimed = saved.get('claimed', False)
                result.append(mission)
            return result

        daily = _load_group(DAILY_MISSION_DEFINITIONS, data.get('daily_state', {}))
        weekly = _load_group(WEEKLY_MISSION_DEFINITIONS, data.get('weekly_state', {}))
        return cls(daily_missions=daily, weekly_missions=weekly,
                    daily_reset_at=data.get('daily_reset_at'),
                    weekly_reset_at=data.get('weekly_reset_at'))
