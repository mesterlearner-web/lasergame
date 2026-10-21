"""
utils/fonts.py  (فاز ۸)

⚠️ باگی که در بازبینی فاز۸ پیدا شد: تا قبل از این فایل، هیچ‌جای پروژه فونت
تعیین نشده بود، و فونت پیش‌فرض Kivy (Roboto) هیچ حرف عربی/فارسی ندارد. یعنی
حتی با `utils.persian_text.shape()` درست، تمام متن‌های فارسی روی صفحه
به‌شکل مربع‌های توخالی (□□□) رسم می‌شدند -- چون Kivy (SDL2_ttf) هیچ‌گونه
font fallback ندارد. این مشکل تا حالا دیده نشده بود چون در هیچ فازی Kivy واقعاً
اجرا نشده بود (فقط در sandbox بدون Kivy نوشته شده بود).

راه‌حل: یک فونت دارای گلیف‌های فارسی کنار برنامه بسته‌بندی می‌شود
(`assets/fonts/`) و به‌عنوان *فونت پیش‌فرض* همه‌ی ویجت‌ها ثبت می‌شود
(`LabelBase.register(DEFAULT_FONT, ...)`) -- بدون نیاز به دست‌زدن به
`font_name` تک‌تک Label/Button ها.

اولویت فونت‌ها: اگر طراح بعداً Vazirmatn (یا هر فونت زیباتری) با همین نام‌ها
در `assets/fonts/` بگذارد، خودکار جایگزین DejaVu می‌شود -- بدون تغییر کد.
بررسی این‌که یک فونت همه‌ی حروف مورد استفاده‌ی UI را دارد:
`python tools/font_coverage.py assets/fonts/<font>.ttf`

این ماژول عمداً Kivy را فقط داخل `register_default_font` import می‌کند (نه
سطح ماژول) تا منطق انتخاب فونت بدون Kivy قابل‌تست باشد.
"""
import os

#: (regular, bold) به ترتیب اولویت. اولین جفتی که فایل regular‌اش موجود باشد برنده است.
FONT_FAMILIES = (
    ('Vazirmatn-Regular.ttf', 'Vazirmatn-Bold.ttf'),
    ('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf'),
)

#: نام پیش‌فرض Kivy -- فقط اگر import مستقیم DEFAULT_FONT از Kivy شکست بخورد.
_FALLBACK_DEFAULT_FONT_NAME = 'Roboto'


def default_fonts_dir():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'assets', 'fonts')


def resolve_font_family(fonts_dir=None):
    """(regular_path, bold_path) اولین خانواده‌ی موجود، یا None اگر هیچ‌کدام نبود.
    اگر فایل bold نبود، از regular به‌جایش استفاده می‌شود (بهتر از نبودن فونت)."""
    fonts_dir = fonts_dir or default_fonts_dir()
    for regular_name, bold_name in FONT_FAMILIES:
        regular_path = os.path.join(fonts_dir, regular_name)
        if os.path.isfile(regular_path):
            bold_path = os.path.join(fonts_dir, bold_name)
            return regular_path, (bold_path if os.path.isfile(bold_path) else regular_path)
    return None


def register_default_font(fonts_dir=None, label_base=None, default_font_name=None):
    """فونت فارسی‌دار را به‌عنوان فونت پیش‌فرض Kivy ثبت می‌کند. باید *قبل از*
    ساخته‌شدن/رسم اولین ویجت صدا زده شود.

    (regular, bold) ثبت‌شده را برمی‌گرداند، یا None اگر هیچ فونتی پیدا نشد (در
    این حالت فونت پیش‌فرض Kivy دست‌نخورده می‌ماند و فارسی مربع نشان داده می‌شود
    -- تماس‌گیرنده باید این را به‌صراحت لاگ کند).

    label_base / default_font_name فقط برای تست تزریق می‌شوند؛ در اجرای واقعی
    از خودِ Kivy گرفته می‌شوند."""
    family = resolve_font_family(fonts_dir)
    if family is None:
        return None
    if label_base is None:
        from kivy.core.text import LabelBase
        label_base = LabelBase
        try:
            from kivy.core.text import DEFAULT_FONT
            default_font_name = DEFAULT_FONT
        except ImportError:
            default_font_name = _FALLBACK_DEFAULT_FONT_NAME
    elif default_font_name is None:
        default_font_name = _FALLBACK_DEFAULT_FONT_NAME
    regular_path, bold_path = family
    label_base.register(default_font_name, fn_regular=regular_path, fn_bold=bold_path)
    return family
