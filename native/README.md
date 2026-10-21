# native/ — اعلان‌های محلی واقعی اندروید (استیج‌شده، هنوز فعال نیست)

## چرا استیج‌شده؟

اصل: **اول یک APK پایه‌ی سبز، بعد کد native.** کد جاوا + patch مانیفست دو قطعه‌ی جدید روی
مسیر بیلدند که در این جلسه امکان اجرای واقعی‌شان نبود. اگر داخل بیلد پایه می‌بودند و بیلد شکست
می‌خورد، نمی‌شد فهمید مشکل از pipeline است یا از این‌ها. پس کامل نوشته و تا حد ممکن تست
شده‌اند، ولی در `buildozer.spec` کامنت‌اند.

## فعال‌سازی (بعد از اولین بیلد موفق APK پایه)

در `buildozer.spec` این دو خط را از حالت کامنت دربیاورید (**باید هر دو باهم فعال شوند** —
`tools/preflight.py` اگر فقط یکی فعال باشد خطا می‌دهد):

```ini
android.add_src = native/android/java
p4a.hook = native/p4a_hook.py
```

سپس commit/push. بیلد جدید را نصب کنید؛ بار اول در اندروید ۱۳+ پنجره‌ی مجوز اعلان نشان داده می‌شود.

## چطور کار می‌کند

```
بازی به پس‌زمینه می‌رود (on_pause)
   └─ main.py -> NotificationManager.schedule_energy_full / schedule_comeback_reminder
        └─ AlarmManager.setAndAllowWhileIdle( PendingIntent.getBroadcast(Intent -> ReminderReceiver) )
              ... زمان می‌گذرد، حتی اگر پروسه‌ی بازی مرده باشد ...
        └─ اندروید ReminderReceiver (جاوا) را صدا می‌زند -> NotificationChannel + Notification
بازیکن برمی‌گردد (on_start/on_resume) -> cancel_all()  (اعلان کهنه «انرژیت پر شد» نیاید)
```

| فایل | نقش |
|---|---|
| `android/java/org/laserricochet/notify/ReminderReceiver.java` | `BroadcastReceiver` — اعلان را می‌سازد/نشان می‌دهد. فقط کلاس‌های خودِ فریم‌ورک (بدون AndroidX)، سطح Java 8. |
| `p4a_hook.py` | بعد از تولید پروژه‌ی Gradle و قبل از assemble، `<receiver ... exported="false"/>` را در مانیفست می‌گذارد. هرگز بیلد را نمی‌شکند (خطا = فقط هشدار در لاگ). |
| `../core/notification_manager.py` | سمت پایتون: PyJNIus. اگر کلاس جاوا داخل APK نباشد `receiver_missing` و `scheduled=False` برمی‌گرداند (نه موفقیت دروغین). |

چرا hook و نه کلید buildozer: `android.extra_manifest_application_arguments` فقط **attribute** به تگ
`<application>` اضافه می‌کند و `android.extra_manifest_xml` بیرون از آن می‌نشیند؛ کلیدی برای المان
فرزند داخل `<application>` وجود ندارد.

## چه چیزی تأیید شده، چه چیزی نه (صادقانه)

**تأییدشده (در تست‌ها):**
- کد جاوا با `-source 8 -target 8 -Xlint:all` در برابر استاب‌های API اندروید بدون هیچ خطا/هشداری
  کامپایل می‌شود (`tests/test_build.py`؛ استاب‌ها در `tests/java_stubs/`، فقط تست).
- منطق patch مانیفست (idempotent، حالت‌های مرزی، خطا).
- سمت پایتون با یک JNI ساختگی: ترتیب و آرگومان دقیق فراخوانی‌ها (`setClassName` صریح،
  `getBroadcast` با `FLAG_IMMUTABLE | FLAG_UPDATE_CURRENT`، `setAndAllowWhileIdle(RTC_WAKEUP, ...)`،
  متن خام/shape‌نشده، لغو، مجوز، مسیر خطا).

**تأییدنشده (فقط روی گوشی/CI واقعی قابل‌تأیید):**
- معنای دقیق `android.add_src` در نسخه‌ی buildozer/p4a استفاده‌شده (فرض: محتوای پوشه داخل
  `src/main/java` ادغام می‌شود). اگر غلط باشد، بدترین حالت `receiver_missing` است، نه شکست بیلد.
- مسیر مانیفست تولیدشده (`src/main/AndroidManifest.xml`)؛ اگر فرق کند hook هشدار می‌دهد.
- رفتار واقعی Doze/باتری‌بهینه‌سازی سازنده‌های مختلف (Xiaomi/Huawei/Samsung alarm را گاهی تأخیر
  می‌دهند یا حذف می‌کنند — `setAndAllowWhileIdle` غیردقیق است و عمداً مجوز `SCHEDULE_EXACT_ALARM` نمی‌خواهد).
- ظاهر اعلان: آیکن کوچک همان آیکن اپ است؛ روی اندروید جدید به‌شکل سیلوئت سفید دیده می‌شود. برای
  آیکن تک‌رنگ مخصوص اعلان باید یک drawable جداگانه اضافه شود (پولیش بعدی).

## تست روی گوشی

1. اپ را باز کنید (مجوز اعلان را بدهید)، بعد Home بزنید.
2. بررسی ثبت alarm: `adb shell dumpsys alarm | grep -B2 -A6 laserricochet` — باید یک alarm با
   `ReminderReceiver` ببینید.
3. برای دیدن اعلان بدون چند ساعت انتظار: موقتاً `DEFAULT_COMEBACK_DELAY_HOURS = 0.02` (≈۷۰ ثانیه)
   را در `core/notification_manager.py` بگذارید، بیلد/نصب، اپ را ببندید و صبر کنید. (Doze ممکن است
   چند دقیقه تأخیر بدهد.)
4. لاگ: `adb logcat | grep -i -E "laser|ReminderReceiver"`.

> `adb shell am broadcast` مستقیم به receiver کار نمی‌کند چون `exported="false"` است (عمداً — وگرنه هر
> اپ دیگری می‌توانست اعلان جعلی با نام بازی بفرستد).
