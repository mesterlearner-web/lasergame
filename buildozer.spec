[app]
title = Laser Ricochet
package.name = laserricochet
package.domain = com.laserricochet
source.dir = .

# فاز۸: ttf اضافه بود ولی فونتی در پروژه نبود -- حالا assets/fonts/ (DejaVu Sans،
# تنها فونتی که گلیف فارسی دارد؛ بدون آن همه‌ی متن فارسی مربع نشان داده می‌شد).
# txt = متن مجوز فونت (بازتوزیع فونت مستلزم همراه‌بودن مجوز است).
source.include_exts = py,json,ogg,wav,ttf,txt,png,jpg,kv,atlas
# tools/native/docs فقط زمان توسعه‌اند و نباید داخل APK برن. (پوشه‌های پنهان مثل
# .git/.github/.buildozer را خودِ buildozer همیشه نادیده می‌گیرد.)
source.exclude_dirs = tests,tools,native,docs,bin,.git,__pycache__,.github

version = 0.1.0

# توجه: KivEnt/Cymunk عمداً حذف شده‌اند -- طبق تصمیم فایل مرجع (بخش ۲.۱)،
# ECS دستی است و هیچ موتور فیزیک خارجی لازم نیست.
#
# فاز۸ -- چرا همه‌ی این‌ها pin شده‌اند (و با requirements.txt یکسان‌اند):
# * python-bidi==0.4.2: نسخه‌های ۰.۵+ با Rust نوشته شده‌اند و برای اندروید wheel
#   ندارند؛ بدون pin، p4a آخرین نسخه را می‌گیرد و یا بیلد می‌شکند یا import روی
#   گوشی خطا می‌دهد -- و چون utils/persian_text.py خطای import را *بی‌صدا*
#   می‌بلعد، فارسی بدون هیچ پیغامی خراب (حروف جدا و برعکس) نمایش داده می‌شد.
# * six: python-bidi 0.4.2 به آن import می‌کند. p4a پکیج‌های pip را با --no-deps
#   نصب می‌کند، پس وابستگی‌های pip باید *صریحاً* اینجا فهرست شوند.
# * pyjnius/android: برای NotificationManager و درخواست مجوز اعلان؛ (kivy خودش
#   pyjnius را می‌کشد ولی صریح‌بودن ایمن‌تر است).
requirements = python3,kivy==2.3.0,pyjnius,android,arabic_reshaper==3.0.0,python-bidi==0.4.2,six

orientation = portrait
fullscreen = 1

# فاز۱۰: آیکن و صفحه‌ی ورود اختصاصی (تولید با tools/generate_icons.py).
# رنگ زمینه‌ی presplash باید با PRESPLASH_COLOR در همان ابزار یکی باشد.
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/presplash.png
android.presplash_color = #060610

# طبق تصمیم فایل مرجع، بخش ۲.۳: API مدرن و پایدار برای p4a، بدون الزام
# سطح ۳۶ گوگل‌پلی چون توزیع از مسیر مستقیم APK/GitHub است.
android.api = 34
android.minapi = 24
# فاز۸: NDK صریحاً pin شد (پیش‌فرض buildozer در نسخه‌های مختلف فرق می‌کند).
# r25b همان NDK توصیه‌شده‌ی p4a v2024.01.21 است.
android.ndk = 25b
android.ndk_api = 24
android.accept_sdk_license = True

# فقط arm64-v8a برای کاهش حجم APK -- طبق تصمیم فایل مرجع، بخش ۲.۳.
# اگر پشتیبانی از گوشی‌های ۳۲بیتی قدیمی لازم شد، armeabi-v7a هم اضافه شود.
# (امولاتور x86 اندروید استودیو این APK را اجرا نمی‌کند؛ روی گوشی واقعی یا
# امولاتور arm64 تست شود.)
android.archs = arm64-v8a

android.allow_backup = True
android.permissions = VIBRATE,INTERNET,ACCESS_NETWORK_STATE,POST_NOTIFICATIONS

android.release_artifact = apk
android.debug_artifact = apk

# فاز۸: python-for-android روی یک tag مشخص pin شد (نه master) تا بیلد قابل‌تکرار
# باشد: v2024.01.21 = Python 3.11 + Kivy 2.3.0 + NDK r25b. اگر لازم شد عوض کنید،
# CI یک پروفایل experimental روی master هم دارد (بخش «ساخت APK» در README).
p4a.branch = v2024.01.21

# --- اعلان‌های واقعی (استیج‌شده -- هنوز فعال نیست) ---------------------------
# کد جاوا + patch مانیفست در native/ آماده و تست‌شده‌اند ولی عمداً از بیلد پایه
# بیرون نگه داشته شده‌اند: «اول یک APK پایه‌ی سبز، بعد کد native». بعد از
# اولین بیلد موفق، این دو خط را از حالت کامنت دربیاورید (جزئیات: native/README.md):
# android.add_src = native/android/java
# p4a.hook = native/p4a_hook.py

[buildozer]
log_level = 2
warn_on_root = 1
