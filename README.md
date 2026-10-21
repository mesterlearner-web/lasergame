# Laser Ricochet

بازی پازل موبایل اندرویدی — تیراندازی لیزری با کمانه در آینه‌ها. ساخته‌شده با Python/Kivy.

## وضعیت پروژه
فاز۱ تا فاز۷ کامل شدن (هسته‌ی ECS + Raycasting، مرحله/تایمر/سختی، اقتصاد با SQLite واقعی، ناوبری، لایه‌ی Juice، سیستم‌های نگه‌داشت). **فاز۸** (آماده‌سازی برای اندروید واقعی) و **فاز۹** (محتوای کامل: ۱۰۰ مرحله‌ی کمپین با مولد رویه‌ای، حالت بی‌نهایت، چالش روزانه، دستاوردها) و بخش آفلاینِ **فاز۱۰** (صدای واقعی، آیکن، پولیش HUD/لرزش، بازتوازن اقتصاد) پیاده‌سازی شده‌اند. **هنوز هیچ APKی ساخته یا روی گوشی اجرا نشده:** هرچه بدون بیلد واقعی قابل‌اثبات بود با تست آفلاین پوشش داده شده، و اولین اجرای CI روی GitHub تنها تأیید قطعی بیلد است (بخش «ساخت APK»). مراحل تولیدی *حل‌پذیر اثبات شده‌اند*، نه اینکه انسانی بازی و از نظر «حس سختی/لذت» تنظیم شده باشند -- این فقط روی دستگاه ممکن است. مشخصات کامل و تصمیم‌های معماری در فایل‌های زیر (بیرون از این ریپو، همراه پروژه نگه داشته می‌شوند) مستندند:
- `LASER_RICOCHET_MASTER_SPEC.md` — مشخصات فنی کامل و تصمیم‌های حل‌شده
- `PROGRESS.md` — وضعیت لحظه‌ای ساخت (چه چیزی آماده است، قدم بعدی چیست)

## اجرای محلی (برای توسعه)
```bash
pip install -r requirements.txt
python main.py
```
(روی دسکتاپ پنجره‌ی ۴۰۵×۷۲۰ باز می‌شود؛ همان اندازه‌ی گوشی‌های ۳۶۰ تا ۴۱۱dp.)

## اجرای تست‌ها (بدون نیاز به Kivy و بدون اندروید)
```bash
python tests/test_core.py        # ۳۱۲ تست: منطق هسته (ECS، Raycasting، اقتصاد، ذخیره‌سازی، ماموریت‌ها، ...)
python tests/test_build.py       # ۱۹۳ تست: بیلد، بسته‌بندی، فونت، شکستن خط RTL، اعلان‌ها (JNI ساختگی)، کامپایل جاوا
python tests/test_ui_smoke.py    # ۱۶۱ تست: کل برنامه‌ی واقعی با «Kivy ساختگی» (همه‌ی صفحه‌ها، هر دکمه، بازی کامل، چالش‌ها)
python tests/test_phase9.py      # ۱۵۲ تست: مولد مراحل، ۱۰۰ فایل کمپین، بی‌نهایت، چالش روزانه، دستاوردها، ذخیره‌سازی (≈۴۰ ثانیه)
python tests/test_phase10.py     # ۸۱ تست: صدای واقعی (و مقاوم در برابر خرابی)، آیکن/presplash، HUD، راهنمای مرحله، لرزش واقعی صحنه، ساختار canvas، صدای دکمه، اقتصاد
python tools/preflight.py        # ۱۰ بررسی آفلاین پیکربندی بیلد (spec، requirements، فونت، dp، پایتون ۳.۱۱، workflow، فایل مراحل)
```
همه‌ی این‌ها باید OK بدهند. `test_build.py` اگر PyYAML یا JDK نباشد بخش مربوطه را SKIP می‌کند (شکست حساب نمی‌شود).

**دامنه‌ی صادقانه‌ی تست دودی UI:** `tests/kivy_stub.py` یک Kivy *ساختگیِ سخت‌گیر* است (kwarg ناموجود → `TypeError` مثل Kivy واقعی). کدِ خودِ ما را اجرا می‌کند و خطای import، غلط تایپی، فراخوانی اشتباه APIهای داخلی و استثنا در callbackها را می‌گیرد. ظاهر، layout واقعی، عملکرد و رفتار OpenGL/SDL را **نمی‌سنجد.** مراحل تولیدی در این تست‌ها با *راه‌حل ثابت‌شده‌ی مولد* در GameWidget واقعی شلیک می‌شوند.

## ساخت APK

### روی GitHub Actions (روش اصلی)

**۱. آپلود (مهم):** پروژه ۲۳۹ فایل دارد؛ آپلود از مرورگر («Add file → Upload files») حداکثر ۱۰۰ فایل در هر بار می‌پذیرد و بقیه‌ی زنجیره را به چند commit می‌شکند (هر commit یک اجرای ناقص و قرمز می‌سازد). پس با **git** یا **GitHub Desktop** و در **یک commit** پوش کنید:
```bash
cd laser_ricochet                       # پوشه‌ای که buildozer.spec و .github داخلش است
git init -b main
git add -A
git commit -m "Laser Ricochet"
git remote add origin https://github.com/<user>/<repo>.git
git push -u origin main
```
قواعد حیاتی: (الف) `.github/workflows/build-apk.yml` باید **در ریشه‌ی ریپو** باشد، نه داخل زیرپوشه‌ای مثل `laser_ricochet/` (GitHub فقط ریشه را می‌خواند و در غیر این صورت هیچ اتفاقی نمی‌افتد)؛ (ب) فایل zip را مستقیم آپلود نکنید (GitHub آن را باز نمی‌کند)؛ (ج) تب **Actions** باید فعال باشد (برای ریپوی جدید پیش‌فرض است؛ روی fork باید دستی فعال شود).

**۲. اجرای خودکار:** هر push به شاخه‌ی `main` یا `master` و هر tag مثل `v0.1.0` یک اجرا شروع می‌کند؛ اجرای دستی: تب **Actions** ← «Build Android APK» ← «Run workflow».
۳. مراحل:
   - **preflight** (≈۲ دقیقه): هر پنج مجموعه تست + `tools/preflight.py` روی **پایتون ۳.۱۱** (نسخه‌ی پایتونِ داخل APK). شکستش بیلد سنگین را اصلاً شروع نمی‌کند.
   - **build** (۲۵ تا ۶۰ دقیقه، بار اول بیشتر): دو پروفایل موازی. `pinned` = نسخه‌های دقیقاً pin‌شده (buildozer 1.5.0، p4a `v2024.01.21`، NDK r25b) و **ملاک موفقیت**. `latest` = ابزار جدید + p4a master، آزمایشی (شکستش workflow را قرمز نمی‌کند)؛ فقط پوششی در برابر تغییرات ناشناخته‌ی ابزار بیلد.
   - **release** (فقط روی tag مثل `v0.1.0`): APK پروفایل pinned را به یک GitHub Release وصل می‌کند (لینک عمومی).
۴. بعد از موفقیت: صفحه‌ی اجرا ← **Artifacts** ← `laser-ricochet-debug-apk-pinned` (داخلش `LaserRicochet-pinned-debug.apk`؛ خلاصه‌ی حجم/sha256 در Summary اجرا هم هست).
۵. نصب: APK را روی گوشی **arm64** با اندروید ۷.۰+ نصب کنید («نصب از منبع ناشناس» را مجاز کنید). امولاتور x86 این APK را اجرا نمی‌کند.

### اگر بیلد شکست خورد
آرتیفکت **`build-log-pinned`** (و `build-log-latest`) همیشه آپلود می‌شود -- لاگ کامل را دانلود کنید و همراه PROGRESS.md در گفت‌وگوی بعدی بدهید. اگر `pinned` شکست خورد و `latest` موفق شد، مشکل از pinهاست و pin را به نسخه‌ی کارکرده می‌بریم.

> ⚠️ جدول زیر **حدس‌های مبتنی بر تجربه‌ی عمومی با buildozer/p4a** است، نه نتیجه‌ی بیلد واقعی این پروژه (هیچ بیلدی هنوز اجرا نشده).

| نشانه | علت محتمل | اقدام |
|---|---|---|
| `Aidl not found, please install it` | buildozer 1.5.0 بالاترین build-tools موجود (ممکن است نسخه‌ی جدید/RC) را نصب می‌کند و `aidl` همراهش نیست | نتیجه‌ی پروفایل `latest` را ببینید؛ اگر سبز بود pin را به آن ببرید |
| هشدار Gradle: `compileSdk = 34 ... tested up to compileSdk = 32` | AGP قدیمی داخل p4a؛ فقط هشدار | هیچ -- بی‌خطر |
| خطای نصب `python-bidi` (Rust/maturin) | pin `python-bidi==0.4.2` از دست رفته | `python tools/preflight.py` این را می‌گیرد |
| روی گوشی: متن فارسی به‌صورت مربع □ | فونت پیدا/ثبت نشده | `adb logcat \| grep "no Persian-capable font"` |
| روی گوشی: حروف فارسی جدا و برعکس | `arabic_reshaper`/`python-bidi` import نشده (مثلاً وابستگی `six` نیامده) | `adb logcat \| grep "failed to import"` |
| `INSTALL_FAILED_NO_MATCHING_ABIS` | دستگاه ۳۲بیتی یا x86 | فقط `arm64-v8a` ساخته می‌شود (تصمیم فایل مرجع ۲.۳) |
| برنامه هنگام باز شدن کرش می‌کند | -- | `adb logcat \| grep -i -E "python\|laser\|traceback"` و لاگ را بدهید |

### ساخت محلی (لینوکس، JDK 17)
```bash
python -m pip install "buildozer==1.5.0" "cython==0.29.36"
buildozer -v android debug          # خروجی: bin/*.apk
```
فهرست بسته‌های سیستمی لازم در مرحله‌ی «Install system dependencies» فایل workflow است.

### اعلان‌های واقعی اندروید (استیج‌شده)
کد جاوا و patch مانیفست در `native/` آماده و تست‌شده‌اند ولی عمداً *بعد از* اولین بیلد سبز فعال می‌شوند (دو خط کامنت در `buildozer.spec`). جزئیات و مرز «تأییدشده/تأییدنشده»: `native/README.md`.

## ساختار پروژه
```
laser_ricochet/
├── main.py                      # نقطه‌ی ورود -- AppContext، ثبت صفحات، فونت، دکمه‌ی Back، چرخه‌ی عمر اعلان‌ها
├── buildozer.spec                # تنظیمات ساخت اندروید (pinها و دلیل هرکدام در کامنت‌ها)
├── .github/workflows/build-apk.yml  # preflight -> build (pinned + latest) -> release
├── ecs/                           # هسته‌ی Entity-Component-System
│   ├── entity.py / component.py / system.py / world.py
│   ├── components/                # Position, Velocity, Render, Collision, Mirror, Target,
│   │                               # Obstacle, Portal, Prism, BlackHole
│   └── systems/                   # MovementSystem (۷ الگوی حرکت), RotationSystem
├── game_logic/
│   ├── raycast.py                 # موتور Raycasting
│   ├── scene_builder.py           # ساخت صحنه + تبدیل ECS -> ورودی Raycaster
│   ├── level.py                   # بارگذاری یک مرحله از JSON -> دنیای ECS
│   ├── level_manager.py           # بارگذاری/باز کردن قفل/پیشروی/ثبت ستاره
│   ├── level_condition.py         # شرط برد/باخت + رتبه‌بندی + calculate_stars
│   ├── level_validator.py         # is_solvable (+ RotationSystem، deterministic_only، angle_range) + used_mechanic_types
│   ├── level_generator.py         # مولد سازنده‌ی مراحل -- ۹۵ مرحله‌ی کمپین، بی‌نهایت، روزانه (فاز۹)
│   ├── endless_mode.py            # حالت بی‌نهایت + پیش‌تولید پس‌زمینه (فاز۹)
│   ├── daily_challenge.py         # چالش روزانه از روی تاریخ (فاز۹)
│   ├── achievements.py            # AchievementManager (فاز۹؛ کلیدهای بخش ۶ فایل مرجع)
│   ├── difficulty_manager.py      # منحنی سختی ۵فاز روی کل ۱۰۰ مرحله
│   ├── special_shot_manager.py    # شلیک‌های ویژه متصل به raycast
│   ├── economy_manager.py         # EconomyManager + EconomyBalance
│   ├── energy_manager.py          # سیستم انرژی با بازآفرینی پیوسته
│   ├── equipment_manager.py       # بونوس اسلحه‌ی مجهز
│   ├── shop_manager.py            # فروشگاه -- ۴ دسته‌ی آیتم
│   ├── settings_manager.py        # ترجیح رنگ‌کوری/صدا/موسیقی
│   ├── save_manager.py            # PlayerProfile کامل <-> SQLite
│   ├── navigation_history.py      # منطق خالص پشته‌ی ناوبری
│   ├── back_navigation.py         # منطق خالص دکمه‌ی Back اندروید (فاز۸)
│   ├── missions.py                # ماموریت‌های روزانه/هفتگی (فاز۷)
│   ├── daily_rewards.py           # جایزه‌ی ورود روزانه + استریک (فاز۷)
│   ├── weekly_challenge.py        # چالش هفتگی (فاز۷)
│   └── retention_analytics.py     # D1/D3/D7/D14/D30 (فاز۷)
├── core/
│   ├── constants.py
│   ├── database.py                # پوشش SQLite (WAL mode)
│   ├── app_context.py             # باندل مشترک بین همه‌ی صفحات
│   ├── color_palette.py           # پالت رنگ صحنه -- حساس به کوررنگی
│   ├── audio_manager.py           # AudioManager -- افکت/موسیقی
│   ├── game.py                    # AnimationManager Singleton
│   └── notification_manager.py    # NotificationManager -- AlarmManager واقعی؛ بدون گیرنده‌ی جاوا receiver_missing می‌دهد (فاز۷/۸)
├── ui/
│   ├── screen_manager.py          # GameScreenManager (goto/go_back)
│   ├── widgets/                   # PersianLabel (شکستن خط RTL)/Button, TopBar, EconomyBar, TimerRing
│   ├── effects/                   # AdvancedScreenShake
│   └── screens/                   # ۱۰ صفحه: main_menu, level_select, game, shop, settings,
│                                   # profile, sandbox, battle_pass, missions, challenges (فاز۹)
├── utils/
│   ├── pool.py                    # Object Pooling عمومی
│   ├── timer.py                   # تایمر دقیق + آستانه‌ی درصدی رتبه‌بندی
│   ├── persian_text.py            # شکل‌دهی/راست‌چین متن فارسی + wrap_logical_text (فاز۸)
│   ├── fonts.py                   # ثبت فونت فارسی‌دار به‌عنوان فونت پیش‌فرض Kivy (فاز۸)
│   └── particles.py               # AdvancedParticleSystem
├── data/
│   ├── shop_items.json             # کاتالوگ فروشگاه
│   └── battle_pass_rewards.json    # جدول پاداش ۵۰سطحی -- فرمولی
├── assets/
│   ├── levels/                     # level_001..005 دستی + level_006..100 تولیدی (tools/generate_levels.py)
│   ├── fonts/                      # DejaVu Sans (Regular+Bold) + مجوز -- گلیف فارسی؛ Vazirmatn کنارش بگذارید خودکار برنده می‌شود
│   └── audio/                      # فایل‌های .ogg واقعی اینجا اضافه می‌شن (فعلاً خالی)
├── tools/                          # فقط زمان توسعه/CI (داخل APK نمی‌رود)
│   ├── preflight.py                # بررسی‌های آفلاین پیکربندی بیلد
│   ├── generate_levels.py          # تولید/بررسی level_006..100 با مولد (فاز۹)
│   ├── generate_audio.py           # سنتز ۱۵ فایل صوتی → assets/audio/*.ogg (فاز۱۰؛ ffmpeg لازم)
│   ├── generate_icons.py           # آیکن و presplash → assets/*.png (فاز۱۰؛ Pillow لازم)
│   └── font_coverage.py            # آیا فونت همه‌ی گلیف‌های لازم UI را دارد؟
├── native/                         # اعلان‌های واقعی اندروید -- استیج‌شده (native/README.md)
│   ├── android/java/org/laserricochet/notify/ReminderReceiver.java
│   └── p4a_hook.py
└── tests/
    ├── test_core.py / test_build.py / test_ui_smoke.py / test_phase9.py / test_phase10.py
    ├── kivy_stub.py / fake_jnius.py   # Kivy و JNI ساختگی (فقط تست)
    └── java_stubs/ fixtures/          # استاب API اندروید برای کامپایل‌چک جاوا؛ فونت لاتین‌فقط برای تست منفی
```

## محتوای کامل (فاز۹)

### ۱۰۰ مرحله‌ی کمپین
مراحل ۱ تا ۵ دستی‌اند و **هرگز بازنویسی نمی‌شوند**؛ ۶ تا ۱۰۰ را مولد رویه‌ای می‌سازد و به‌صورت فایل (همان قالب فشرده‌ی مراحل دستی) در `assets/levels/` نگه‌داری می‌شوند: همه‌ی بازیکن‌ها دقیقاً یک ۱۰۰ مرحله دارند، قابل‌بازبینی/diff‌اند، و هزینه‌ی تولید (تا ≈۱ ثانیه برای مراحل بالا) هنگام بازی نیست.
```bash
python tools/generate_levels.py            # بازتولید level_006..100
python tools/generate_levels.py --check    # فایل‌ها با مولد یکی‌اند؟ (test_phase9 هم همین را می‌سنجد)
```
**مولد سازنده است، نه «بچین و امیدوار باش»:** برای هر هدف اول یک مسیر حل واقعی (اسلحه ← چند آینه ← هدف) از روی قانون بازتاب ساخته می‌شود (مسیرسازی هدایت‌شده: طول هر پاره فقط از بازه‌ای انتخاب می‌شود که پرتو داخل میدان می‌ماند، هر قدم بلافاصله بررسی و در صورت تداخل فقط همان قدم دوباره امتحان می‌شود). بعد شلوغی انحرافی اضافه می‌شود و خودِ موتور Raycasting همان راه‌حل را **بازپخش** می‌کند و باید با حاشیه‌ی زاویه‌ی کافی به هدف بخورد. هر مکانیک در سطح معرفی‌اش *اجباراً* می‌آید (۱۶ نیمه‌شفاف، ۲۰ چرخان، ۲۲ منشور، ۳۳ پورتال، ۳۸ سیاه‌چاله، ۴۳ شکسته).

سیاست «اثبات قطعی»: سیاه‌چاله و آینه‌ی شکسته به random سراسری وابسته‌اند، پس فقط مانع/تزئین حساب می‌شوند؛ الگوهای حرکت `random` و `chase_crosshair` در مراحل تولیدی نیستند. هر ۹۵ مرحله‌ی فایل را اعتبارسنج جاروبیِ مستقل از مولد (`is_solvable(..., deterministic_only=True, angle_range=(5, 175))`) و `DifficultyManager.validate_level_conformance` هم تأیید می‌کنند. RNG فقط `random()` را مصرف می‌کند (تنها بخش تضمین‌شده‌ی پایدار بین نسخه‌های پایتون).

### صفحه‌ی «چالش‌ها»
* **چالش روزانه:** هر روز یک مرحله از روی *تاریخ* (همه در یک روز مرحله‌ی یکسان می‌گیرند)، سختی با روز هفته از ≈ مرحله‌ی ۲۰ (دوشنبه) تا ≈ ۶۴ (یکشنبه). پاداش اولین موفقیت هر روز `۵۰ + ۱۰·min(استریک،۱۰)` سکه و ۱ جواهر هر ۷ روز استریک. عقب‌بردن ساعت گوشی پاداش دوباره نمی‌دهد.
* **حالت بی‌نهایت:** مرحله‌های پیاپی با سختی فزاینده (مرحله‌ی ۱ ≈ سطح ۸، هر مرحله ۳ سطح بالاتر) و زمان کمتر از کمپین؛ باخت = پایان اجرا. هر اجرا ۱ انرژی؛ پاداش `min(25, 3+مرحله)` سکه به‌ازای هر مرحله. مرحله‌ی بعد در یک نخ پس‌زمینه پیش‌تولید می‌شود (تولید مراحل بالا روی گوشی میان‌رده ممکن است چند ثانیه طول بکشد).
* **دستاوردها:** `streak_25`، `endless_10`، `endless_25` (طبق بخش ۶ فایل مرجع) + `daily_challenge_7`.
* هیچ‌کدام به پیشرفت کمپین (ستاره، قفل مرحله، انرژی هر مرحله) دست نمی‌زنند.

## سیستم مختصات
تمام منطق بازی در «فضای طراحی» ثابت ۱۰۸۰×۱۹۲۰ کار می‌کند؛ تبدیل design-space↔screen-space فقط در `ui/screens/game_screen.py` انجام می‌شود. جزئیات کامل در `LASER_RICOCHET_MASTER_SPEC.md` بخش ۲.۲.

## ذخیره‌سازی
پیشرفت بازیکن (سکه، جواهر، انرژی، Battle Pass، مراحل/ستاره‌ها، تنظیمات، ماموریت‌ها، جایزه‌ی روزانه، چالش هفتگی، تاریخچه‌ی جلسات) در یک فایل SQLite (حالت WAL) ذخیره می‌شود -- روی اندروید در `App.user_data_dir`.

## نگه‌داشت (فاز۷)
هر بار اپ باز می‌شود، یک «جلسه‌ی امروز» ثبت و ریست‌های تقویمی (ماموریت‌های روزانه/هفتگی، چالش هفتگی) چک می‌شوند. ماموریت‌ها از رویدادهای واقعی بازی (شلیک، نابودی هدف، برد مرحله، خرید، ...) پیش می‌روند -- `MissionManager._find_mission_by_id` + `copy.deepcopy` تضمین می‌کند پیشرفت یک بازیکن هیچ‌وقت تعریف پایه‌ی ماموریت را خراب نکند. چالش هفتگی فقط پاداش شرکت می‌دهد (بدون رتبه‌بندی جهانی، چون این پروژه بک‌اند واقعی ندارد). `NotificationManager` از فاز۸ واقعاً `AlarmManager` را صدا می‌زند (نسخه‌ی فاز۷ فقط `scheduled=True` برمی‌گرداند بی‌آن‌که چیزی زمان‌بندی کند)؛ ولی نمایش اعلان به یک گیرنده‌ی جاوا نیاز دارد که در `native/` استیج‌شده و تا فعال‌شدنش `receiver_missing` (نه موفقیت دروغین) برمی‌گردد. تأیید نهایی فقط روی گوشی واقعی ممکن است.

## صدا
`core/audio_manager.AudioManager` معماری کامل صدا را فراهم می‌کند، ولی فایل‌های صوتی واقعی هنوز اضافه نشده‌اند — بدون آن‌ها بازی کاملاً عادی کار می‌کند (سکوت، نه کرش). جزئیات در `assets/audio/README.md`.

## فونت فارسی (فاز۸)
فونت پیش‌فرض Kivy (Roboto) هیچ حرف عربی/فارسی ندارد؛ بدون فونت دیگر همه‌ی متن فارسی مربع □ نشان داده می‌شد (و تا فاز۷ هیچ‌وقت دیده نشد چون Kivy هرگز اجرا نشده بود). `assets/fonts/` فونت DejaVu Sans را دارد که با `python tools/font_coverage.py` تأیید شده همه‌ی ۲۵۶ کدپوینت لازم UI را دارد -- از جمله **اشکال پیوسته‌ی** هر حرف (چون `arabic_reshaper` به کدپوینت‌های Presentation Forms تبدیل می‌کند، نه حروف پایه) و نیم‌فاصله. `utils/fonts.py` آن را به‌عنوان فونت پیش‌فرض ثبت می‌کند. فونت زیباتر (مثلاً Vazirmatn) را با نام‌های `Vazirmatn-Regular.ttf` / `Vazirmatn-Bold.ttf` در همان پوشه بگذارید تا خودکار جایگزین شود؛ سپس `python tools/font_coverage.py` را اجرا کنید تا مطمئن شوید گلیف کم ندارد.
