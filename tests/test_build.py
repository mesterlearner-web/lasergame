"""
tests/test_build.py  (فاز ۸)

تست‌های بیلد و بسته‌بندی که بدون اندروید/Kivy/شبکه قابل‌اجرا هستند. دو دسته:
  * مثبت: پروژه‌ی واقعی همه‌ی قواعد را برآورده می‌کند.
  * منفی (مهم‌تر): ورودی ساختگیِ *خراب* دقیقاً همان خطا را می‌دهد. تستی که فقط سبز
    می‌شود ثابت نمی‌کند چیزی را می‌سنجد؛ آزمون جهش فاز۸ نشان داد چند بررسی بدون
    تست منفی اصلاً خراب‌شدن را نمی‌دیدند.

اجرا:  python tests/test_build.py
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))

from tools import font_coverage, preflight  # noqa: E402

passed = 0
failed = 0
skipped = 0
_tmp_dirs = []


def check(name, condition, detail=''):
    global passed, failed
    if condition:
        passed += 1
        print(f"  OK   {name}")
    else:
        failed += 1
        print(f"  FAIL {name}  {detail}")


def skip(name, reason):
    global skipped
    skipped += 1
    print(f"  SKIP {name}  ({reason})")


def section(title):
    print(f"\n=== {title} ===")


def make_project(files):
    root = tempfile.mkdtemp(prefix='lr_proj_')
    _tmp_dirs.append(root)
    for relative, content in files.items():
        path = os.path.join(root, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(content)
    return root


def spec_with(changes=None, remove=()):
    spec = preflight.load_spec()
    for key, value in (changes or {}).items():
        spec['app'][key] = value
    for key in remove:
        spec.remove_option('app', key)
    return spec


def has(problems, needle):
    return any(needle in p for p in problems)


def raises(function, exception_type):
    try:
        function()
    except exception_type:
        return True
    except Exception:  # noqa: BLE001 -- استثنای نوع دیگر یعنی همان نوع انتظار نمی‌رفت
        return False
    return False


DEJAVU = os.path.join(ROOT, 'assets', 'fonts', 'DejaVuSans.ttf')
DEJAVU_BOLD = os.path.join(ROOT, 'assets', 'fonts', 'DejaVuSans-Bold.ttf')
LATIN_ONLY = os.path.join(ROOT, 'tests', 'fixtures', 'latin_only.ttf')

# ====================================================================
section("۱) tools/font_coverage: خواننده‌ی cmap و تعریف «کدپوینت لازم»")

cmap = font_coverage.read_cmap(DEJAVU)
check("cmap فونت DejaVu: حرف ب، ی و نیم‌فاصله (ZWNJ) هست",
      {0x0628, 0x06CC, 0x200C} <= cmap and len(cmap) > 3000, str(len(cmap)))
check("فیکسچر لاتین‌فقط: دقیقاً ۴ کدپوینت (فرمت ۴ و ۱۲ هر دو خوانده می‌شوند)",
      font_coverage.read_cmap(LATIN_ONLY) == {0x20, 0x41, 0x42, 0x1F600})

beh = font_coverage.required_codepoints(['ب'])
check("حرف «ب» -> حرف پایه + هر چهار شکل پیوسته (مجزا/پایانی/آغازی/میانی) لازم است",
      {0x0628, 0xFE8F, 0xFE90, 0xFE91, 0xFE92} <= beh, str(sorted(hex(c) for c in beh)))
check("حرف فارسی «ی» -> اشکال مخصوص فارسی FBFC..FBFF لازم است",
      {0x06CC, 0xFBFC, 0xFBFD, 0xFBFE, 0xFBFF} <= font_coverage.required_codepoints(['ی']))
check("هر متن عربی‌خط -> لیگاچر لام‌الف (U+FEFB) هم لازم است",
      0xFEFB in font_coverage.required_codepoints(['ل']))
check("نیم‌فاصله همیشه لازم است", 0x200C in font_coverage.required_codepoints(['abc']))
check("متن ASCII -> هیچ شکل عربی لازم نیست",
      font_coverage.required_codepoints(['abc']) == {0x61, 0x62, 0x63, 0x200C})
check("کاراکترهای کنترلی (\\n \\t) گلیف لازم ندارند",
      not ({0x09, 0x0A} & font_coverage.required_codepoints(['a\n\tb'])))

ui_strings = font_coverage.collect_ui_strings()
check("رشته‌های UI واقعی جمع‌آوری می‌شوند (متن دکمه‌ی «بازگشت»)", any('بازگشت' in s for s in ui_strings))
check("docstringها جزو متن UI نیستند (حذف شدند)",
      not any('Roboto) هیچ حرف' in s for s in ui_strings))

check("DejaVuSans: همه‌ی گلیف‌های لازم UI را دارد", font_coverage.missing_codepoints(DEJAVU) == [])
check("DejaVuSans-Bold: همه‌ی گلیف‌های لازم UI را دارد", font_coverage.missing_codepoints(DEJAVU_BOLD) == [])
missing = font_coverage.missing_codepoints(LATIN_ONLY, strings=['بازگشت'])
check("(منفی) فونت لاتین‌فقط برای متن فارسی گلیف کم دارد و دقیقاً ب را گزارش می‌کند",
      0x0628 in missing and len(missing) > 10, str(len(missing)))

# ====================================================================
section("۲) utils/fonts: انتخاب و ثبت فونت پیش‌فرض")

from utils import fonts  # noqa: E402

real = fonts.resolve_font_family()
check("پروژه‌ی واقعی: فونت regular و bold موجودند", real is not None and all(os.path.isfile(p) for p in real))
check("regular و bold دو فایل متفاوت‌اند", real is not None and real[0] != real[1])

only_dejavu = make_project({'DejaVuSans.ttf': 'x', 'DejaVuSans-Bold.ttf': 'x'})
check("فقط DejaVu -> DejaVu انتخاب می‌شود",
      os.path.basename(fonts.resolve_font_family(only_dejavu)[0]) == 'DejaVuSans.ttf')
both = make_project({'DejaVuSans.ttf': 'x', 'DejaVuSans-Bold.ttf': 'x',
                     'Vazirmatn-Regular.ttf': 'x', 'Vazirmatn-Bold.ttf': 'x'})
check("اگر Vazirmatn کنارش باشد، اولویت با آن است (ارتقا بدون تغییر کد)",
      os.path.basename(fonts.resolve_font_family(both)[0]) == 'Vazirmatn-Regular.ttf')
no_bold = make_project({'Vazirmatn-Regular.ttf': 'x'})
regular, bold = fonts.resolve_font_family(no_bold)
check("فایل bold نبود -> از regular به‌جایش استفاده می‌شود", regular == bold)
empty = make_project({'README.txt': 'x'})
check("پوشه‌ی بدون فونت -> None", fonts.resolve_font_family(empty) is None)


class FakeLabelBase:
    calls = []

    @classmethod
    def register(cls, name, **kwargs):
        cls.calls.append((name, kwargs))


FakeLabelBase.calls.clear()
check("ثبت با پوشه‌ی بدون فونت: None برمی‌گرداند و به LabelBase دست نمی‌زند",
      fonts.register_default_font(empty, label_base=FakeLabelBase, default_font_name='Roboto') is None
      and FakeLabelBase.calls == [])
family = fonts.register_default_font(both, label_base=FakeLabelBase, default_font_name='Roboto')
name, kwargs = FakeLabelBase.calls[0]
check("ثبت: نام پیش‌فرض Kivy بازنویسی می‌شود (نه یک نام جدید که هیچ ویجتی استفاده نمی‌کند)", name == 'Roboto')
check("ثبت: fn_regular و fn_bold به فایل‌های انتخاب‌شده اشاره می‌کنند",
      kwargs['fn_regular'] == family[0] and kwargs['fn_bold'] == family[1])

# ====================================================================
section("۳) game_logic/back_navigation (منطق خالص)")

from game_logic.back_navigation import ANDROID_BACK_KEY, decide_back_action  # noqa: E402

check("کد کلید Back اندروید در Kivy = 27", ANDROID_BACK_KEY == 27)
check("Back از منوی اصلی -> خروج", decide_back_action('main_menu') == ('exit_app', None))
check("Back بدون صفحه‌ی مشخص -> خروج (ایمن)", decide_back_action(None) == ('exit_app', None))
for screen in ('shop', 'settings', 'profile', 'battle_pass', 'missions', 'level_select', 'sandbox'):
    check(f"Back از «{screen}» -> برگشت به main_menu", decide_back_action(screen) == ('go_back', 'main_menu'))
check("Back از game -> مقصد پیش‌فرض level_select (مثل دکمه‌ی «خروج»)",
      decide_back_action('game') == ('go_back', 'level_select'))
check("صفحه‌ی ناشناخته -> برگشت امن به main_menu، نه کرش", decide_back_action('???') == ('go_back', 'main_menu'))

# ====================================================================
section("۳.۵) utils/persian_text.wrap_logical_text: «اول بشکن، بعد shape کن»")

import random  # noqa: E402

from utils.persian_text import wrap_logical_text  # noqa: E402


def ten_per_char(line):
    return len(line) * 10


check("متن کوتاه که جا می‌شود -> یک خط", wrap_logical_text('aa bb', 100, ten_per_char) == ['aa bb'])
check("شکستن حریصانه", wrap_logical_text('aa bb cc dd', 50, ten_per_char) == ['aa bb', 'cc dd'])
check("ترتیب خطوط = ترتیب خواندن (خط اول با اولین کلمه شروع می‌شود، نه آخرین)",
      wrap_logical_text('one two three four', 80, ten_per_char)[0].startswith('one'))
check("کلمه‌ی بلندتر از عرض: در خط خودش می‌ماند (نه حلقه‌ی بی‌نهایت/حذف)",
      wrap_logical_text('a verylongword b', 40, ten_per_char) == ['a', 'verylongword', 'b'])
check("خط‌شکن صریح حفظ می‌شود", wrap_logical_text('a\nbb cc', 25, ten_per_char) == ['a', 'bb', 'cc'])
check("رشته‌ی خالی -> یک خط خالی", wrap_logical_text('', 100, ten_per_char) == [''])
word = 'می\u200cخواهم'
check("نیم‌فاصله (ZWNJ) جداکننده‌ی کلمه نیست: کلمه وسطش نمی‌شکند",
      wrap_logical_text(f'{word} من', len(word) * 10 + 5, ten_per_char)[0] == word)
persian = 'این یک جمله‌ی نسبتاً طولانی برای آزمودن شکستن خط راست به چپ است'
lines = wrap_logical_text(persian, 200, ten_per_char)
check("جمله‌ی فارسی: چند خط، ترتیب خواندن حفظ، هیچ کلمه‌ای گم یا تکرار نشده",
      len(lines) > 1 and ' '.join(lines) == persian and lines[0].startswith('این'), str(lines))
check("هر خطِ چندکلمه‌ای از عرض بیشتر نیست", all(ten_per_char(l) <= 200 for l in lines if ' ' in l))

rng = random.Random(8)
violations = []
for trial in range(300):
    words = [''.join(rng.choice('abcdefgh') for _ in range(rng.randint(1, 9))) for _ in range(rng.randint(1, 14))]
    text = ' '.join(words)
    width = rng.randint(10, 160)
    out = wrap_logical_text(text, width, ten_per_char)
    if ' '.join(out) != text:
        violations.append(('content', text, width))
    if any(' ' in line and ten_per_char(line) > width for line in out):
        violations.append(('overflow', text, width))
check("ویژگی تصادفی (۳۰۰ متن): محتوا حفظ می‌شود و هیچ خط چندکلمه‌ای سرریز نمی‌کند", not violations, str(violations[:2]))

# ====================================================================
section("۴) core/notification_manager: زمان‌بندی واقعی با JNI ساختگی")

import fake_jnius as fj  # noqa: E402
from core.notification_manager import (DEFAULT_COMEBACK_DELAY_HOURS, NOTIFICATION_MESSAGES,  # noqa: E402
                                       RECEIVER_CLASS_NAME, REQUEST_CODES, NotificationManager)

check("هر نوع اعلان یک requestCode دارد", set(REQUEST_CODES) == set(NOTIFICATION_MESSAGES))
check("requestCodeها یکتا هستند", len(set(REQUEST_CODES.values())) == len(REQUEST_CODES))

default_nm = NotificationManager()
result = default_nm.schedule('comeback', 100.0)
check("(سازگاری با فاز۷) دسکتاپ: not_android با همان فیلدها",
      result == {'scheduled': False, 'reason': 'not_android', 'key': 'comeback', 'delay_seconds': 100.0}, str(result))
check("دسکتاپ: cancel/permission بی‌اثر و بدون استثنا",
      default_nm.cancel('comeback')['cancelled'] is False and default_nm.request_permission() is False)
check("نوع ناشناخته -> ValueError", raises(lambda: default_nm.schedule('bogus', 10), ValueError))
check("cancel با نوع ناشناخته -> ValueError", raises(lambda: default_nm.cancel('bogus'), ValueError))
check("تأخیر نامعتبر -> invalid_delay",
      default_nm.schedule('comeback', 0)['reason'] == 'invalid_delay'
      and default_nm.schedule('comeback', None)['reason'] == 'invalid_delay')

jni = fj.FakeJNI()
nm = NotificationManager(autoclass=jni.autoclass, platform_name='linux')
check("platform=linux حتی با autoclass تزریق‌شده -> اندروید نیست", not nm.is_android_ready)

jni = fj.FakeJNI(missing_classes=('android.app.AlarmManager',))
nm = NotificationManager(autoclass=jni.autoclass, platform_name='android')
check("کلاس AlarmManager نبود -> اندروید-آماده نیست (کرش نمی‌کند)", not nm.is_android_ready)

jni = fj.FakeJNI(receiver_present=False)
nm = NotificationManager(autoclass=jni.autoclass, platform_name='android', clock=lambda: 1000.0)
result = nm.schedule('comeback', 3600)
check("اندروید ولی گیرنده‌ی جاوا در APK نیست -> صادقانه receiver_missing (نه scheduled=True دروغین)",
      nm.is_android_ready and not nm.is_receiver_available and result['scheduled'] is False
      and result['reason'] == 'receiver_missing', str(result))
check("receiver_missing: هیچ alarmی ثبت نشده", jni.alarms == [])

jni = fj.FakeJNI()
nm = NotificationManager(autoclass=jni.autoclass, platform_name='android', clock=lambda: 1000.0)
check("اندروید + گیرنده موجود -> can_schedule", nm.can_schedule)
result = nm.schedule('comeback', 3600)
check("زمان‌بندی موفق: scheduled=True و trigger_at_ms = (clock + delay) * 1000",
      result['scheduled'] and result['trigger_at_ms'] == int((1000.0 + 3600) * 1000), str(result))
kind, alarm_type, trigger_ms, pending = jni.alarms[0]
check("alarm با setAndAllowWhileIdle (غیردقیق -> بدون نیاز به SCHEDULE_EXACT_ALARM)", kind == 'set')
check("نوع alarm = RTC_WAKEUP", alarm_type == fj.RTC_WAKEUP)
check("زمان alarm همان trigger_at_ms است", trigger_ms == result['trigger_at_ms'])
check("سرویس 'alarm' از Activity گرفته شد", jni.service_requests == ['alarm'])
check("PendingIntent.getBroadcast با FLAG_IMMUTABLE | FLAG_UPDATE_CURRENT (الزام اندروید ۱۲+)",
      pending.flags == fj.FLAG_IMMUTABLE | fj.FLAG_UPDATE_CURRENT, hex(pending.flags))
check("requestCode همان کد ثابت این نوع اعلان", pending.request_code == REQUEST_CODES['comeback'])
check("Intent صریح به کلاس گیرنده در بسته‌ی خودِ اپ",
      pending.intent.component == (fj.PACKAGE, RECEIVER_CLASS_NAME), str(pending.intent.component))
title, text = NOTIFICATION_MESSAGES['comeback']
check("extraها: key/title/text و همه str (بدون ابهام overload در PyJNIus)",
      pending.intent.extras == {'key': 'comeback', 'title': title, 'text': text}
      and all(isinstance(v, str) for v in pending.intent.extras.values()), str(pending.intent.extras))
check("متن فارسی *خام* می‌رود (shape نشده -- TextView بومی خودش می‌چسباند)",
      title == 'دلمون برات تنگ شده!')

nm.schedule('comeback', 7200)
check("schedule مجدد همان نوع -> همان requestCode (alarm قبلی جایگزین می‌شود، نه دو alarm)",
      jni.alarms[1][3].request_code == jni.alarms[0][3].request_code)
nm.schedule('energy_full', 600)
check("نوع دیگر -> requestCode دیگر", jni.alarms[2][3].request_code == REQUEST_CODES['energy_full'])


class FakeEnergy:
    def __init__(self, seconds):
        self._seconds = seconds

    def seconds_until_full(self, now):
        return self._seconds


jni = fj.FakeJNI()
nm = NotificationManager(autoclass=jni.autoclass, platform_name='android', clock=lambda: 50.0)
result = nm.schedule_energy_full(FakeEnergy(120), now=0)
check("schedule_energy_full: تأخیر = ثانیه‌های باقی‌مانده تا پر شدن",
      result['scheduled'] and result['delay_seconds'] == 120 and result['key'] == 'energy_full')
check("schedule_energy_full با انرژی پر -> already_full (بدون alarm)",
      nm.schedule_energy_full(FakeEnergy(0), now=0)['reason'] == 'already_full' and len(jni.alarms) == 1)
result = nm.schedule_comeback_reminder()
check(f"یادآوری عمومی پیش‌فرض {DEFAULT_COMEBACK_DELAY_HOURS:g} ساعت دیگر",
      result['delay_seconds'] == DEFAULT_COMEBACK_DELAY_HOURS * 3600)

jni = fj.FakeJNI()
nm = NotificationManager(autoclass=jni.autoclass, platform_name='android')
nm.schedule('comeback', 100)
cancelled = nm.cancel('comeback')
cancel_entries = [e for e in jni.alarms if e[0] == 'cancel']
check("cancel: alarm با همان requestCode لغو و PendingIntent آزاد می‌شود",
      cancelled['cancelled'] and cancel_entries[0][1].request_code == REQUEST_CODES['comeback']
      and cancel_entries[0][1].cancelled is True)
results = nm.cancel_all()
check("cancel_all: هر ۴ نوع لغو می‌شوند", set(results) == set(NOTIFICATION_MESSAGES)
      and all(r['cancelled'] for r in results.values()))

for fail_point in ('getBroadcast', 'setAndAllowWhileIdle'):
    jni = fj.FakeJNI(fail_on=fail_point)
    nm = NotificationManager(autoclass=jni.autoclass, platform_name='android')
    result = nm.schedule('comeback', 100)
    check(f"خطای JNI در {fail_point} -> android_error با متن خطا (نه استثنا، نه کرش)",
          result['scheduled'] is False and result['reason'] == 'android_error' and 'simulated' in result['error'], str(result))
jni = fj.FakeJNI(fail_on='cancel')
check("خطای JNI در cancel -> android_error",
      NotificationManager(autoclass=jni.autoclass, platform_name='android').cancel('comeback')['reason'] == 'android_error')

requests = []
for sdk, expect in ((34, True), (33, True), (32, False), (30, False)):
    jni = fj.FakeJNI(sdk=sdk)
    requests.clear()
    nm = NotificationManager(autoclass=jni.autoclass, platform_name='android',
                             permission_requester=lambda perms: requests.append(list(perms)))
    got = nm.request_permission()
    check(f"مجوز اعلان: SDK {sdk} -> {'درخواست می‌شود' if expect else 'درخواست نمی‌شود (مجوز زمان‌اجرا فقط از ۳۳)'}",
          got is expect and bool(requests) is expect)
check("مجوز اعلان: دقیقاً POST_NOTIFICATIONS درخواست می‌شود",
      NotificationManager(autoclass=fj.FakeJNI(sdk=34).autoclass, platform_name='android',
                          permission_requester=lambda p: requests.append(list(p))).request_permission()
      and requests[-1] == ['android.permission.POST_NOTIFICATIONS'])
requests.clear()
nm = NotificationManager(autoclass=fj.FakeJNI(receiver_present=False).autoclass, platform_name='android',
                         permission_requester=lambda p: requests.append(p))
check("گیرنده نیست -> مجوز نمی‌پرسد (درخواست مجوزِ قابلیتی که در APK نیست، بازیکن را بی‌دلیل اذیت می‌کند)",
      nm.request_permission() is False and requests == [])

# ====================================================================
section("۵) preflight روی پروژه‌ی واقعی")

results = preflight.run_all()
check(f"{len(results)} بررسی preflight تعریف شده", len(results) == 10)
for name, problems in results:
    if problems is None:
        skip(f"preflight: {name}", 'PyYAML نصب نیست')
    else:
        check(f"preflight: {name}", problems == [], '; '.join(problems[:3]))
required = preflight.required_bundle_files()
bundled = preflight.simulate_bundle(preflight.load_spec())
check(f"همه‌ی {len(required)} فایل لازم در APK (شبیه‌سازی) هست", required <= bundled, str(sorted(required - bundled)[:5]))
check("فونت‌ها و مجوز فونت داخل APK می‌روند",
      {'assets/fonts/DejaVuSans.ttf', 'assets/fonts/DejaVuSans-Bold.ttf', 'assets/fonts/LICENSE_DejaVu.txt'} <= bundled)
check("tests/tools/native داخل APK نمی‌روند",
      not any(p.split('/')[0] in ('tests', 'tools', 'native') for p in bundled))
check("مستندات .md داخل APK نمی‌روند", not any(p.endswith('.md') for p in bundled))

# ====================================================================
section("۶) (منفی) هر قانون spec وقتی نقض شود خطا می‌دهد")

base_problems = preflight.check_spec(preflight.load_spec())
check("پایه: spec واقعی بدون مشکل", base_problems == [], str(base_problems))
bidi_pin = 'python3,kivy==2.3.0,pyjnius,android,arabic_reshaper==3.0.0,python-bidi{},six'
cases = [
    ("python-bidi بدون pin", {'requirements': bidi_pin.format('')}, 'python-bidi'),
    ("python-bidi نسخه‌ی Rust (0.6.0)", {'requirements': bidi_pin.format('==0.6.0')}, 'python-bidi'),
    ("six حذف شده", {'requirements': 'python3,kivy==2.3.0,pyjnius,android,arabic_reshaper==3.0.0,python-bidi==0.4.2'}, 'six'),
    ("kivy بدون pin", {'requirements': 'python3,kivy,pyjnius,android,arabic_reshaper==3.0.0,python-bidi==0.4.2,six'}, 'kivy'),
    ("kivent برگشته", {'requirements': 'python3,kivy==2.3.0,kivent_core,arabic_reshaper==3.0.0,python-bidi==0.4.2,six'}, 'kivent'),
    ("arabic_reshaper بدون pin", {'requirements': 'python3,kivy==2.3.0,arabic_reshaper,python-bidi==0.4.2,six'}, 'arabic_reshaper'),
    ("android.api=33", {'android.api': '33'}, 'android.api'),
    ("android.minapi=21", {'android.minapi': '21'}, 'android.minapi'),
    ("archs دوتایی", {'android.archs': 'arm64-v8a, armeabi-v7a'}, 'android.archs'),
    ("p4a روی master", {'p4a.branch': 'master'}, 'متحرک'),
    ("ndk_api > minapi", {'android.ndk_api': '30'}, 'ndk_api'),
    ("accept_sdk_license=False", {'android.accept_sdk_license': 'False'}, 'accept_sdk_license'),
    ("orientation=landscape", {'orientation': 'landscape'}, 'portrait'),
    ("ttf از include_exts حذف", {'source.include_exts': 'py,json,ogg,png'}, 'ttf'),
    ("tests از exclude_dirs حذف", {'source.exclude_dirs': 'tools,bin'}, 'tests'),
    ("POST_NOTIFICATIONS حذف", {'android.permissions': 'VIBRATE,INTERNET'}, 'POST_NOTIFICATIONS'),
    ("add_src بدون hook", {'android.add_src': 'native/android/java'}, 'با هم'),
    ("hook بدون add_src", {'p4a.hook': 'native/p4a_hook.py'}, 'با هم'),
    ("add_src به مسیر ناموجود", {'android.add_src': 'nope/java', 'p4a.hook': 'native/p4a_hook.py'}, 'ناموجود'),
    ("hook به فایل ناموجود", {'android.add_src': 'native/android/java', 'p4a.hook': 'native/nope.py'}, 'ناموجود'),
]
for label, changes, needle in cases:
    check(f"(منفی) {label}", has(preflight.check_spec(spec_with(changes)), needle),
          str(preflight.check_spec(spec_with(changes))))
check("(منفی) android.ndk حذف", has(preflight.check_spec(spec_with(remove=('android.ndk',))), 'android.ndk'))
check("(منفی) p4a.branch حذف", has(preflight.check_spec(spec_with(remove=('p4a.branch',))), 'p4a.branch'))
check("(مثبت) فعال‌سازی صحیح native (هر دو کلید، مسیرهای موجود) خطایی نمی‌دهد",
      preflight.check_spec(spec_with({'android.add_src': 'native/android/java',
                                      'p4a.hook': 'native/p4a_hook.py'})) == [])

# ====================================================================
section("۷) (منفی) همخوانی requirements.txt، importها، بسته‌بندی، dp، پایتون ۳.۱۱")

spec = preflight.load_spec()
proj = make_project({'requirements.txt': 'kivy==2.3.0\narabic-reshaper==3.0.0\npython-bidi==0.4.2\nsix\n'})
check("(مثبت) requirements.txt همخوان -> خطایی ندارد", preflight.check_requirements_txt(spec, proj) == [])
proj = make_project({'requirements.txt': 'kivy==2.2.0\narabic-reshaper==3.0.0\npython-bidi==0.4.2\nsix\n'})
check("(منفی) pin ناهم‌خوان kivy بین spec و requirements.txt", has(preflight.check_requirements_txt(spec, proj), 'ناهم‌خوان'))
proj = make_project({'requirements.txt': 'kivy==2.3.0\narabic-reshaper==3.0.0\nsix\n'})
check("(منفی) python-bidi در requirements.txt نیست", has(preflight.check_requirements_txt(spec, proj), 'python-bidi'))
proj = make_project({'requirements.txt': 'kivy==2.3.0\narabic-reshaper==3.0.0\npython-bidi==0.4.2\nsix\nnumpy\n'})
check("(منفی) numpy فقط در requirements.txt", has(preflight.check_requirements_txt(spec, proj), 'numpy'))

proj = make_project({'main.py': 'import numpy\n', 'ui/__init__.py': '', 'ui/a.py': 'import os\nfrom kivy.app import App\n'})
problems = preflight.check_third_party_imports(spec, proj)
check("(منفی) import numpy که هیچ requirement ندارد", has(problems, 'numpy'), str(problems))
check("(مثبت) import kivy با requirement موجود خطا نمی‌دهد", not has(problems, 'kivy'))
no_kivy = spec_with({'requirements': 'python3,arabic_reshaper==3.0.0,python-bidi==0.4.2,six'})
check("(منفی) import kivy وقتی kivy در requirements نیست", has(preflight.check_third_party_imports(no_kivy, proj), 'kivy'))
proj = make_project({'main.py': 'from jnius import autoclass\n'})
check("(منفی) import jnius بدون pyjnius",
      has(preflight.check_third_party_imports(spec_with({'requirements': 'python3,kivy==2.3.0,six'}), proj), 'pyjnius'))

assets_proj = make_project({
    'main.py': 'x = 1\n', 'assets/a.json': '{}', 'assets/b.webp': 'x', 'assets/audio/README.md': 'doc',
    'tests/t.py': 'x = 1\n', 'tools/x.py': 'x = 1\n', '.hidden/h.py': 'x = 1\n', 'data/save.db': 'x',
    'core/__init__.py': '', 'core/c.py': 'x = 1\n'})
sim = preflight.simulate_bundle(spec, assets_proj)
check("شبیه‌سازی: json و py داخل، tests/tools/پوشه‌ی پنهان بیرون",
      {'main.py', 'assets/a.json', 'core/c.py'} <= sim
      and not ({'tests/t.py', 'tools/x.py', '.hidden/h.py'} & sim), str(sorted(sim)))
problems = preflight.check_bundle(spec, assets_proj)
check("(منفی) asset با پسوند ثبت‌نشده (.webp) بی‌صدا از APK بیرون می‌ماند -> گزارش می‌شود",
      has(problems, 'assets/b.webp'), str(problems))
check("README.md و save.db جزو «لازم» نیستند", not has(problems, 'README') and not has(problems, 'save.db'))

bundle_dir = make_project({'main.py': 'x', 'core/c.py': 'x', 'tests/t.py': 'x'})
problems = preflight.verify_bundle_dir(bundle_dir, assets_proj)
check("(منفی) تطبیق با خروجی واقعی: فایل لازم ناموجود", has(problems, 'assets/a.json'), str(problems))
check("(منفی) تطبیق با خروجی واقعی: tests/ نباید باشد", has(problems, 'tests/t.py'))
check("(منفی) پوشه‌ی بیلد ناموجود پیام روشن می‌دهد", has(preflight.verify_bundle_dir('/nonexistent/x'), 'پیدا نشد'))

ui_proj = make_project({
    'ui/__init__.py': '',
    'ui/screens/__init__.py': '',
    'ui/screens/x.py': ('from kivy.metrics import dp\n'
                        'a = Label(height=64)\n'
                        'b = Label(height=dp(64))\n'
                        'c = Label(size=(10, 20), width=0)\n'
                        'd = Rectangle(size=(10, 10))\n'
                        'e = self.top - 60\n'
                        'f = self.top - dp(60)\n'
                        'g = kwargs.setdefault("height", 50)\n'
                        'h = BoxLayout(padding=(12, 8), spacing=0)\n')})
problems = preflight.check_raw_pixel_sizes(ui_proj)
check("(منفی) height=64 خام گرفته می‌شود", has(problems, 'height=64'), str(problems))
check("(منفی) size=(10, 20) خام گرفته می‌شود", has(problems, 'size=(10, 20)'))
check("(منفی) افست موقعیت self.top - 60 گرفته می‌شود", has(problems, 'self.top - 60'))
check("(منفی) setdefault('height', 50) گرفته می‌شود", has(problems, "setdefault('height', 50)"))
check("(منفی) padding=(12, 8) خام گرفته می‌شود", has(problems, 'padding=(12, 8)'))
check("(مثبت) dp(64)، صفر، دستور گرافیکی و dp در افست گرفته نمی‌شوند",
      not has(problems, 'dp(64)') and not has(problems, 'width=0') and not has(problems, 'Rectangle')
      and not has(problems, 'dp(60)') and not has(problems, 'spacing=0'), str(problems))

py_proj = make_project({
    'good.py': 'def f(x):\n    match x:\n        case 1:\n            return f"{x!r:>5}"\n    return None\n',
    'bad.py': "d = {'k': 1}\nprint(f\"{d['k']} and {d[\"k\"]}\")\n"})
problems = preflight.check_python311_compat(py_proj)
check("(منفی) f-string با نقل‌قول تودرتوی هم‌نوع (فقط ۳.۱۲+) گرفته می‌شود", has(problems, 'bad.py'), str(problems))
check("(مثبت) match و f-string معمولی (سازگار با ۳.۱۱) گرفته نمی‌شود", not has(problems, 'good.py'))

font_proj = make_project({
    'assets/fonts/DejaVuSans.ttf': 'placeholder',
    'ui/__init__.py': '', 'ui/s.py': "T = 'بازگشت'\n"})
shutil.copy(LATIN_ONLY, os.path.join(font_proj, 'assets', 'fonts', 'DejaVuSans.ttf'))
problems = preflight.check_fonts(font_proj)
check("(منفی) فونتِ بدون گلیف فارسی گرفته می‌شود", has(problems, 'گلیف'), str(problems))
check("(منفی) نبودن فایل مجوز فونت گرفته می‌شود", has(problems, 'مجوز'))
check("(منفی) پوشه‌ی فونتِ خالی گرفته می‌شود",
      has(preflight.check_fonts(make_project({'assets/fonts/README.txt': 'x'})), 'هیچ فونت'))

good_level = '{"level_id": %d, "targets": [{"x": 1}], "time_limit": 60, "laser_start": {"x": 1}}'
three = make_project({f'assets/levels/level_{i:03d}.json': good_level % i for i in (1, 2, 3)})
check("(مثبت) مراحل کمپین پیوسته و سالم -> بدون مشکل", preflight.check_campaign_levels(three, total_levels=3) == [])
check("(منفی) فایل مرحله ناموجود", has(preflight.check_campaign_levels(three, total_levels=4), 'level_004.json'))
check("(منفی) فایل اضافه/نام نامعتبر", has(preflight.check_campaign_levels(three, total_levels=2), 'level_003.json'))
broken = make_project({'assets/levels/level_001.json': good_level % 1,
                       'assets/levels/level_002.json': '{not json',
                       'assets/levels/level_003.json': good_level % 9,
                       'assets/levels/level_004.json': '{"level_id": 4, "targets": [], "time_limit": 60, "laser_start": {}}',
                       'assets/levels/level_005.json': '{"level_id": 5, "targets": [{"x": 1}], "time_limit": 0, "laser_start": {}}',
                       'assets/levels/level_006.json': '{"level_id": 6, "targets": [{"x": 1}], "time_limit": 9}'})
problems = preflight.check_campaign_levels(broken, total_levels=6)
check("(منفی) JSON نامعتبر", has(problems, 'level_002.json: JSON نامعتبر'), str(problems))
check("(منفی) level_id با نام فایل نمی‌خواند", has(problems, 'level_003.json: level_id'))
check("(منفی) مرحله‌ی بدون هدف", has(problems, 'level_004.json: هیچ هدفی'))
check("(منفی) time_limit صفر", has(problems, 'level_005.json: time_limit'))
check("(منفی) نبودن laser_start", has(problems, 'level_006.json: laser_start'))
check("(منفی) پوشه‌ی assets/levels ناموجود", has(preflight.check_campaign_levels(make_project({'x.txt': 'x'})), 'وجود ندارد'))

# ====================================================================
section("۸) workflow (ساختار + قواعد ایمنی)")

try:
    import yaml
except ImportError:
    yaml = None
if yaml is None:
    skip("بررسی‌های workflow", 'PyYAML نصب نیست')
else:
    with open(os.path.join(ROOT, '.github', 'workflows', 'build-apk.yml'), encoding='utf-8') as handle:
        text = handle.read()
    doc = yaml.safe_load(text)
    jobs = doc['jobs']
    check("سه job: preflight، build، release", set(jobs) == {'preflight', 'build', 'release'})
    check("build به preflight وابسته است", jobs['build']['needs'] == 'preflight')
    check("release به build وابسته و فقط روی tag", jobs['release']['needs'] == 'build'
          and "refs/tags/v" in jobs['release']['if'])
    check("release تنها job با مجوز نوشتن است",
          jobs['release']['permissions'] == {'contents': 'write'} and doc['permissions'] == {'contents': 'read'})
    matrix = jobs['build']['strategy']['matrix']['include']
    profiles = {m['profile']: m for m in matrix}
    check("دو پروفایل: pinned (مبنا) و latest (آزمایشی)", set(profiles) == {'pinned', 'latest'})
    check("فقط latest آزمایشی است و شکستش workflow را قرمز نمی‌کند",
          profiles['pinned']['experimental'] is False and profiles['latest']['experimental'] is True
          and jobs['build']['continue-on-error'] == '${{ matrix.experimental }}')
    check("fail-fast خاموش (شکست یک پروفایل دیگری را لغو نمی‌کند)", jobs['build']['strategy']['fail-fast'] is False)
    check("پروفایل pinned: buildozer و Cython دقیقاً pin",
          profiles['pinned']['buildozer_spec'] == 'buildozer==1.5.0' and '==' in profiles['pinned']['cython_spec'])
    check("پایتون ۳.۱۱ در هر دو job (نسخه‌ی پایتون داخل APK)", text.count("python-version: '3.11'") == 2)
    check("timeout برای هر دو job سنگین تعریف شده", all('timeout-minutes' in jobs[j] for j in ('preflight', 'build')))
    check("preflight هر سه مجموعه تست + گزارش را اجرا می‌کند",
          all(s in text for s in ('tests/test_core.py', 'tests/test_build.py', 'tests/test_ui_smoke.py',
                                  'tests/test_phase9.py', 'tests/test_phase10.py', 'tools/preflight.py')))
    check("بیلد با shell: bash (pipefail) تا شکست buildozer از زیر tee رد نشود",
          'shell: bash' in text and '| tee build-' in text)
    check("«yes | buildozer» نیست (با pipefail به SIGPIPE می‌خورد)", 'yes |' not in text)
    check("لاگ بیلد همیشه آپلود می‌شود (if: always())",
          "name: Upload build log\n        if: always()" in text)
    check("مرحله‌ی تطبیق bundle اطلاعاتی است (APK سالم را بخاطر فرض مسیر از دست نمی‌دهیم)",
          'continue-on-error: true\n        run: python tools/preflight.py --bundle' in text)
    check("کش دو مرحله‌ای: کامل بعد از موفقیت، فقط SDK/NDK بعد از شکست",
          'actions/cache/restore@v4' in text and text.count('actions/cache/save@v4') == 2)

    bad_dir = make_project({'.github/workflows/build-apk.yml':
                            "on: {push: {}}\njobs:\n  build:\n    runs-on: x\n    steps:\n"
                            "      - run: buildozer android debug | tee build.log\n"})
    problems = preflight.check_workflow(bad_dir)
    check("(منفی) workflow بدون preflight/workflow_dispatch گرفته می‌شود",
          has(problems, 'preflight') and has(problems, 'workflow_dispatch'), str(problems))
    bad_dir = make_project({'.github/workflows/build-apk.yml':
                            "on: {push: {}, workflow_dispatch: {}}\njobs:\n  preflight:\n    runs-on: x\n    steps: []\n"
                            "  build:\n    needs: preflight\n    runs-on: x\n    steps:\n"
                            "      - run: yes | buildozer android debug | tee build.log\n"})
    problems = preflight.check_workflow(bad_dir)
    check("(منفی) tee بدون pipefail و yes | گرفته می‌شود", has(problems, 'pipefail') and has(problems, 'yes |'), str(problems))

# ====================================================================
section("۹) native/: گیرنده‌ی جاوا و hook مانیفست")

java_file = os.path.join(ROOT, 'native', 'android', 'java', 'org', 'laserricochet', 'notify', 'ReminderReceiver.java')
stub_files = [os.path.join(d, f) for d, _, fs in os.walk(os.path.join(ROOT, 'tests', 'java_stubs'))
              for f in fs if f.endswith('.java')]


def java_compile(sources):
    javac = shutil.which('javac')
    if javac:
        command = [javac]
    elif shutil.which('java'):
        command = [shutil.which('java'), '-m', 'jdk.compiler/com.sun.tools.javac.Main']
    else:
        return None
    out_dir = tempfile.mkdtemp(prefix='lr_java_')
    _tmp_dirs.append(out_dir)
    command += ['-source', '8', '-target', '8', '-Xlint:all,-options', '-encoding', 'UTF-8', '-d', out_dir] + sources
    proc = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
    output = proc.stdout + proc.stderr
    if proc.returncode != 0 and 'jdk.compiler' in output and 'not found' in output.lower():
        return None
    return proc.returncode, output, out_dir


compiled = java_compile(stub_files + [java_file])
if compiled is None:
    skip("کامپایل گیرنده‌ی جاوا", 'JDK با کامپایلر در دسترس نیست')
else:
    rc, output, out_dir = compiled
    check("گیرنده‌ی جاوا (Java 8، -Xlint:all) بدون خطا کامپایل می‌شود", rc == 0, output[:300])
    check("هیچ هشدار/خطایی درباره‌ی ReminderReceiver.java نیست", 'ReminderReceiver.java' not in output, output[:300])
    check("کلاس خروجی org/laserricochet/notify/ReminderReceiver.class تولید شد",
          os.path.isfile(os.path.join(out_dir, 'org', 'laserricochet', 'notify', 'ReminderReceiver.class')))
    bad_src = open(java_file, encoding='utf-8').read().replace('manager.notify(', 'manager.notifyy(')
    bad_dir = make_project({'org/laserricochet/notify/ReminderReceiver.java': bad_src})
    rc_bad, _out, _d = java_compile(stub_files + [os.path.join(bad_dir, 'org', 'laserricochet', 'notify',
                                                               'ReminderReceiver.java')])
    check("(منفی) خطای تایپی در API (notifyy) کامپایل را می‌شکند -> بررسی بی‌اثر نیست", rc_bad != 0)

java_text = open(java_file, encoding='utf-8').read()
from core.notification_manager import RECEIVER_CLASS_NAME as _CLS  # noqa: E402
check("نام کلاس و بسته‌ی جاوا با RECEIVER_CLASS_NAME پایتون یکی است",
      'package org.laserricochet.notify;' in java_text and _CLS == 'org.laserricochet.notify.ReminderReceiver'
      and 'class ReminderReceiver' in java_text)
check("کلیدهای extra در جاوا همان‌هایی‌اند که پایتون می‌فرستد",
      all(f'getStringExtra("{k}")' in java_text for k in ('key', 'title', 'text')))
check("جاوا: FLAG_IMMUTABLE برای PendingIntent (الزام اندروید ۱۲+)", 'FLAG_IMMUTABLE' in java_text)
check("جاوا: بدون AndroidX (هیچ وابستگی Gradle اضافه نمی‌شود)", 'androidx' not in java_text)

hook_spec = importlib.util.spec_from_file_location('p4a_hook', os.path.join(ROOT, 'native', 'p4a_hook.py'))
hook = importlib.util.module_from_spec(hook_spec)
hook_spec.loader.exec_module(hook)
MANIFEST = ('<manifest>\n  <application android:label="x">\n    <activity android:name="A"/>\n'
            '  </application>\n</manifest>\n')
patched, changed = hook.patch_manifest_text(MANIFEST)
check("hook: receiver قبل از </application> درج می‌شود",
      changed and patched.index('ReminderReceiver') < patched.index('</application>'))
check("hook: receiver با exported=false و همان نام کلاس پایتون",
      f'android:name="{_CLS}"' in patched and 'android:exported="false"' in patched)
check("hook: idempotent (بار دوم تغییری نمی‌دهد)", hook.patch_manifest_text(patched) == (patched, False))
check("hook: تورفتگی تگ بستن دست‌نخورده می‌ماند", '\n  </application>' in patched)
check("hook: مانیفست بدون </application> -> ValueError",
      raises(lambda: hook.patch_manifest_text('<manifest/>'), ValueError))
cwd = os.getcwd()
work = make_project({'src/main/AndroidManifest.xml': MANIFEST})
try:
    os.chdir(work)
    hook.after_apk_build(None)
    check("hook.after_apk_build: مانیفست واقعی روی دیسک patch می‌شود",
          'ReminderReceiver' in open('src/main/AndroidManifest.xml', encoding='utf-8').read())
    hook.after_apk_build(None)
    check("hook.after_apk_build: بار دوم (idempotent) فقط یک receiver",
          open('src/main/AndroidManifest.xml', encoding='utf-8').read().count('<receiver') == 1)
    os.chdir(make_project({'unrelated.txt': 'x'}))
    check("hook: مانیفست پیدا نشد -> فقط هشدار، بدون استثنا (بیلد نمی‌شکند)", hook.after_apk_build(None) is None)
    os.chdir(make_project({'src/main/AndroidManifest.xml': '<manifest/>'}))
    check("hook: مانیفست خراب -> فقط هشدار، بدون استثنا (بیلد نمی‌شکند)", hook.after_apk_build(None) is None)
finally:
    os.chdir(cwd)

check("preflight: native/ سالم گزارش می‌شود", preflight.check_native_staging(preflight.load_spec()) == [])
no_hook = make_project({'native/android/java/org/laserricochet/notify/ReminderReceiver.java': 'x',
                        'native/README.md': 'x', 'native/p4a_hook.py': 'def other():\n    pass\n'})
problems = preflight.check_native_staging(preflight.load_spec(), no_hook)
check("(منفی) hook بدون after_apk_build/patch_manifest_text گرفته می‌شود",
      has(problems, 'after_apk_build') and has(problems, 'patch_manifest_text'), str(problems))
check("(منفی) فایل جاوای ناموجود گرفته می‌شود",
      has(preflight.check_native_staging(preflight.load_spec(), make_project({'native/README.md': 'x'})), 'ReminderReceiver'))

# ====================================================================
for directory in _tmp_dirs:
    shutil.rmtree(directory, ignore_errors=True)

print(f"\n=== نتیجه: {passed} OK, {failed} FAIL" + (f", {skipped} SKIP" if skipped else '') + " ===")
sys.exit(1 if failed else 0)
