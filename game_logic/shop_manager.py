"""
game_logic/shop_manager.py  (فاز ۴)

طبق بخش ۵.۱۰ فایل مرجع: `ShopManager._apply_item_effect` کامل می‌شه و
دقیقاً این مسیرها رو داره:
- `special_shots` -> `special_shot_manager.unlock_shot(item_id بدون پیشوند 'shot_')`
- `guns` -> `equipment_manager.apply_gun_bonus(item.extra['bonus'])`
- `helpers` (`remove_obstacle`, `skip_level`) -> کال‌بک به GameScreen/LevelManager
- `upgrades` (`regen_speed`, `coin_bonus`) -> مقدار متناظر در EnergyManager/EconomyManager

⚠️ نکته‌ی مستندسازی: «جدول‌های Faucet/Sink» که کاتالوگ آیتم‌ها ازش میاد
از بخش۴ (پرامپت خام) است، نه خودِ فایل مرجع، و در دسترس نیست. کاتالوگ
`data/shop_items.json` بر پایه‌ی همون ۴ دسته‌ای که خودِ فایل مرجع نام
می‌بره ساخته شد؛ قیمت‌ها/آیتم‌های دقیق placeholder معقول‌ان.

`helpers`: چون `GameScreen` هنوز وجود نداره (فاز۵، UI)، به‌جای وصل‌شدن
مستقیم به یک کلاس UI که وجود نداره، یک الگوی callback-registry ساده
طراحی شد (`register_helper_callback`) -- وقتی فاز۵ صفحه‌ی بازی رو
ساخت، فقط کافیه callback واقعی رو ثبت کنه؛ تا اون‌موقع، اگه callback ی
ثبت نشده باشه، آیتم صرفاً در `owned_helpers` نگه داشته می‌شه (خریدشده،
مصرف‌نشده) تا گم نشه.
"""
import json
import os

DEFAULT_ITEMS_PATH = os.path.join('data', 'shop_items.json')

#: این سه دسته یک‌بار خریداری و برای همیشه صاحب‌شون باقی می‌مونن (نه
#: مصرف‌شدنی) -- دوباره‌خریدن‌شون بی‌معنی است. 'helpers' برعکس، مصرفی‌ست
#: (remove_obstacle/skip_level هر بار مصرف می‌شن)، پس تکرارپذیره.
_ONE_TIME_CATEGORIES = ('special_shots', 'guns', 'upgrades')


def load_items(path=DEFAULT_ITEMS_PATH):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


class ShopManager:
    def __init__(self, economy_manager, special_shot_manager=None, equipment_manager=None,
                 energy_manager=None, items=None, items_path=DEFAULT_ITEMS_PATH):
        self.economy_manager = economy_manager
        self.special_shot_manager = special_shot_manager
        self.equipment_manager = equipment_manager
        self.energy_manager = energy_manager
        self.items = {
            item['id']: item
            for item in (items if items is not None else load_items(items_path))
        }
        self.owned_items = set()   # دسته‌های یک‌بارخرید (special_shots/guns/upgrades)
        self.owned_helpers = set() # helpers خریداری‌شده‌ای که هنوز callback نداشتن
        self._helper_callbacks = {}

    def register_helper_callback(self, action_name, callback):
        """فاز۵ (UI) با این، اکشن واقعی remove_obstacle/skip_level رو
        به GameScreen/LevelManager وصل می‌کنه."""
        self._helper_callbacks[action_name] = callback

    def get_item(self, item_id):
        if item_id not in self.items:
            raise ValueError(f"آیتم ناشناخته: {item_id!r}")
        return self.items[item_id]

    def get_items_by_category(self, category):
        return [item for item in self.items.values() if item['category'] == category]

    def purchase_item(self, item_id):
        """نتیجه: {'success': bool, 'reason': str|None, 'item': dict|None}.
        مثل LevelManager.get_level (که None برمی‌گردونه، نه exception،
        برای 'پیدا نشد')، اینجا هم «موجودی کافی نیست»/«قبلاً خریداری
        شده» شرایط عادی و مورد‌انتظار UIان، نه خطای برنامه‌نویسی -- پس
        نتیجه‌ی ساختاریافته برمی‌گردونیم، نه exception. آیتم ناشناخته
        یا نبودِ manager لازم، برعکس، خطای برنامه‌نویسیه -- exception."""
        item = self.get_item(item_id)

        if item['category'] in _ONE_TIME_CATEGORIES and item_id in self.owned_items:
            return {'success': False, 'reason': 'already_owned', 'item': item}

        cost_coins = item.get('cost_coins', 0)
        cost_gems = item.get('cost_gems', 0)
        if not self.economy_manager.can_afford(coins=cost_coins, gems=cost_gems):
            return {'success': False, 'reason': 'insufficient_funds', 'item': item}

        if cost_coins:
            self.economy_manager.spend_coins(cost_coins)
        if cost_gems:
            self.economy_manager.spend_gems(cost_gems)

        self._apply_item_effect(item)
        if item['category'] in _ONE_TIME_CATEGORIES:
            self.owned_items.add(item_id)

        return {'success': True, 'reason': None, 'item': item}

    def _apply_item_effect(self, item):
        category = item['category']

        if category == 'special_shots':
            if self.special_shot_manager is None:
                raise RuntimeError("special_shot_manager به ShopManager داده نشده")
            shot_id = item['id']
            if shot_id.startswith('shot_'):
                shot_id = shot_id[len('shot_'):]
            self.special_shot_manager.unlock_shot(shot_id)

        elif category == 'guns':
            if self.equipment_manager is None:
                raise RuntimeError("equipment_manager به ShopManager داده نشده")
            self.equipment_manager.apply_gun_bonus(item['extra'].get('bonus', {}), gun_id=item['id'])

        elif category == 'helpers':
            action = item['extra'].get('helper_action')
            callback = self._helper_callbacks.get(action)
            if callback is not None:
                callback()
            else:
                self.owned_helpers.add(item['id'])

        elif category == 'upgrades':
            upgrade_type = item['extra'].get('upgrade_type')
            value = item['extra'].get('value')
            if upgrade_type == 'regen_speed':
                if self.energy_manager is None:
                    raise RuntimeError("energy_manager به ShopManager داده نشده")
                self.energy_manager.apply_regen_speed_upgrade(value)
            elif upgrade_type == 'coin_bonus':
                self.economy_manager.apply_coin_bonus_upgrade(value)
            else:
                raise ValueError(f"upgrade_type ناشناخته: {upgrade_type!r}")

        else:
            raise ValueError(f"دسته‌ی ناشناخته: {category!r}")

    def to_dict(self):
        return {
            'owned_items': sorted(self.owned_items),
            'owned_helpers': sorted(self.owned_helpers),
        }

    def restore_from_dict(self, data):
        """برخلاف بقیه‌ی managerها from_dict جداگانه نداره چون
        ShopManager به منابع دیگه (economy_manager و ...) در __init__
        نیاز داره که از قبل باید ساخته شده باشن؛ این متد فقط وضعیت
        owned_* رو روی یک نمونه‌ی از قبل ساخته‌شده برمی‌گردونه."""
        self.owned_items = set(data.get('owned_items', ()))
        self.owned_helpers = set(data.get('owned_helpers', ()))
