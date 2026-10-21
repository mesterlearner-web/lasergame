"""
native/p4a_hook.py  (فاز ۸ -- استیج‌شده؛ در buildozer.spec با `p4a.hook = native/p4a_hook.py` فعال می‌شود)

hook برای python-for-android: بعد از این‌که پروژه‌ی اندروید ساخته شد و *قبل از* اجرای Gradle،
`<receiver>` گیرنده‌ی اعلان (native/android/java/.../ReminderReceiver.java) را در
AndroidManifest.xml می‌گذارد.

چرا hook: buildozer.spec کلیدی برای افزودن *المان فرزند* داخل `<application>` ندارد
(`android.extra_manifest_application_arguments` فقط ATTRIBUTE به تگ application اضافه
می‌کند، `android.extra_manifest_xml` بیرون از آن می‌نشیند). hook مستندشده‌ترین راه
دست‌بردن در مانیفست تولیدشده است.

طراحی دفاعی: *هرگز* بیلد را نمی‌شکند. اگر مانیفست پیدا نشد یا ساختارش غیرمنتظره بود،
فقط یک هشدار در لاگ بیلد چاپ می‌شود و APK بدون گیرنده ساخته می‌شود (نتیجه‌ی بدترین حالت:
اعلانی نمایش داده نمی‌شود -- NotificationManager پایتون هم receiver_missing برمی‌گرداند
و صادقانه scheduled=False می‌دهد، نه این‌که الکی موفقیت گزارش دهد).

منطق اصلی (patch_manifest_text) تابع خالص و idempotent است و بدون p4a تست می‌شود
(tests/test_build.py).
"""
import os

RECEIVER_CLASS = 'org.laserricochet.notify.ReminderReceiver'
#: exported=false: فقط خودِ برنامه (و سیستم از طریق PendingIntent خودمان) می‌تواند آن را صدا بزند.
RECEIVER_XML = f'<receiver android:name="{RECEIVER_CLASS}" android:exported="false" />'

#: p4a (bootstrap sdl2، Gradle) مانیفست را اینجا می‌نویسد؛ مسیر دوم برای bootstrapهای قدیمی‌تر.
_MANIFEST_CANDIDATES = (
    os.path.join('src', 'main', 'AndroidManifest.xml'),
    'AndroidManifest.xml',
)


def patch_manifest_text(manifest_text):
    """(متن_جدید، تغییر_کرد). receiver را درست قبل از `</application>` می‌گذارد.
    Idempotent: اگر قبلاً هست دوباره اضافه نمی‌کند. اگر `</application>` نبود ValueError."""
    if RECEIVER_CLASS in manifest_text:
        return manifest_text, False
    closing = manifest_text.rfind('</application>')
    if closing == -1:
        raise ValueError('AndroidManifest.xml has no </application> element')
    line_start = manifest_text.rfind('\n', 0, closing) + 1
    indent = manifest_text[line_start:closing]
    if indent.strip() == '':
        # حالت معمول: تگ بستن در ابتدای خط خودش است -> یک خط جدا با تورفتگی فرزند، تورفتگی تگ بستن دست‌نخورده.
        patched = (manifest_text[:line_start] + indent + '    ' + RECEIVER_XML + '\n'
                   + manifest_text[line_start:])
    else:
        patched = manifest_text[:closing] + RECEIVER_XML + manifest_text[closing:]
    return patched, True


def find_manifest(base_dir='.'):
    for relative in _MANIFEST_CANDIDATES:
        path = os.path.join(base_dir, relative)
        if os.path.isfile(path):
            return path
    return None


def patch_manifest_file(base_dir='.'):
    """None = مانیفست پیدا نشد؛ True = patch شد؛ False = از قبل patch شده بود."""
    path = find_manifest(base_dir)
    if path is None:
        return None
    with open(path, encoding='utf-8') as handle:
        text = handle.read()
    patched, changed = patch_manifest_text(text)
    if changed:
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(patched)
    return changed


def after_apk_build(toolchain):
    """p4a بعد از تولید پروژه‌ی Gradle (cwd = پوشه‌ی dist) و قبل از assemble صدایش می‌زند."""
    try:
        result = patch_manifest_file('.')
    except Exception as exc:  # noqa: BLE001 -- عمداً همه‌چیز؛ هرگز بیلد نشکند
        print(f'[laser-ricochet hook] WARNING: manifest patch failed ({exc!r}); '
              'this APK will have NO notification receiver')
        return
    if result is None:
        print('[laser-ricochet hook] WARNING: AndroidManifest.xml not found in the dist dir; '
              'this APK will have NO notification receiver')
    elif result:
        print(f'[laser-ricochet hook] receiver {RECEIVER_CLASS} added to AndroidManifest.xml')
    else:
        print('[laser-ricochet hook] receiver already present in AndroidManifest.xml')
