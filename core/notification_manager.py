"""
core/notification_manager.py  (فاز ۷، بازسازی فاز ۸)

طبق فایل مرجع بخش ۵.۲۰:
- «NotificationManager._init_android: self.AlarmManager = autoclass
  ('android.app.AlarmManager') اضافه می‌شه.»
- «PendingIntent باید FLAG_IMMUTABLE رو هم OR بزنه (الزام اندروید۱۲+):
  FLAG_IMMUTABLE | FLAG_UPDATE_CURRENT.»

⚠️ اصلاح صادقانه‌ی فاز۸: نسخه‌ی فاز۷ روی اندروید فقط flagها را حساب می‌کرد و بی‌آن‌که
هیچ Intent/AlarmManager‌ای صدا بزند `{'scheduled': True}` برمی‌گرداند -- یعنی روی گوشی
گزارش موفقیت می‌داد ولی هیچ اعلانی زمان‌بندی نمی‌شد. حالا:

  Python (این فایل)            Java (native/ -- استیج‌شده)
  ─────────────────            ───────────────────────────
  AlarmManager.setAndAllow-    ReminderReceiver (BroadcastReceiver) وقتی alarm
  WhileIdle(PendingIntent  ──▶ بیدار شد، NotificationChannel + Notification را
  .getBroadcast(...))          می‌سازد و نشان می‌دهد؛ حتی اگر پروسه‌ی بازی مرده باشد.

چرا Java لازم است: PyJNIus فقط می‌تواند کلاس‌های *موجود* را صدا بزند؛ وقتی بازی بسته
است (دقیقاً زمانی که اعلان معنا دارد) هیچ کد پایتونی نیست که alarm را بگیرد. گیرنده
باید یک کلاس جاوای ثبت‌شده در مانیفست باشد.

حالت‌های نتیجه‌ی schedule (همیشه دیکشنری، هیچ‌وقت Exception برای شرایط پلتفرم):
  not_android       -- دسکتاپ/تست؛ عادی است.
  receiver_missing  -- روی اندروید ولی کلاس جاوا داخل APK نیست (بیلد پایه، قبل از فعال‌سازی
                       native/)؛ *عمداً* scheduled=False تا دروغ نگوییم.
  android_error     -- استثنای JNI/سیستم‌عامل (متن خطا در 'error').
  invalid_delay / already_full -- ورودی نامعتبر / چیزی برای اعلان نیست.

متن اعلان *خام* (shape-نشده) به جاوا می‌رود: TextView بومی اندروید خودش حروف فارسی را
درست می‌چسباند و راست‌چین می‌کند؛ shape() اینجا متن را خراب می‌کرد (فقط برای Kivy است).

مثل بقیه‌ی پروژه، منطق «چه اعلانی، کِی» (compute_*) کاملاً جدا از فراخوانی سیستم‌عامل و
مستقل از Kivy نگه داشته شده، و فراخوانی‌های JNI/مجوز تزریق‌پذیرند تا ترتیب و آرگومان‌ها
بدون گوشی واقعی تست شوند (tests/test_build.py).
"""
import time

try:
    from kivy.utils import platform
except Exception:  # pragma: no cover -- در sandbox بدون Kivy نصب نمی‌شه؛
    # توابع compute_* (منطق خالص زیر) بدون این import هم کامل قابل‌تست‌ان.
    platform = 'unknown'

#: طبق بخش۵.۲۰ -- هر پیام باید از قبل مشخص باشه، نه در لحظه‌ی schedule
#: ساخته بشه (تا متن‌ها یک‌جا قابل‌بازبینی/ترجمه باشن).
NOTIFICATION_MESSAGES = {
    'energy_full': ('انرژیت پر شد!', 'وقتشه برگردی و چند مرحله‌ی دیگه رو کامل کنی.'),
    'comeback': ('دلمون برات تنگ شده!', 'چند مرحله‌ی جدید منتظرتن.'),
    'daily_reward': ('جایزه‌ی روزانه‌ات آماده‌ست', 'وارد شو و استریکت رو از دست نده!'),
    'weekly_challenge_ending': ('چالش هفتگی داره تموم می‌شه', 'وقت داری امتیازت رو تکمیل کنی.'),
}

DEFAULT_COMEBACK_DELAY_HOURS = 20.0

#: کلاس جاوای گیرنده -- باید دقیقاً با native/android/java/... و مانیفست یکی باشد.
RECEIVER_CLASS_NAME = 'org.laserricochet.notify.ReminderReceiver'

#: هر نوع اعلان یک requestCode ثابت دارد: schedule دوباره‌ی همان نوع، alarm قبلی را
#: *جایگزین* می‌کند (FLAG_UPDATE_CURRENT) و cancel همان را پیدا می‌کند -- نه دو alarm.
REQUEST_CODES = {
    'energy_full': 7101,
    'comeback': 7102,
    'daily_reward': 7103,
    'weekly_challenge_ending': 7104,
}

#: POST_NOTIFICATIONS مجوز زمان‌اجرا فقط از اندروید ۱۳ (API 33) است.
_RUNTIME_NOTIFICATION_PERMISSION_API = 33
_POST_NOTIFICATIONS = 'android.permission.POST_NOTIFICATIONS'


def compute_energy_full_delay_seconds(energy_manager, now=None):
    """چند ثانیه‌ی دیگه انرژی پر می‌شه -- None اگه همین الان پره (چیزی
    برای اعلان‌دادن نیست). مستقل از Kivy؛ فقط از EnergyManager
    (فاز۴) که خودش قبلاً کامل تست شده استفاده می‌کنه."""
    now = now if now is not None else time.time()
    seconds = energy_manager.seconds_until_full(now)
    return seconds if seconds > 0 else None


def compute_comeback_delay_seconds(hours=DEFAULT_COMEBACK_DELAY_HOURS):
    return hours * 3600.0


class NotificationManager:
    def __init__(self, autoclass=None, platform_name=None, clock=None, permission_requester=None):
        """autoclass/platform_name/clock/permission_requester فقط برای تست تزریق می‌شوند؛
        در اجرای واقعی همه‌شان None‌اند و از jnius/Kivy/ساعت سیستم/p4a گرفته می‌شوند."""
        self._android_ready = False
        self._receiver_available = False
        self._autoclass = None
        self._clock = clock or time.time
        self._permission_requester = permission_requester
        self.AlarmManager = None
        self.PendingIntent = None
        if (platform_name or platform) == 'android':
            self._init_android(autoclass)

    def _init_android(self, autoclass=None):
        try:
            if autoclass is None:
                from jnius import autoclass
            self._autoclass = autoclass
            # طبق بخش۵.۲۰ -- دقیقاً همین کلاس‌ها.
            self.AlarmManager = autoclass('android.app.AlarmManager')
            self.PendingIntent = autoclass('android.app.PendingIntent')
            self._android_ready = True
        except Exception:
            # هر خطایی اینجا (pyjnius نصب نیست، ...) نباید کل اپ رو بترکونه --
            # فقط اعلان‌ها غیرفعال می‌مونن.
            self._android_ready = False
            return
        self._receiver_available = self._probe_receiver()

    def _probe_receiver(self):
        """آیا کلاس جاوای گیرنده داخل APK هست؟ (فقط وقتی native/ فعال شده باشد)"""
        try:
            self._autoclass(RECEIVER_CLASS_NAME)
            return True
        except Exception:
            return False

    @property
    def is_android_ready(self):
        return self._android_ready

    @property
    def is_receiver_available(self):
        return self._receiver_available

    @property
    def can_schedule(self):
        return self._android_ready and self._receiver_available

    def _pending_intent_flags(self):
        """طبق بخش۵.۲۰ -- الزام اندروید۱۲+: FLAG_IMMUTABLE باید با
        FLAG_UPDATE_CURRENT ترکیب (OR) بشه، نه فقط یکی از این دو."""
        return self.PendingIntent.FLAG_IMMUTABLE | self.PendingIntent.FLAG_UPDATE_CURRENT

    def _activity(self):
        return self._autoclass('org.kivy.android.PythonActivity').mActivity

    def _build_pending_intent(self, key):
        """Intent صریح (با نام کلاس -- نه intent-filter عمومی) به گیرنده‌ی خودمان. همه‌ی
        extraها رشته‌اند: putExtra(String, int/long) در PyJNIus می‌تواند overload اشتباه
        انتخاب کند، ولی putExtra(String, String) بی‌ابهام است؛ شناسه‌ی عددی اعلان را خود
        جاوا از key می‌سازد."""
        activity = self._activity()
        intent = self._autoclass('android.content.Intent')()
        intent.setClassName(activity.getPackageName(), RECEIVER_CLASS_NAME)
        title, text = NOTIFICATION_MESSAGES[key]
        intent.putExtra('key', key)
        intent.putExtra('title', title)
        intent.putExtra('text', text)
        pending = self.PendingIntent.getBroadcast(
            activity, REQUEST_CODES[key], intent, self._pending_intent_flags())
        return activity, pending

    def _alarm_service(self, activity):
        context_cls = self._autoclass('android.content.Context')
        return activity.getSystemService(context_cls.ALARM_SERVICE)

    def schedule(self, key, delay_seconds):
        """در دسترس‌بودن نتیجه رو با یک دیکشنری ساختاریافته گزارش
        می‌کنه (نه Exception) -- چون «اندروید واقعی نیست» یک خطای
        برنامه‌نویسی نیست، یک وضعیت پلتفرم عادیه."""
        if key not in NOTIFICATION_MESSAGES:
            raise ValueError(f"نوع اعلان ناشناخته: {key!r}")
        if delay_seconds is None or delay_seconds <= 0:
            return {'scheduled': False, 'reason': 'invalid_delay', 'key': key}
        if not self._android_ready:
            return {'scheduled': False, 'reason': 'not_android', 'key': key,
                    'delay_seconds': delay_seconds}
        if not self._receiver_available:
            return {'scheduled': False, 'reason': 'receiver_missing', 'key': key,
                    'delay_seconds': delay_seconds}
        try:
            activity, pending = self._build_pending_intent(key)
            trigger_ms = int((self._clock() + delay_seconds) * 1000)
            # غیردقیق عمداً: یادآوری «برگرد بازی کنی» به دقت میلی‌ثانیه نیاز ندارد، و
            # نسخه‌ی غیردقیق مجوز SCHEDULE_EXACT_ALARM نمی‌خواهد (که در buildozer.spec هم
            # عمداً نیست). AllowWhileIdle: در Doze هم (با تأخیر مجاز) بیدار می‌شود.
            self._alarm_service(activity).setAndAllowWhileIdle(
                self.AlarmManager.RTC_WAKEUP, trigger_ms, pending)
        except Exception as exc:
            return {'scheduled': False, 'reason': 'android_error', 'key': key, 'error': repr(exc)}
        return {'scheduled': True, 'key': key, 'delay_seconds': delay_seconds,
                'trigger_at_ms': trigger_ms}

    def cancel(self, key):
        """alarm زمان‌بندی‌شده را لغو می‌کند. بدون این، با برگشتن بازیکن به بازی
        «انرژیت پر شد!» *بعد از* شروع بازی هم می‌آمد -- اعلان کهنه. الگوی استاندارد:
        هنگام خروج schedule، هنگام ورود cancel_all."""
        if key not in NOTIFICATION_MESSAGES:
            raise ValueError(f"نوع اعلان ناشناخته: {key!r}")
        if not self.can_schedule:
            return {'cancelled': False, 'reason': 'not_available', 'key': key}
        try:
            activity, pending = self._build_pending_intent(key)
            self._alarm_service(activity).cancel(pending)
            pending.cancel()
        except Exception as exc:
            return {'cancelled': False, 'reason': 'android_error', 'key': key, 'error': repr(exc)}
        return {'cancelled': True, 'key': key}

    def cancel_all(self):
        return {key: self.cancel(key) for key in NOTIFICATION_MESSAGES}

    def request_permission(self):
        """اندروید ۱۳+ (API 33): بدون مجوز زمان‌اجرای POST_NOTIFICATIONS هیچ اعلانی نشان
        داده نمی‌شود (فقط داخل مانیفست بودن کافی نیست). فقط وقتی می‌پرسیم که واقعاً
        می‌توانیم اعلان بدهیم؛ درخواست مجوزی که قابلیتش در APK نیست (receiver_missing)
        فقط بازیکن را بی‌دلیل اذیت می‌کند. True یعنی درخواست ارسال شد."""
        if not self.can_schedule:
            return False
        try:
            sdk = self._autoclass('android.os.Build$VERSION').SDK_INT
            if sdk < _RUNTIME_NOTIFICATION_PERMISSION_API:
                return False
            requester = self._permission_requester
            if requester is None:
                from android.permissions import request_permissions as requester
            requester([_POST_NOTIFICATIONS])
        except Exception:
            return False
        return True

    def schedule_energy_full(self, energy_manager, now=None):
        delay = compute_energy_full_delay_seconds(energy_manager, now)
        if delay is None:
            return {'scheduled': False, 'reason': 'already_full', 'key': 'energy_full'}
        return self.schedule('energy_full', delay)

    def schedule_comeback_reminder(self, hours=DEFAULT_COMEBACK_DELAY_HOURS):
        return self.schedule('comeback', compute_comeback_delay_seconds(hours))
