"""
game_logic/battle_pass_manager.py  (فاز ۴)

طبق بخش ۵.۱۲ فایل مرجع -- **بازتعادل کامل، تأیید‌شده با شبیه‌سازی**
(این بخش برخلاف DifficultyManager/SpecialShotManager، کاملاً و دقیق
مشخص شده؛ چیزی برای بازسازی حدسی نیست):

- XP(level) = 40 + level*5  (جمع کل ۵۰ سطح = ۸۳۷۵)
- جدول پاداش فرمولی (نه هاردکد): coins = 50 + level*15، هر ۵ سطح یک
  جواهر اضافه (level%5==0)، در سطوح ۱۰/۲۵/۴۵ یک آیتم خاص.
- جایزه‌ی نسخه‌ی پولی روی رایگان *اضافه* می‌شه، نه جایگزینش.
- جدول در data/battle_pass_rewards.json ذخیره می‌شه، نه هاردکد در کد.

⚠️ نکته‌ی مستندسازی (برای شفافیت، نه چون این بخش ناقصه): فایل مرجع
دقیقاً می‌گه فرمول جایزه‌ی «رایگان» چیه، ولی برای مسیر «پولی» (premium)
فقط قانون *ترکیب* رو می‌ده («جمع می‌زنه»)، نه فرمول خودِ مقدار پولی.
اینجا یک جایزه‌ی پولی ساده و فرمولی اضافه شد (`gems = 5 + level//10`)
تا مسیر پولی خالی نباشه و قانون «جمع، نه جایگزینی» قابل‌تست باشه؛ اگه
عدد دقیق‌تری از سند اصلی در دسترس قرار گرفت، همین‌جا (PREMIUM_GEMS_FN)
باید جایگزین بشه.
"""
import json
import os

MAX_LEVEL = 50
DEFAULT_REWARDS_PATH = os.path.join('data', 'battle_pass_rewards.json')

# سطوحی که یک آیتم خاص (اسکین/اسلحه) در مسیر رایگان می‌دن -- طبق بخش ۵.۱۲
SPECIAL_ITEM_LEVELS = {
    10: 'skin_azure_beam',
    25: 'gun_prism_blaster',
    45: 'skin_golden_ricochet',
}


def xp_cost_for_level(level):
    """XP لازم برای رسیدن از سطح level-1 به level -- فرمول دقیق بخش۵.۱۲."""
    return 40 + level * 5


def total_xp_for_level(level):
    """XP تجمعی لازم برای رسیدن به این سطح از صفر (فرم بسته‌ی همون فرمول)."""
    if level <= 0:
        return 0
    return 40 * level + 5 * level * (level + 1) // 2


def generate_rewards_table(max_level=MAX_LEVEL):
    """جدول پاداش ۵۰ سطح رو فرمولی می‌سازه -- طبق بخش ۵.۱۲: سکه، هر ۵
    سطح یک جواهر، آیتم خاص در ۱۰/۲۵/۴۵. پاداش پولی: یک مقدار جواهر
    فرمولی و ساده (بالا توضیح داده شد -- جایگزین‌شدنی با عدد دقیق‌تر)."""
    table = []
    for level in range(1, max_level + 1):
        free = {'coins': 50 + level * 15}
        if level % 5 == 0:
            free['gems'] = 1
        if level in SPECIAL_ITEM_LEVELS:
            free['special_items'] = [SPECIAL_ITEM_LEVELS[level]]
        premium = {'gems': 5 + level // 10}
        table.append({'level': level, 'free': free, 'premium': premium})
    return table


def load_rewards_table(path=DEFAULT_REWARDS_PATH):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _combine_rewards(free, premium):
    """طبق بخش ۵.۱۲: هر دو دیکشنری جمع می‌شن، نه اینکه premium جایگزین
    free بشه. برای کلیدهای عددی مشترک (coins/gems) جمع ساده؛ برای
    کلیدهای غیرعددی (special_items) از هر دو طرف الحاق می‌شه."""
    combined = dict(free)
    for key, value in premium.items():
        if key not in combined:
            combined[key] = value
        elif isinstance(value, (int, float)) and isinstance(combined[key], (int, float)):
            combined[key] = combined[key] + value
        elif isinstance(value, list) and isinstance(combined[key], list):
            combined[key] = combined[key] + value
        else:
            combined[key] = value
    return combined


class BattlePassManager:
    def __init__(self, total_xp=0, is_premium=False, claimed_levels=None,
                 rewards_table=None, rewards_path=DEFAULT_REWARDS_PATH):
        self.total_xp = total_xp
        self.is_premium = is_premium
        self.claimed_levels = set(claimed_levels or ())
        self._rewards_by_level = {
            entry['level']: entry
            for entry in (rewards_table if rewards_table is not None else load_rewards_table(rewards_path))
        }

    def get_current_level(self):
        """سطح فعلی طبق total_xp، سقف‌زده در MAX_LEVEL."""
        level = 0
        while level < MAX_LEVEL and self.total_xp >= total_xp_for_level(level + 1):
            level += 1
        return level

    def add_xp(self, amount):
        if amount < 0:
            raise ValueError("amount نمی‌تواند منفی باشد")
        self.total_xp += amount
        return self.get_current_level()

    def get_progress_to_next_level(self):
        """(xp_رسیده‌به‌سطح‌فعلی, xp_لازم‌برای‌سطح‌بعدی) یا None اگه سقف زده باشه."""
        current = self.get_current_level()
        if current >= MAX_LEVEL:
            return None
        floor_xp = total_xp_for_level(current)
        next_xp = total_xp_for_level(current + 1)
        return (self.total_xp - floor_xp, next_xp - floor_xp)

    def get_reward(self, level):
        """پاداش این سطح -- اگه is_premium باشه، رایگان+پولی جمع می‌شن
        (بخش ۵.۱۲: 'اضافه می‌شه نه جایگزینش')."""
        entry = self._rewards_by_level[level]
        if self.is_premium:
            return _combine_rewards(entry['free'], entry['premium'])
        return dict(entry['free'])

    def claim_reward(self, level):
        if level > self.get_current_level():
            raise ValueError(f"سطح {level} هنوز باز نشده (سطح فعلی: {self.get_current_level()})")
        if level in self.claimed_levels:
            raise ValueError(f"پاداش سطح {level} قبلاً گرفته شده")
        self.claimed_levels.add(level)
        return self.get_reward(level)

    def to_dict(self):
        return {
            'total_xp': self.total_xp,
            'is_premium': self.is_premium,
            'claimed_levels': sorted(self.claimed_levels),
        }

    @classmethod
    def from_dict(cls, data, rewards_table=None, rewards_path=DEFAULT_REWARDS_PATH):
        return cls(
            total_xp=data.get('total_xp', 0),
            is_premium=data.get('is_premium', False),
            claimed_levels=data.get('claimed_levels', []),
            rewards_table=rewards_table,
            rewards_path=rewards_path,
        )


if __name__ == '__main__':
    # اجرای مستقیم این فایل، جدول پاداش رو بازتولید می‌کنه -- طبق بخش
    # ۵.۱۲: «این جدول در فایل جدا ذخیره می‌شه، نه هاردکد در کد».
    out_path = DEFAULT_REWARDS_PATH
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(generate_rewards_table(), f, ensure_ascii=False, indent=2)
    print(f"نوشته شد: {out_path}")
