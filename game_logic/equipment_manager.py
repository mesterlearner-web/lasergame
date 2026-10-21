"""
game_logic/equipment_manager.py  (فاز ۴)

طبق بخش ۵.۱۰ فایل مرجع: «guns -> یک equipment_manager.apply_gun_bonus
(item.extra['bonus']) جدید (باید ساخته بشه) که روی محاسبه‌ی پاداش
نهایی (ScoreCalculator) و سرعت شلیک اثر بذاره.»

این کلاس در هیچ‌کدوم از ۸ پرامپت اصلی وجود نداشت -- فایل مرجع صریحاً
می‌گه «باید ساخته بشه»، پس اینجا از صفر طراحی شده (نه بازسازی چیزی که
قبلاً جایی تعریف شده باشه). `ScoreCalculator` خودش هنوز ساخته نشده
(بخشی از فاز بعدی UI/امتیازدهیه)؛ این کلاس فقط ضرایب رو نگه می‌داره و
می‌ده -- وقتی ScoreCalculator ساخته بشه، همین دو متد
(`get_score_multiplier`/`get_fire_rate_multiplier`) رو صدا می‌زنه.
"""

#: هر بونوس ناشناخته نادیده گرفته می‌شه (نه خطا) -- یک اسلحه‌ی جدید که
#: بعداً کلید جدیدی معرفی کنه نباید کل apply_gun_bonus رو خراب کنه.
_KNOWN_BONUS_KEYS = ('score_multiplier', 'fire_rate_multiplier')


class EquipmentManager:
    """اسلحه‌ی مجهز فعلی و بونوس‌هاش -- طبق بخش ۵.۱۰."""

    def __init__(self):
        self.equipped_gun_id = None
        self.score_multiplier = 1.0
        self.fire_rate_multiplier = 1.0

    def apply_gun_bonus(self, bonus, gun_id=None):
        """bonus یک دیکشنریه مثل {'score_multiplier': 1.2} یا
        {'fire_rate_multiplier': 1.15} -- از item.extra['bonus'] در
        ShopManager._apply_item_effect میاد. کلیدهای ناشناخته نادیده
        گرفته می‌شن (بدون خطا)."""
        self.equipped_gun_id = gun_id
        self.score_multiplier = float(bonus.get('score_multiplier', 1.0))
        self.fire_rate_multiplier = float(bonus.get('fire_rate_multiplier', 1.0))

    def reset_to_default(self):
        self.equipped_gun_id = None
        self.score_multiplier = 1.0
        self.fire_rate_multiplier = 1.0

    def get_score_multiplier(self):
        return self.score_multiplier

    def get_fire_rate_multiplier(self):
        return self.fire_rate_multiplier

    def to_dict(self):
        return {
            'equipped_gun_id': self.equipped_gun_id,
            'score_multiplier': self.score_multiplier,
            'fire_rate_multiplier': self.fire_rate_multiplier,
        }

    @classmethod
    def from_dict(cls, data):
        em = cls()
        em.equipped_gun_id = data.get('equipped_gun_id')
        em.score_multiplier = data.get('score_multiplier', 1.0)
        em.fire_rate_multiplier = data.get('fire_rate_multiplier', 1.0)
        return em
