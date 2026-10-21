"""
game_logic/level_manager.py

بارگذاری و مدیریت مراحل از assets/levels/*.json.
"""
import json
from pathlib import Path

from game_logic.level import Level


class LevelManager:
    def __init__(self, levels_dir='assets/levels'):
        self.levels_dir = Path(levels_dir)
        self.levels = {}
        self.current_level = None
        self.current_level_id = None
        self.unlocked_level = 1
        # فاز۵ -- بهترین نتیجه‌ی هر مرحله (برای نمایش ستاره در
        # LevelSelectScreen). level_id -> {'stars', 'shots_used', 'time_remaining'}
        self.level_results = {}
        self._load_all_levels()

    def _load_all_levels(self):
        if not self.levels_dir.exists():
            return
        for level_file in sorted(self.levels_dir.glob('level_*.json')):
            with open(level_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            level = Level(data)
            self.levels[level.level_id] = level

    def get_level(self, level_id):
        return self.levels.get(level_id)

    def load_level(self, level_id):
        level = self.get_level(level_id)
        if level:
            self.current_level = level
            self.current_level_id = level_id
        return level

    def is_unlocked(self, level_id):
        return level_id <= self.unlocked_level

    def unlock_next(self):
        """باید بعد از برد مرحله‌ی current_level_id صدا زده شود -- طبق
        اصلاح لازم‌الاجرا: قبل از این باید حتماً load_level صدا زده
        شده باشد تا current_level_id هماهنگ باشد."""
        if self.current_level_id is not None and self.current_level_id >= self.unlocked_level:
            self.unlocked_level = self.current_level_id + 1

    def get_next_level_id(self):
        if self.current_level_id is None:
            return None
        next_id = self.current_level_id + 1
        return next_id if next_id in self.levels else None

    # ---------- افزوده‌های فاز۳ -- برای پیشروی واقعی بین چند مرحله ----------

    @property
    def level_count(self):
        """تعداد کل مرحله‌هایی که از assets/levels/*.json بارگذاری شده‌اند."""
        return len(self.levels)

    def get_all_level_ids(self):
        """همه‌ی level_id های بارگذاری‌شده، مرتب‌شده صعودی."""
        return sorted(self.levels.keys())

    def get_unlocked_level_ids(self):
        """زیرمجموعه‌ی get_all_level_ids که تا این لحظه باز شده‌اند."""
        return [lid for lid in self.get_all_level_ids() if self.is_unlocked(lid)]

    def has_next_level(self):
        """True اگر مرحله‌ای بعد از current_level_id در assets/levels
        وجود داشته باشد -- برای تشخیص «کمپین تمام شد» در main.py."""
        return self.get_next_level_id() is not None

    # ---------- افزوده‌های فاز۵ -- برای نمایش ستاره در LevelSelectScreen ----------

    def record_level_result(self, level_id, stars, shots_used=None, time_remaining=None):
        """فقط وقتی رکورد به‌روزرسانی می‌شه که نتیجه‌ی تازه *بهتر* از
        بهترین تلاش قبلیه (بیشترین ستاره تا الان نگه داشته می‌شه، نه
        آخرین تلاش -- طبق قرارداد استاندارد بازی‌های پازل موبایل)."""
        existing = self.level_results.get(level_id)
        if existing is None or stars > existing.get('stars', 0):
            self.level_results[level_id] = {
                'stars': stars, 'shots_used': shots_used, 'time_remaining': time_remaining,
            }

    def get_level_result(self, level_id):
        """None اگه هنوز هیچ‌وقت با موفقیت تمام نشده."""
        return self.level_results.get(level_id)

    def get_total_stars(self):
        """مجموع بهترین ستاره‌های همه‌ی مراحل -- برای ProfileScreen."""
        return sum(r.get('stars', 0) for r in self.level_results.values())

    # ---------- افزوده‌های فاز۴ -- برای ذخیره/بازیابی توسط SaveManager ----------

    def export_progress(self):
        """LevelManager هیچ‌وقت خودش SQLite/JSON نمی‌شناسه (هم‌راستا با
        بقیه‌ی پروژه: این کلاس فقط قانون بازی رو بلده)؛
        game_logic/save_manager.py این دیکشنری رو ذخیره می‌کنه."""
        return {
            'unlocked_level': self.unlocked_level,
            'current_level_id': self.current_level_id,
            # کلیدهای dict در JSON همیشه رشته‌ان -- سرِ import_progress
            # دوباره به int تبدیل می‌شن (پایین).
            'level_results': {str(k): v for k, v in self.level_results.items()},
        }

    def import_progress(self, data):
        self.unlocked_level = data.get('unlocked_level', 1)
        self.level_results = {int(k): v for k, v in data.get('level_results', {}).items()}
        saved_current = data.get('current_level_id')
        if saved_current is not None and saved_current in self.levels:
            self.load_level(saved_current)
