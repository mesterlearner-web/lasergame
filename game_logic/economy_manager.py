"""
game_logic/economy_manager.py  (فاز ۴)

دو کلاس مجزا با دو مسئولیت متفاوت (طبق بخش ۵.۱۰ فایل مرجع، که این دو
را با دو اسم جدا -- `EconomyManager` و `EconomyBalance` -- می‌آورد):

۱. EconomyManager -- ردیاب زمان‌اجرا: موجودی واقعی یک بازیکن (سکه/
   جواهر)، با add/spend امن (spend هیچ‌وقت موجودی رو منفی نمی‌کنه).
   بدون وابستگی به Kivy یا دیتابیس -- ذخیره‌سازی واقعی برعهده‌ی
   `game_logic/save_manager.py`ست (همون الگوی جداسازی که در کل پروژه
   تکرار شده: این کلاس فقط قانون بازی رو بلده، نه اینکه کجا ذخیره بشه).

۲. EconomyBalance -- ابزار تحلیلی/طراحی (نه ردیاب یک بازیکن مشخص):
   برای هر یک از ۴ نوع بازیکن (`casual`, `average`, `active`, `whale`)
   درآمد/هزینه‌ی روزانه‌ی *پیش‌بینی‌شده* رو حساب می‌کنه -- دقیقاً طبق
   بخش ۵.۱۰: «باید واقعاً برای هر چهار player_type مقادیر متفاوت (بر
   اساس تعداد جلسه/سطح روزانه‌ی هرکدوم) محاسبه کنه، نه فقط active رو
   جدا کنه».

⚠️ نکته‌ی مستندسازی: فایل مرجع می‌گه «جدول‌های Faucet/Sink ... بدون
تغییر» -- یعنی این جدول‌ها قبلاً در یکی از ۸ پرامپت خام (نه خودِ فایل
مرجع) طراحی شده بودن. آن متن در این جلسه در دسترس نیست. مقادیر
PLAYER_PROFILES و فرمول درآمد/هزینه‌ی زیر با این قیود بازسازی شدن:
(۱) عدد «۱۶ مرحله در روز برای بازیکن فعال» و «~۱۵۳XP/روز برای بازیکن
معمولی» مستقیماً از خودِ فایل مرجع (بخش ۵.۱۲، Battle Pass) گرفته شده
تا دو بخش با هم ناهماهنگ نباشن؛ (۲) whale با اضافه‌کردن یک منبع درآمد
از نوع دیگر (`iap_gems_per_day` -- خرید واقعی، نه فقط بازی بیشتر) از
بقیه به‌طور کیفی متفاوت شد، نه فقط بزرگ‌تر -- که دقیقاً همون چیزیه که
بخش ۵.۱۰ با «نه فقط active رو جدا کنه» می‌خواد اصلاح بشه. اگه بعداً
متن اصلی این جدول‌ها در دسترس قرار گرفت، باید جایگزین این بازسازی بشه.
"""

# میانگین سکه‌ی هر مرحله -- از rewards.coins مراحل واقعی.
# فاز۱۰: با ۱۰۰ مرحله‌ی واقعی بازمحاسبه شد (میانگین دقیق ۳۳٫۱۵ -> ۳۳)؛ قبلاً ۱۷ بود که فقط از
# ۵ مرحله‌ی دستی می‌آمد. tests/test_phase10.py تضمین می‌کند این ثابت با فایل‌های مراحل هم‌خوان بماند
# (هر وقت پاداش مراحل عوض شد، تست می‌شکند و یادآوری می‌کند اینجا را هم به‌روز کنی).
AVG_COINS_PER_LEVEL = 33
DAILY_LOGIN_COINS = 10


class EconomyManager:
    """موجودی زمان‌اجرای یک بازیکن -- سکه و جواهر."""

    def __init__(self, coins=0, gems=0, coin_bonus_multiplier=1.0):
        self.coins = coins
        self.gems = gems
        # طبق بخش ۵.۱۰: «upgrades (coin_bonus) -> مقدار متناظر در
        # EconomyManager ذخیره و در محاسبات بعدی اعمال بشه». فقط روی
        # پاداش مرحله اعمال می‌شه (apply_level_rewards)، نه روی هر
        # add_coins ای -- چون این یک بونوس کسب‌درآمدِ گیم‌پلی است، نه
        # ضریب عمومی (مثلاً استرداد فروشگاه نباید تحت تأثیرش باشه).
        self.coin_bonus_multiplier = coin_bonus_multiplier

    def add_coins(self, amount):
        if amount < 0:
            raise ValueError("amount نمی‌تواند منفی باشد -- برای کم‌کردن از spend_coins استفاده کن")
        self.coins += amount
        return self.coins

    def add_gems(self, amount):
        if amount < 0:
            raise ValueError("amount نمی‌تواند منفی باشد -- برای کم‌کردن از spend_gems استفاده کن")
        self.gems += amount
        return self.gems

    def can_afford(self, coins=0, gems=0):
        return self.coins >= coins and self.gems >= gems

    def spend_coins(self, amount):
        """اگر موجودی کافی نبود، هیچ تغییری نمی‌ده و False برمی‌گردونه
        -- موجودی هیچ‌وقت منفی نمی‌شه."""
        if amount < 0:
            raise ValueError("amount نمی‌تواند منفی باشد")
        if self.coins < amount:
            return False
        self.coins -= amount
        return True

    def spend_gems(self, amount):
        if amount < 0:
            raise ValueError("amount نمی‌تواند منفی باشد")
        if self.gems < amount:
            return False
        self.gems -= amount
        return True

    def apply_level_rewards(self, rewards):
        """rewards یک دیکشنری {'coins':..,'gems':..,'xp':..} است --
        دقیقاً همون‌طور که در assets/levels/*.json ذخیره شده. xp
        اینجا مصرف نمی‌شه (مال BattlePassManager است)، فقط سکه/جواهر
        اعمال می‌شن. سکه تحت تأثیر coin_bonus_multiplier قرار می‌گیره."""
        bonus_coins = round(rewards.get('coins', 0) * self.coin_bonus_multiplier)
        self.add_coins(bonus_coins)
        if rewards.get('gems', 0):
            self.add_gems(rewards['gems'])

    def apply_coin_bonus_upgrade(self, multiplier):
        """طبق بخش ۵.۱۰ -- از ShopManager._apply_item_effect برای
        دسته‌ی 'upgrades' با upgrade_type='coin_bonus' صدا زده می‌شه."""
        self.coin_bonus_multiplier *= multiplier

    def to_dict(self):
        return {'coins': self.coins, 'gems': self.gems,
                'coin_bonus_multiplier': self.coin_bonus_multiplier}

    @classmethod
    def from_dict(cls, data):
        return cls(coins=data.get('coins', 0), gems=data.get('gems', 0),
                    coin_bonus_multiplier=data.get('coin_bonus_multiplier', 1.0))


class EconomyBalance:
    """ابزار تحلیلی طراحی بازی -- نه ردیاب یک بازیکن واقعی. برای
    پرسش‌هایی مثل «آیا بازیکن معمولی تا روز ۳۰ به‌اندازه‌ی کافی سکه
    جمع می‌کنه؟» استفاده می‌شه."""

    PLAYER_PROFILES = {
        'casual':  {'sessions_per_day': 1, 'levels_per_day': 3,  'iap_gems_per_day': 0},
        'average': {'sessions_per_day': 2, 'levels_per_day': 8,  'iap_gems_per_day': 0},
        # ۱۶ مرحله/روز دقیقاً طبق فایل مرجع بخش۵.۱۲ (شبیه‌سازی Battle Pass)
        'active':  {'sessions_per_day': 4, 'levels_per_day': 16, 'iap_gems_per_day': 0},
        'whale':   {'sessions_per_day': 5, 'levels_per_day': 20, 'iap_gems_per_day': 50},
    }

    # نسبت خرج‌کردن روزانه از موجودی محتمل -- بازیکن‌های سنگین‌تر نسبت
    # بزرگ‌تری از درآمدشون رو در فروشگاه خرج می‌کنن.
    _SPEND_RATIO = {'casual': 0.10, 'average': 0.30, 'active': 0.50, 'whale': 0.90}

    def _profile(self, player_type):
        if player_type not in self.PLAYER_PROFILES:
            raise ValueError(
                f"player_type ناشناخته: {player_type!r} -- باید یکی از "
                f"{sorted(self.PLAYER_PROFILES)} باشد")
        return self.PLAYER_PROFILES[player_type]

    def calculate_daily_income(self, player_type):
        profile = self._profile(player_type)
        coins = profile['levels_per_day'] * AVG_COINS_PER_LEVEL + DAILY_LOGIN_COINS
        # جواهرِ درون‌بازی: نرخ کمیاب، هر ۱۰ مرحله حدود ۱ جواهر
        earned_gems = profile['levels_per_day'] / 10.0
        gems = round(earned_gems + profile['iap_gems_per_day'], 2)
        return {'coins': coins, 'gems': gems}

    def calculate_daily_expenses(self, player_type):
        income = self.calculate_daily_income(player_type)
        ratio = self._SPEND_RATIO[player_type]
        return {
            'coins': round(income['coins'] * ratio),
            'gems': round(income['gems'] * ratio, 2),
        }

    def calculate_daily_net(self, player_type):
        income = self.calculate_daily_income(player_type)
        expenses = self.calculate_daily_expenses(player_type)
        return {
            'coins': income['coins'] - expenses['coins'],
            'gems': round(income['gems'] - expenses['gems'], 2),
        }
