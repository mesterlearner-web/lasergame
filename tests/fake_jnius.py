"""
tests/fake_jnius.py  (فاز ۸ -- فقط تست)

یک `autoclass` ساختگی که کلاس‌های اندرویدِ مورد استفاده‌ی NotificationManager را شبیه‌سازی
و *هر فراخوانی* را به‌ترتیب ثبت می‌کند، تا ترتیب و آرگومان دقیق فراخوانی‌های JNI بدون گوشی
تست شود. ثابت‌ها مقدار واقعی اندروید را دارند.

دامنه‌ی صادقانه: صحت *فراخوانی‌های ما* را می‌سنجد؛ رفتار واقعی اندروید/PyJNIus را نه.
"""
FLAG_IMMUTABLE = 0x04000000
FLAG_UPDATE_CURRENT = 0x08000000
RTC_WAKEUP = 0
PACKAGE = 'com.laserricochet.laserricochet'


class FakePendingIntent:
    def __init__(self, request_code, intent, flags):
        self.request_code, self.intent, self.flags = request_code, intent, flags
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


class FakeIntent:
    def __init__(self):
        self.component = None
        self.extras = {}

    def setClassName(self, package, class_name):
        self.component = (package, class_name)

    def putExtra(self, key, value):
        self.extras[key] = value


class FakeAlarmService:
    def __init__(self, jni):
        self._jni = jni

    def setAndAllowWhileIdle(self, alarm_type, trigger_ms, pending):
        self._jni._maybe_fail('setAndAllowWhileIdle')
        self._jni.alarms.append(('set', alarm_type, trigger_ms, pending))

    def cancel(self, pending):
        self._jni._maybe_fail('cancel')
        self._jni.alarms.append(('cancel', pending))


class FakeActivity:
    def __init__(self, jni):
        self._jni = jni

    def getPackageName(self):
        return PACKAGE

    def getSystemService(self, name):
        self._jni.service_requests.append(name)
        return FakeAlarmService(self._jni)


class FakeJNI:
    """jni.autoclass برای تزریق به NotificationManager(autoclass=jni.autoclass)."""

    def __init__(self, receiver_present=True, sdk=34, fail_on=None, missing_classes=()):
        self.receiver_present = receiver_present
        self.sdk = sdk
        self.fail_on = fail_on
        self.missing_classes = set(missing_classes)
        self.alarms = []             # ('set', type, ms, pending) / ('cancel', pending)
        self.pending_intents = []
        self.service_requests = []
        self.class_lookups = []
        self.activity = FakeActivity(self)

    def _maybe_fail(self, what):
        if self.fail_on == what:
            raise RuntimeError(f'simulated JNI failure in {what}')

    def autoclass(self, name):
        from core.notification_manager import RECEIVER_CLASS_NAME
        self.class_lookups.append(name)
        if name in self.missing_classes or (name == RECEIVER_CLASS_NAME and not self.receiver_present):
            raise Exception(f'class not found: {name}')
        jni = self

        if name == 'android.app.AlarmManager':
            return type('AlarmManager', (), {'RTC_WAKEUP': RTC_WAKEUP})
        if name == 'android.app.PendingIntent':
            def get_broadcast(context, request_code, intent, flags):
                jni._maybe_fail('getBroadcast')
                pending = FakePendingIntent(request_code, intent, flags)
                jni.pending_intents.append(pending)
                return pending
            return type('PendingIntent', (), {'FLAG_IMMUTABLE': FLAG_IMMUTABLE,
                                              'FLAG_UPDATE_CURRENT': FLAG_UPDATE_CURRENT,
                                              'getBroadcast': staticmethod(get_broadcast)})
        if name == 'android.content.Intent':
            return FakeIntent
        if name == 'android.content.Context':
            return type('Context', (), {'ALARM_SERVICE': 'alarm'})
        if name == 'org.kivy.android.PythonActivity':
            return type('PythonActivity', (), {'mActivity': jni.activity})
        if name == 'android.os.Build$VERSION':
            return type('VERSION', (), {'SDK_INT': jni.sdk})
        if name == RECEIVER_CLASS_NAME:
            return type('ReminderReceiver', (), {})
        raise Exception(f'FakeJNI: unexpected class lookup {name!r}')
