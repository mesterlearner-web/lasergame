"""
game_logic/endless_mode.py  (فاز ۹)

«حالت بی‌نهایت»: دنباله‌ی بی‌پایان مراحل رویه‌ای با سختی فزاینده؛ باخت (تمام‌شدن زمان) اجرا را تمام می‌کند.
فایل مرجع فقط می‌گوید `EndlessMode.on_level_complete` باید `achievement_manager` را صدا بزند (بخش ۶)؛
بقیه‌ی طراحی تصمیم خودم است:

* هر اجرا ۱ انرژی (مثل شروع یک مرحله‌ی کمپین)، نه به‌ازای هر مرحله -- مصرف انرژی را UI انجام می‌دهد.
* مرحله‌ی s سختی «مرحله‌ی کمپین معادل» را دارد: min(100, 8 + 3·(s−1)). مکانیک‌ها فقط تا همان سطح باز می‌شوند
  و معرفی‌اجباری خاموش است (مولد: equivalent_level).
* **زمان محدود‌تر از کمپین**: max(40, 100 − 3·(s−1)) ثانیه. دلیل: تنها شکل باخت «تمام‌شدن زمان» است؛ با
  ۳۰۰ثانیه‌ی کمپین هیچ‌کس هرگز نمی‌باخت و اجرا بی‌پایان می‌شد.
* پاداش هر مرحله min(25, 3+s) سکه (از مسیر apply_level_rewards، یعنی ضریب سکه‌ی تجهیزات هم اثر می‌کند).
* اجرای نیمه‌کاره ذخیره *نمی‌شود* (اگر برنامه وسط اجرا بسته شود، اجرا از دست می‌رود؛ آمار ثبت‌شده می‌ماند).
* **پیش‌تولید پس‌زمینه**: تولید مرحله‌های بالا روی گوشی میان‌رده می‌تواند چند ثانیه طول بکشد (روی دسکتاپ تا ≈۱ ثانیه
  در سطوح ۸۰ به بالا)؛ در نخ اصلی بازی خطر ANR دارد. پس وقتی مرحله‌ی s شروع می‌شود، مرحله‌ی s+1 در یک نخ
  پس‌زمینه ساخته می‌شود. چون تولید یک تابع خالص از (seed، stage) است، نتیجه‌ی نخ و تولید همزمان دقیقاً یکی است؛
  اگر نخ خطا بدهد به تولید همزمان برمی‌گردیم، و اگر هنوز تمام نشده باشد منتظرش می‌مانیم (کار نیمه‌کاره هدر نمی‌رود).
"""
import threading
import time

from game_logic.difficulty_manager import TOTAL_LEVELS
from game_logic.level import Level
from game_logic.level_generator import generate_level

START_EQUIVALENT_LEVEL = 8
STAGE_LEVEL_STEP = 3
RUN_ENERGY_COST = 1


def _safe_int(value, default=0):
    """مقدار خراب در دیتابیس (رشته‌ی نامعتبر، None، منفی) نباید بارگذاری کل ذخیره را بشکند."""
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _generate_stage(seed, stage):
    """تابع خالص: Level مرحله‌ی stage برای seed -- هیچ وضعیتی از EndlessMode نمی‌خواند (قابل‌اجرا در نخ)."""
    eq = equivalent_level(stage)
    data = generate_level(eq, seed=seed * 1000 + stage, equivalent_level=eq,
                          rewards={'coins': 0, 'gems': 0, 'xp': 0})
    data['time_limit'] = stage_time_limit(stage)
    return Level(data)


def equivalent_level(stage):
    return min(TOTAL_LEVELS, START_EQUIVALENT_LEVEL + STAGE_LEVEL_STEP * (int(stage) - 1))


def stage_time_limit(stage):
    return max(40, 100 - 3 * (int(stage) - 1))


def stage_reward_coins(stage):
    return min(25, 3 + int(stage))


class EndlessMode:
    def __init__(self, best_stage=0, total_runs=0, total_stages_cleared=0):
        self.best_stage = best_stage
        self.total_runs = total_runs
        self.total_stages_cleared = total_stages_cleared
        self._run = None            # {'seed', 'stage', 'cleared'} -- عمداً ذخیره نمی‌شود
        self._prefetch = None       # {'key': (seed, stage), 'level', 'thread'} -- پیش‌تولید پس‌زمینه

    @property
    def is_running(self):
        return self._run is not None

    @property
    def current_stage(self):
        return self._run['stage'] if self._run else 0

    @property
    def stages_cleared_this_run(self):
        return self._run['cleared'] if self._run else 0

    def start_run(self, seed=None):
        """اجرای تازه؛ مرحله‌ی ۱. اجرای قبلی (اگر مانده بود) بدون شمارش دوباره بسته می‌شود."""
        seed = (int(time.time()) & 0x7FFFFFFF) if seed is None else int(seed)
        self._run = {'seed': seed, 'stage': 1, 'cleared': 0}
        self._prefetch = None
        self.total_runs += 1
        return 1

    def build_level(self, stage=None):
        """Level مرحله‌ی جاری (یا stage داده‌شده). برای seed و stage یکسان همیشه همان مرحله. بدون آرگومان
        (مرحله‌ی جاری) مرحله‌ی بعد را هم در پس‌زمینه پیش‌تولید می‌کند."""
        if self._run is None:
            raise RuntimeError("هیچ اجرای فعالی نیست؛ اول start_run() را صدا بزن")
        seed = self._run['seed']
        current = stage is None
        stage = self._run['stage'] if current else int(stage)
        level = self._take_prefetched(seed, stage)
        if level is None:
            level = _generate_stage(seed, stage)
        if current:
            self.prefetch_next()
        return level

    def prefetch_next(self):
        """ساخت مرحله‌ی بعد در نخ پس‌زمینه. True اگر نخ تازه‌ای شروع شد."""
        if self._run is None:
            return False
        key = (self._run['seed'], self._run['stage'] + 1)
        if self._prefetch is not None and self._prefetch['key'] == key:
            return False
        box = {'key': key, 'level': None}

        def work():
            try:
                box['level'] = _generate_stage(*key)
            except Exception:  # noqa: BLE001 -- هر خطایی: بعداً تولید همزمان جایگزین می‌شود
                box['level'] = None

        box['thread'] = threading.Thread(target=work, name='endless-prefetch', daemon=True)
        self._prefetch = box
        box['thread'].start()
        return True

    def _take_prefetched(self, seed, stage):
        box = self._prefetch
        if box is None or box['key'] != (seed, stage):
            return None
        self._prefetch = None
        box['thread'].join()          # اگر هنوز در حال ساخت است، همین‌جا تمام می‌شود (کار هدر نمی‌رود)
        return box['level']

    def on_level_complete(self, achievement_manager=None, economy=None):
        """مرحله‌ی جاری با موفقیت تمام شد: پاداش + آمار + دستاوردها، سپس مرحله‌ی بعد. (طبق بخش ۶ فایل
        مرجع achievement_manager صدا زده می‌شود.) خلاصه را برمی‌گرداند."""
        if self._run is None:
            raise RuntimeError("هیچ اجرای فعالی نیست")
        stage = self._run['stage']
        coins = stage_reward_coins(stage)
        if economy is not None:
            economy.apply_level_rewards({'coins': coins, 'gems': 0, 'xp': 0})
        self._run['cleared'] += 1
        self._run['stage'] = stage + 1
        self.total_stages_cleared += 1
        new_best = stage > self.best_stage
        self.best_stage = max(self.best_stage, stage)
        achievements = achievement_manager.check_endless(stage, economy) if achievement_manager else []
        return {'stage_cleared': stage, 'coins': coins, 'next_stage': stage + 1, 'new_best': new_best,
                'best_stage': self.best_stage, 'achievements': achievements}

    def on_level_failed(self):
        """باخت: اجرا تمام می‌شود. خلاصه‌ی اجرا."""
        return self.finish_run()

    def finish_run(self):
        """پایان اجرا (باخت یا خروج وسط بازی). اگر اجرایی نبود خلاصه‌ی صفر."""
        run, self._run = self._run, None
        self._prefetch = None          # نخ (اگر هنوز می‌دود) خودش تمام می‌شود؛ نتیجه‌اش دیگر لازم نیست
        cleared = run['cleared'] if run else 0
        return {'stages_cleared': cleared, 'best_stage': self.best_stage}

    def to_dict(self):
        return {'best_stage': self.best_stage, 'total_runs': self.total_runs,
                'total_stages_cleared': self.total_stages_cleared}

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        return cls(best_stage=_safe_int(data.get('best_stage')), total_runs=_safe_int(data.get('total_runs')),
                   total_stages_cleared=_safe_int(data.get('total_stages_cleared')))
