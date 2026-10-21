"""
game_logic/save_manager.py  (فاز ۴، بسط فاز۷)

طبق بخش۳ فایل مرجع («ذخیره‌سازی: SQLite (WAL mode) + JSON»): این تنها
ماژولیه که مستقیماً `core/database.py` رو می‌بینه. بقیه‌ی managerها
(EconomyManager, EnergyManager, ...) هیچ‌کدوم SQLite نمی‌شناسن -- فقط
`to_dict()`/`from_dict()` می‌دن، دقیقاً مثل الگویی که از فاز۲
(`Level.from_json_file`) تکرار شده: منطق بازی هیچ‌وقت مستقیماً با
فایل/دیتابیس کار نمی‌کنه.

`PlayerProfile` یک باندل ساده‌ست -- برای این‌که main.py مجبور نباشه
یازده تا self.xxx_manager جدا نگه داره؛ همه از طریق self.profile.economy
و مانند آن در دسترسن.

فاز۷: هر بار load() صدا زده می‌شه (یعنی اپ همین الان باز شده)، یک
«جلسه‌ی امروز» ثبت می‌شه (retention.record_session) و ریست‌های
تقویمی چک می‌شن (missions.maybe_reset_daily/weekly،
weekly_challenge.maybe_reset) -- دقیقاً همون‌جایی که این کار باید
اتفاق بیفته، چون این تنها نقطه‌ایه که همیشه یک‌بار در شروع هر اجرای
واقعی اپ صدا زده می‌شه.
"""
from core.database import Database, DEFAULT_DB_PATH
from game_logic.achievements import AchievementManager
from game_logic.battle_pass_manager import BattlePassManager
from game_logic.daily_challenge import DailyChallenge
from game_logic.daily_rewards import DailyRewardsManager
from game_logic.endless_mode import EndlessMode
from game_logic.economy_manager import EconomyManager
from game_logic.energy_manager import EnergyManager
from game_logic.equipment_manager import EquipmentManager
from game_logic.missions import MissionManager
from game_logic.retention_analytics import RetentionAnalytics
from game_logic.settings_manager import SettingsManager
from game_logic.shop_manager import ShopManager
from game_logic.special_shot_manager import SpecialShotManager
from game_logic.weekly_challenge import WeeklyChallenge

SAVE_KEY = 'player_profile'


class PlayerProfile:
    def __init__(self, economy, energy, equipment, battle_pass, special_shots, shop,
                 level_manager, settings, missions, daily_rewards, weekly_challenge, retention,
                 endless=None, daily_challenge=None, achievements=None):
        self.economy = economy
        self.energy = energy
        self.equipment = equipment
        self.battle_pass = battle_pass
        self.special_shots = special_shots
        self.shop = shop
        self.level_manager = level_manager
        self.settings = settings
        # فاز۷ -- نگه‌داشت (Retention)
        self.missions = missions
        self.daily_rewards = daily_rewards
        self.weekly_challenge = weekly_challenge
        self.retention = retention
        # فاز۹ -- محتوای کامل (پیش‌فرض‌های None: ذخیره‌ی قدیمی/ساخت مستقیم بدون این سه هم کار کند)
        self.endless = endless if endless is not None else EndlessMode()
        self.daily_challenge = daily_challenge if daily_challenge is not None else DailyChallenge()
        self.achievements = achievements if achievements is not None else AchievementManager()


class SaveManager:
    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db = Database(db_path)

    def load(self, level_manager, shop_items_path=None):
        """یک PlayerProfile کامل برمی‌گردونه: یا بازسازی‌شده از آخرین
        ذخیره، یا (برای بازیکن جدید) با مقادیر پیش‌فرض هر manager."""
        data = self.db.get(SAVE_KEY)

        if data is None:
            economy = EconomyManager()
            energy = EnergyManager()
            equipment = EquipmentManager()
            battle_pass = BattlePassManager()
            special_shots = SpecialShotManager()
            settings = SettingsManager()
            missions = MissionManager()
            daily_rewards = DailyRewardsManager()
            weekly_challenge = WeeklyChallenge()
            retention = RetentionAnalytics()
            endless = EndlessMode()
            daily_challenge = DailyChallenge()
            achievements = AchievementManager()
        else:
            economy = EconomyManager.from_dict(data.get('economy', {}))
            energy = EnergyManager.from_dict(data.get('energy', {}))
            equipment = EquipmentManager.from_dict(data.get('equipment', {}))
            battle_pass = BattlePassManager.from_dict(data.get('battle_pass', {}))
            special_shots = SpecialShotManager.from_dict(data.get('special_shots', {}))
            settings = SettingsManager.from_dict(data.get('settings', {}))
            level_manager.import_progress(data.get('level_manager', {}))
            missions = MissionManager.from_dict(data.get('missions', {}))
            daily_rewards = DailyRewardsManager.from_dict(data.get('daily_rewards', {}))
            weekly_challenge = WeeklyChallenge.from_dict(data.get('weekly_challenge', {}))
            retention = RetentionAnalytics.from_dict(data.get('retention', {}))
            # ذخیره‌های قبل از فاز۹ این کلیدها را ندارند -> پیش‌فرض
            endless = EndlessMode.from_dict(data.get('endless', {}))
            daily_challenge = DailyChallenge.from_dict(data.get('daily_challenge', {}))
            achievements = AchievementManager.from_dict(data.get('achievements', {}))

        # فاز۷ -- هر بار پروفایل load می‌شه یعنی بازیکن همین الان اومده:
        # جلسه ثبت، و ریست‌های تقویمی (روزانه/هفتگی) چک می‌شن. باگ واقعی
        # که همین‌جا حین تست پیدا شد: session_started نباید به‌ازای *هر*
        # باز شدن اپ گزارش بشه -- وگرنه بستن‌و‌بازکردن مکرر اپ در یک روز،
        # ماموریت هفتگیِ «۵ روز مختلف» رو به‌اشتباه در یک روز کامل می‌کرد.
        # فقط وقتی record_session() می‌گه امروز واقعاً اولین جلسه‌ست،
        # گزارش می‌شه.
        is_new_day = retention.record_session()
        missions.maybe_reset_daily()
        missions.maybe_reset_weekly()
        weekly_challenge.maybe_reset()
        if is_new_day:
            missions.report_event('session_started', 1)

        shop_kwargs = {'items_path': shop_items_path} if shop_items_path else {}
        shop = ShopManager(economy, special_shot_manager=special_shots,
                            equipment_manager=equipment, energy_manager=energy, **shop_kwargs)
        if data is not None:
            shop.restore_from_dict(data.get('shop', {}))

        return PlayerProfile(economy, energy, equipment, battle_pass, special_shots, shop,
                              level_manager, settings, missions, daily_rewards, weekly_challenge,
                              retention, endless, daily_challenge, achievements)

    def save(self, profile):
        data = {
            'economy': profile.economy.to_dict(),
            'energy': profile.energy.to_dict(),
            'equipment': profile.equipment.to_dict(),
            'battle_pass': profile.battle_pass.to_dict(),
            'special_shots': profile.special_shots.to_dict(),
            'shop': profile.shop.to_dict(),
            'level_manager': profile.level_manager.export_progress(),
            'settings': profile.settings.to_dict(),
            'missions': profile.missions.to_dict(),
            'daily_rewards': profile.daily_rewards.to_dict(),
            'weekly_challenge': profile.weekly_challenge.to_dict(),
            'retention': profile.retention.to_dict(),
            'endless': profile.endless.to_dict(),
            'daily_challenge': profile.daily_challenge.to_dict(),
            'achievements': profile.achievements.to_dict(),
        }
        self.db.set(SAVE_KEY, data)

    def close(self):
        self.db.close()

    def reset(self):
        """پاک کردن کامل ذخیره -- برای دکمه‌ی «شروع از نو» در
        SettingsScreen (فاز۵). خودِ فایل دیتابیس رو حذف نمی‌کنه، فقط
        کلید ذخیره رو -- بار بعدی که load() صدا زده بشه، انگار بازیکن
        کاملاً تازه‌ست."""
        self.db.delete(SAVE_KEY)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
