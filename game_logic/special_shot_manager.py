"""
game_logic/special_shot_manager.py  (فاز ۳)

مدیریت شلیک‌های ویژه -- طبق تصمیم صریح فایل مرجع (بخش ۵.۶):
«SpecialShotManager.execute_shot باید effects هر نوع شلیک رو به
RaycastEngine.cast(shot_effects=...) پاس بده». منطق واقعی افکت‌ها
(pierce_obstacles, split_on_bounce) از قبل در game_logic/raycast.py
پیاده و در فاز۲ تست شده (بخش ۵.۲)؛ این کلاس آن را دوباره پیاده نمی‌کند،
فقط شلیک انتخابی را با effects درستش به cast() پاس می‌دهد -- دقیقاً
همان چیزی که بخش ۵.۶ می‌خواهد.

⚠️ نکته‌ی مستندسازی: «جدول قیمت/اثر بخش۲.۶.۱» که فایل مرجع به آن ارجاع
می‌دهد ("بدون تغییر") از یکی از ۸ پرامپت خام اصلی است، نه خودِ فایل
مرجع، و در این جلسه در دسترس نیست. SHOT_TYPES زیر بر پایه‌ی تنها دو
افکتی بازسازی شد که واقعاً در raycast.py پیاده‌سازی و تست شده‌اند
(pierce_obstacles, split_on_bounce) -- قیمت‌ها اعداد معقول placeholder‌
هستند، نه از سند اصلی. اگر بعداً متن دقیق بخش۲.۶.۱ در دسترس قرار گرفت،
این جدول باید با آن جایگزین شود؛ در PROGRESS.md هم ثبت شده.

باز کردن قفل شلیک‌های ویژه (unlock_shot) قرار است از فروشگاه فاز۴ صدا
زده شود (بخش ۵.۱۰: `special_shots -> special_shot_manager.unlock_shot
(item_id بدون پیشوند 'shot_')`)؛ چون فاز۴ (اقتصاد) هنوز ساخته نشده،
این کلاس فقط API لازم را آماده و کامل تست‌شده نگه می‌دارد. طبق همین
دلیل، main.py فعلاً فقط شلیک 'normal' را در دسترس می‌گذارد (هیچ
فروشگاهی برای باز کردن بقیه وجود ندارد) -- ولی مسیر اجرای هر سه نوع
از طریق همین کلاس در زنجیره‌ی بازی زنده است.
"""
from game_logic import raycast

SHOT_TYPES = {
    'normal': {
        'name_fa': 'شلیک عادی',
        'cost_coins': 0,
        'effects': (),
        'description_fa': 'شلیک استاندارد -- همیشه و برای همه در دسترس است.',
    },
    'piercing': {
        'name_fa': 'شلیک نافذ',
        'cost_coins': 50,
        'effects': ('pierce_obstacles',),
        'description_fa': 'به‌جای متوقف‌شدن، از موانع عبور می‌کند (حداکثر ۳ برخورد).',
    },
    'splitting': {
        'name_fa': 'شلیک شکافنده',
        'cost_coins': 75,
        'effects': ('split_on_bounce',),
        'description_fa': 'در هر برخورد با آینه، علاوه بر بازتاب اصلی یک پرتوی دوم '
                           'هم با کمی آفست زاویه تولید می‌کند.',
    },
}

#: طبق فایل مرجع -- شلیک عادی همیشه رایگان و باز است؛ بقیه باید از
#: فروشگاه (فاز۴) باز شوند.
DEFAULT_UNLOCKED_SHOTS = ('normal',)


class SpecialShotManager:
    def __init__(self):
        self.unlocked = set(DEFAULT_UNLOCKED_SHOTS)

    def is_unlocked(self, shot_id):
        return shot_id in self.unlocked

    def get_available_shots(self):
        """فقط شلیک‌های باز‌شده، به همان ترتیب تعریف در SHOT_TYPES."""
        return [sid for sid in SHOT_TYPES if sid in self.unlocked]

    def unlock_shot(self, shot_id):
        """طبق تصمیم فایل مرجع بخش ۵.۱۰ -- قرار است از
        ShopManager._apply_item_effect صدا زده شود (فاز۴)؛ shot_id
        بدون پیشوند 'shot_' (آن پیشوند در خودِ ShopManager حذف
        می‌شود، نه اینجا)."""
        if shot_id not in SHOT_TYPES:
            raise ValueError(f"نوع شلیک ناشناخته: {shot_id!r}")
        self.unlocked.add(shot_id)

    def execute_shot(self, shot_id, start_x, start_y, dir_x, dir_y, surfaces,
                      max_bounces=raycast.DEFAULT_MAX_BOUNCES):
        """طبق فایل مرجع بخش ۵.۶: effects شلیک انتخابی را به
        raycast.cast(shot_effects=...) پاس می‌دهد. برمی‌گرداند:
        list[LaserBeam] -- دقیقاً همان چیزی که raycast.cast برمی‌گرداند."""
        if shot_id not in SHOT_TYPES:
            raise ValueError(f"نوع شلیک ناشناخته: {shot_id!r}")
        if shot_id not in self.unlocked:
            raise PermissionError(f"شلیک «{SHOT_TYPES[shot_id]['name_fa']}» هنوز باز نشده است.")

        effects = list(SHOT_TYPES[shot_id]['effects'])
        return raycast.cast(start_x, start_y, dir_x, dir_y, surfaces,
                             max_bounces=max_bounces, shot_effects=effects)

    def to_dict(self):
        return {'unlocked': sorted(self.unlocked)}

    @classmethod
    def from_dict(cls, data):
        manager = cls()
        manager.unlocked = set(data.get('unlocked', DEFAULT_UNLOCKED_SHOTS))
        return manager
