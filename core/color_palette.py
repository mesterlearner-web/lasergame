"""
core/color_palette.py  (فاز ۶)

پالت رنگ *صحنه‌ی بازی* (لیزر/آینه/هدف/پورتال/مانع/سیاه‌چاله/منشور) -- طبق
فایل مرجع بخش ۵.۱۶. رنگ‌های UI منو (جواهر/دکمه‌ی اصلی/دکمه‌ی ثانوی)
طبق همون بخش ثابت‌ان و به COLOR_BLIND_MODE واکنش نشون نمی‌دن (از فاز۵،
در ui/widgets/common.py، از قبل با همین مقادیر پیاده شده بودن).

⚠️ نکته‌ی مستندسازی: فایل مرجع می‌گه `ColorPalette` باید `get_laser_
color`/`get_portal_color`/`get_mirror_color` رو هم به COLOR_BLIND_MODE
حساس کنه، «الان فقط get_target_color حساسه» -- یعنی این کلاس قبلاً در
یکی از پرامپت‌های خام (بخش۵/۶) با پیاده‌سازی ناقص وجود داشته. آن متن
خام در این جلسه در دسترس نیست؛ چون هیچ نسخه‌ی جزئی‌ای از این کلاس در
کدِ واقعی پروژه (فاز۱ تا ۵) وجود نداشت، این‌جا از صفر و کامل (هر ۴
متد از همون ابتدا حساس به رنگ‌کوری) نوشته شد -- نه فقط ۳ متدِ باقی‌مانده
اضافه شدن.

اصل طراحی: در *هر* حالت (عادی یا هرکدوم از ۳ نوع کوررنگی)، همه‌ی ۷
عنصر باید از هم قابل‌تشخیص باشن. باگ دقیقی که بخش۵.۱۶ توصیف می‌کنه
همین بود: رنگ جایگزین لیزر و رنگ جایگزین هدف در حالت Protanopia یکی
بودن (هردو #FFCC00) -- یعنی درست همون‌جایی که تنظیم کوررنگی باید کمک
می‌کرد، بازی عملاً غیرقابل‌تشخیص می‌شد. مقادیر Protanopia زیر دقیقاً
از فایل مرجع کپی شدن (لیزر=#FF6699، هدف=#FFCC00 بدون تغییر)؛ مقادیر
Deuteranopia/Tritanopia چون در فایل مرجع داده نشده بودن ("Tritanopia
رو هم پوشش بده" -- یعنی تا الان پوشش نداشته)، با همون اصل «۷ عنصر
قابل‌افتراق» از صفر طراحی شدن: Deuteranopia (قرمز/سبز غیرقابل‌افتراق)
از طیف آبی/زرد/بنفش استفاده می‌کنه؛ Tritanopia (آبی/زرد غیرقابل‌افتراق)
از طیف قرمز/صورتی/سبز.
"""

#: رنگ‌های ثابت UI منو -- طبق بخش۵.۱۶، به COLOR_BLIND_MODE حساس نیستن.
#: (پیاده‌سازی واقعی‌شون از فاز۵ در ui/widgets/common.py هست؛ اینجا فقط
#: برای مرجع/مستندسازی مرکزی تکرار شدن.)
UI_GEM = '#B84DFF'
UI_PRIMARY_BUTTON = '#33DDAA'
UI_SECONDARY_BUTTON = '#8855DD'

VALID_MODES = (None, 'protanopia', 'deuteranopia', 'tritanopia')

_PALETTES = {
    None: {
        'laser': '#00FFFF',
        'mirror': '#C0C8FF',
        'target': '#FF3366',
        'portal': '#B84DFF',
        'obstacle': '#8899AA',
        'black_hole': '#2A1A40',
        'prism': '#FFDD55',
    },
    'protanopia': {
        'laser': '#FF6699',       # طبق بخش۵.۱۶ -- جایگزین شد که با هدف یکی نباشه
        'target': '#FFCC00',      # طبق بخش۵.۱۶ -- «بدون تغییر»
        'mirror': '#AACCFF',
        'portal': '#6699FF',
        'obstacle': '#99AABB',
        'black_hole': '#332244',
        'prism': '#66DDCC',
    },
    'deuteranopia': {
        # قرمز/سبز قابل‌افتراق نیست -- طیف آبی/زرد/بنفش
        'laser': '#3399FF',
        'target': '#FFCC00',
        'mirror': '#CCCCEE',
        'portal': '#9966FF',
        'obstacle': '#999999',
        'black_hole': '#221133',
        'prism': '#55E0C0',
    },
    'tritanopia': {
        # آبی/زرد قابل‌افتراق نیست -- طیف قرمز/صورتی/سبز
        'laser': '#FF3399',
        'target': '#33CC66',
        'mirror': '#EEDDDD',
        'portal': '#FF6666',
        'obstacle': '#AA8888',
        'black_hole': '#331122',
        'prism': '#FFAA33',
    },
}

#: طبق بخش۵.۸/۵.۱۹ -- رنگ حلقه‌ی تایمر (TimerRing، همین فاز) بر پایه‌ی
#: همون ۵ تایرِ درصدیِ performance_tier، نه یک سیستم رنگ جدا.
_TIMER_RING_COLORS = {
    None: {
        'legendary': '#33DDAA', 'excellent': '#88DD44', 'great': '#DDCC33',
        'good': '#DD8833', 'close': '#DD3333',
    },
    'protanopia': {
        'legendary': '#3399FF', 'excellent': '#66AAFF', 'great': '#CCCC33',
        'good': '#FF9933', 'close': '#FF6699',
    },
    'deuteranopia': {
        'legendary': '#3399FF', 'excellent': '#66AAFF', 'great': '#CCCC33',
        'good': '#FF9933', 'close': '#FFCC00',
    },
    'tritanopia': {
        'legendary': '#33CC66', 'excellent': '#77CC44', 'great': '#DD8888',
        'good': '#FF6666', 'close': '#FF3399',
    },
}


def hex_to_rgba(hex_color, alpha=1.0):
    """'#RRGGBB' -> (r, g, b, a) با مقادیر ۰..۱ -- برای Color(*..)ی Kivy."""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return (r, g, b, alpha)


class ColorPalette:
    def __init__(self, colorblind_mode=None):
        if colorblind_mode not in VALID_MODES:
            raise ValueError(f"حالت رنگ‌کوری ناشناخته: {colorblind_mode!r}")
        self.colorblind_mode = colorblind_mode

    def _palette(self):
        return _PALETTES[self.colorblind_mode]

    def get_laser_color(self, alpha=1.0):
        return hex_to_rgba(self._palette()['laser'], alpha)

    def get_mirror_color(self, alpha=1.0):
        return hex_to_rgba(self._palette()['mirror'], alpha)

    def get_target_color(self, alpha=1.0):
        return hex_to_rgba(self._palette()['target'], alpha)

    def get_portal_color(self, alpha=1.0):
        return hex_to_rgba(self._palette()['portal'], alpha)

    def get_obstacle_color(self, alpha=1.0):
        return hex_to_rgba(self._palette()['obstacle'], alpha)

    def get_black_hole_color(self, alpha=1.0):
        return hex_to_rgba(self._palette()['black_hole'], alpha)

    def get_prism_color(self, alpha=1.0):
        return hex_to_rgba(self._palette()['prism'], alpha)

    def get_timer_ring_color(self, tier, alpha=1.0):
        colors = _TIMER_RING_COLORS[self.colorblind_mode]
        return hex_to_rgba(colors.get(tier, colors['close']), alpha)

    def all_scene_colors_distinct(self):
        """True اگه هر ۷ رنگ صحنه‌ی بازی در حالت فعلی واقعاً از هم
        متفاوت باشن -- خودِ تعریف عملیاتیِ باگی که بخش۵.۱۶ توصیف
        می‌کنه (لیزر/هدف یکی بودن در Protanopia)."""
        values = list(self._palette().values())
        return len(set(values)) == len(values)
