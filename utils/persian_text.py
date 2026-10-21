"""
utils/persian_text.py

⚠️ یافته‌ی مهم که حین ساخت کشف شد: Kivy به‌صورت پیش‌فرض هیچ Text
Shaping ای برای متن راست‌چین (فارسی/عربی) انجام نمی‌دهد -- یعنی
حروف به‌هم‌نمی‌چسبند و ترتیب نمایش اشتباه است (این یک محدودیت
شناخته‌شده‌ی خودِ Kivy است، نه فقط این پروژه). قبل از هر Label/Button
که متن فارسی نشون می‌ده، باید از تابع shape() همین فایل عبور کنه.

این تابع باید در *همه‌ی* صفحات UI (فاز۵ نقشه‌راه) به‌کار بره، نه
فقط این HUD موقت -- در فایل مرجع (بخش نکات فاز۲) هم ثبت شده.
"""
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def wrap_logical_text(text, max_width, measure):
    """شکستن خط حریصانه‌ی متن *منطقی* (shape-نشده) -- «اول بشکن، بعد shape کن».

    ⚠️ باگی که در بازبینی فاز۸ پیدا شد: shape() کل رشته را برعکس می‌کند (ترتیب بصری
    راست‌به‌چپ). اگر Kivy بعد از آن خط را بشکند، خط اول *آخر* جمله را نشان می‌دهد و
    خط آخر ابتدای آن را -- جمله‌ی چندخطی با ترتیب وارونه. راه درست: شکستن روی متن
    منطقی، و shape هر خط به‌تنهایی.

    measure(line) -> عرض پیکسلی همان خط (بعد از shape؛ تماس‌گیرنده shape را داخل
    measure صدا می‌زند). خروجی: لیست خط‌های منطقی به ترتیب خواندن. کلمه‌ای که تنهایی از
    max_width بلندتر باشد در خط خودش می‌ماند (قابل‌شکستن نیست). خط‌شکن‌های صریح (newline) حفظ می‌شوند. نیم‌فاصله
    (ZWNJ) جداکننده‌ی کلمه نیست، پس کلمه‌ها وسط نیم‌فاصله نمی‌شکنند."""
    lines = []
    for paragraph in text.split('\n'):
        current = ''
        for word in paragraph.split(' '):
            candidate = word if not current else current + ' ' + word
            if current and measure(candidate) > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
    return lines


def is_shaping_available():
    """آیا arabic_reshaper و python-bidi واقعاً import شدند؟ اگر نه، shape() متن خام
    برمی‌گرداند و فارسی جدا/برعکس نمایش داده می‌شود -- بی‌هیچ خطایی. main.py این را
    در شروع برنامه چک و بلند لاگ می‌کند (فاز۸: وگرنه این خرابی روی گوشی کاملاً
    بی‌صدا بود)."""
    return _AVAILABLE


def shape(text):
    """متن فارسی/عربی را برای نمایش صحیح در Kivy آماده می‌کند (اتصال
    حروف + جهت راست‌چین). برای متن انگلیسی/اعداد خالص بی‌ضرر است.

    اگر کتابخانه‌ها نصب نباشند (مثلاً در محیط تست بدون آن‌ها)، متن
    خام برگردانده می‌شود تا برنامه کرش نکند -- ولی این حالت فقط برای
    fallback است؛ برای build واقعی این دو کتابخانه در requirements
    اجباری‌اند.
    """
    if not _AVAILABLE:
        return text
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)
