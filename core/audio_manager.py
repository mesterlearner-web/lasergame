"""
core/audio_manager.py  (فاز ۶)

طبق فایل مرجع بخش ۵.۷: «AudioManager: نسخه‌ی پیشرفته‌ی بخش۵، با این
اصلاح: پارامتر عددی pitch که هیچ‌جا اعمال نمی‌شد حذف می‌شه؛ به‌جاش
فقط از چند فایل صوتی از‌پیش‌ضبط‌شده (مثل ۳ نسخه‌ی mirror_hit) برای
تنوع استفاده می‌شه.»

📌 فاز۱۰: فایل‌های صوتی واقعی حالا در assets/audio هستند (سنتز رویه‌ای با
tools/generate_audio.py؛ جایگزین‌کردنشان با صدای حرفه‌ای فقط با کپی فایل با همان نام ممکن است).
متن زیر مربوط به قبل از فاز۱۰ است و فقط برای توضیح رفتار «فایل موجود نیست» نگه داشته شده.

⚠️ نکته‌ی تاریخی (قبل از فاز۱۰): فایل‌های صوتی واقعی (.ogg) بخشی از آن جلسه
نبودن -- نه تولید صدا جزو ابزارهای در دسترسمه، نه خودِ فایل‌های
بخش۵/۶ (که این کلاس رو دقیق و کامل مشخص کرده بودن، طبق ارجاع فایل
مرجع) در دسترسن. این کلاس با فرض این نوشته شده که یک طراح صدا بعداً
فایل‌های واقعی رو در assets/audio/ (با همین نام‌ها) اضافه می‌کنه:
- اگه SoundLoader (Kivy) در دسترس نباشه (مثلاً همین sandbox)، یا
  فایل موجود نباشه، play_sfx/play_music به‌شکل کاملاً امن سکوت
  می‌کنن (نه کرش، نه Exception) -- یعنی همین امروز هم قابل‌فراخوانی و
  تست‌پذیرن، فقط صدایی واقعاً پخش نمی‌شه.
- منطق تصمیم‌گیری (کدوم فایل انتخاب بشه؟ آیا صدا/موسیقی طبق تنظیمات
  کاربر خاموشه؟) کاملاً مستقل از این‌که فایل واقعی وجود داره یا نه
  تست شده.

Singleton (طبق الگوی AnimationManager بخش۵.۱۸ -- سرویس‌های سراسری
نباید هر بار نمونه‌ی تازه بسازن).
"""
import os
import random

try:
    from kivy.core.audio import SoundLoader
except Exception:  # pragma: no cover -- در sandbox بدون Kivy نصب نمی‌شه
    SoundLoader = None

# فاز۱۰: مسیر مطلق نسبت به خودِ پروژه (نه نسبت به cwd)؛ مسیر نسبی فقط وقتی کار می‌کرد که cwd
# دقیقاً ریشه‌ی پروژه باشد -- روی اندروید/اجرای از پوشه‌ی دیگر بی‌صدا شکست می‌خورد.
DEFAULT_AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 'assets', 'audio')

#: طبق بخش۵.۷ -- چند نسخه‌ی هر افکت به‌جای یک پارامتر عددی pitch.
#: نام‌های فایل placeholder ان (فایل واقعی بعداً توسط طراح صدا اضافه
#: می‌شه)؛ خودِ منطق انتخاب تصادفی/gating از همین امروز درست کار می‌کنه.
SFX_VARIANTS = {
    'mirror_hit': ['mirror_hit_1.ogg', 'mirror_hit_2.ogg', 'mirror_hit_3.ogg'],
    'target_destroy': ['target_destroy_1.ogg', 'target_destroy_2.ogg'],
    'obstacle_hit': ['obstacle_hit_1.ogg'],
    'shot_fire': ['shot_fire_1.ogg', 'shot_fire_2.ogg'],
    'level_win': ['level_win.ogg'],
    'level_lose': ['level_lose.ogg'],
    'low_time_warning': ['low_time_warning.ogg'],
    'button_tap': ['button_tap.ogg'],
    'purchase': ['purchase.ogg'],
}

MUSIC_TRACKS = {
    'menu': 'menu_theme.ogg',
    'gameplay': 'gameplay_theme.ogg',
}


def _log_audio_problem(message):
    """لاگ بدون وابستگی سخت به Kivy (این ماژول بدون Kivy هم import می‌شود)."""
    try:
        from kivy.logger import Logger
        Logger.warning('LaserRicochet: audio: %s', message)
    except Exception:  # noqa: BLE001
        pass


class AudioManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, settings=None, audio_dir=DEFAULT_AUDIO_DIR):
        if self._initialized:
            return
        self._initialized = True
        self.settings = settings
        self.audio_dir = audio_dir
        self._sfx_cache = {}
        self._music_sound = None
        self._current_music_key = None

    @classmethod
    def _reset_instance_for_testing(cls):
        cls._instance = None

    def bind_settings(self, settings):
        """طبق فاز۵: sound_enabled/music_enabled از SettingsManager از
        این‌جا واقعاً خونده می‌شه -- قبلاً placeholder بدون‌مصرف بود."""
        self.settings = settings

    def _resolve_path(self, relative_path):
        return os.path.join(self.audio_dir, relative_path)

    def _load(self, relative_path):
        full_path = self._resolve_path(relative_path)
        if full_path in self._sfx_cache:
            return self._sfx_cache[full_path]
        if SoundLoader is None or not os.path.exists(full_path):
            self._sfx_cache[full_path] = None
            return None
        try:
            sound = SoundLoader.load(full_path)
        except Exception as exc:  # noqa: BLE001 -- فاز۱۰: ارائه‌دهنده‌ی صدا (SDL2) نباید بازی را بشکند
            _log_audio_problem('load %s failed (%r)' % (relative_path, exc))
            sound = None
        self._sfx_cache[full_path] = sound
        return sound

    @staticmethod
    def _safe_play(sound, name):
        try:
            sound.play()
            return True
        except Exception as exc:  # noqa: BLE001
            _log_audio_problem('play %s failed (%r)' % (name, exc))
            return False

    def pick_variant(self, name):
        """فقط انتخاب فایل -- بدون بارگذاری/پخش. جدا نگه داشته شده تا
        بدون نیاز به SoundLoader واقعی هم قابل‌تست باشه."""
        variants = SFX_VARIANTS.get(name)
        if not variants:
            return None
        return random.choice(variants)

    def play_sfx(self, name):
        if self.settings is not None and not self.settings.sound_enabled:
            return
        chosen = self.pick_variant(name)
        if chosen is None:
            return
        sound = self._load(chosen)
        if sound is not None:
            self._safe_play(sound, chosen)

    def play_music(self, key):
        if self._current_music_key == key:
            return  # از نو شروع نکن اگه همون آهنگ داره پخش می‌شه
        self.stop_music()
        self._current_music_key = key
        if self.settings is not None and not self.settings.music_enabled:
            return  # وضعیت ثبت شد؛ چون خاموشه واقعاً پخش نمی‌کنیم
        track = MUSIC_TRACKS.get(key)
        if not track:
            return
        sound = self._load(track)
        if sound is not None:
            try:
                sound.loop = True
            except Exception as exc:  # noqa: BLE001
                _log_audio_problem('loop flag on %s failed (%r)' % (track, exc))
            if self._safe_play(sound, track):
                self._music_sound = sound

    def stop_music(self):
        if self._music_sound is not None:
            try:
                self._music_sound.stop()
            except Exception as exc:  # noqa: BLE001
                _log_audio_problem('stop music failed (%r)' % (exc,))
            self._music_sound = None

    def on_music_setting_changed(self):
        """SettingsScreen بعد از toggle_music صدا می‌زنه -- تا اثرش
        بلافاصله دیده بشه، نه فقط دفعه‌ی بعدی که play_music صدا زده
        می‌شه."""
        if self.settings is None:
            return
        if not self.settings.music_enabled:
            self.stop_music()
        elif self._current_music_key is not None:
            key = self._current_music_key
            self._current_music_key = None  # تا play_music زیر واقعاً اجرا کنه، نه early-return کنه
            self.play_music(key)
