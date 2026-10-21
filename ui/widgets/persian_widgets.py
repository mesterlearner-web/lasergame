"""
ui/widgets/persian_widgets.py  (فاز ۵)

طبق قاعده‌ی سراسری فایل مرجع (بخش ۵.۱۹): «shape() باید قبل از هر متن
فارسی‌ای که روی هر Label/Button/TextInput در کل برنامه نمایش داده
می‌شود صدا زده شود، بدون استثنا.»

به‌جای این‌که هر صفحه (۸ صفحه‌ی همین فاز، به‌علاوه‌ی هرچی فازهای بعدی
اضافه کنن) خودش یادش بمونه shape() رو صدا بزنه، این‌جا یک‌بار در دو
ویجت مرکزی تضمین می‌شه -- دقیقاً همون منطقی که باعث شد phase۱
`scene_builder.py` رو از `main.py` جدا نگه داره: یک قانون حساس، یک‌جا،
نه پخش در ده‌ها فایل که یکیشون ممکنه یادش بره.

قرارداد: متن *خام* (فارسی، shape-نشده) همیشه از طریق `text=` در
سازنده یا متد `set_text()` داده می‌شه -- هیچ‌وقت مستقیم به `self.text`
دست نمی‌زنیم. `raw_text` نسخه‌ی shape-نشده رو برای مقایسه/دیباگ نگه
می‌داره.

فاز۸ -- شکستن خط راست‌به‌چپ: وقتی `text_size` عرض داشته باشد (تقریباً همه‌ی برچسب‌ها)،
متن *قبل از* shape شکسته می‌شود و هر خط جداگانه shape می‌شود. وگرنه shape کل جمله را
برعکس می‌کرد و Kivy بعد آن را می‌شکست: خط اول *آخر* جمله را نشان می‌داد (ترتیب خطوط
وارونه). اگر اندازه‌گیری شکست بخورد، به رفتار قبلی (بدون شکستن) برمی‌گردد -- خراب‌تر
از قبل نمی‌شود.
"""
from kivy.logger import Logger
from kivy.uix.button import Button
from kivy.uix.label import Label

from utils.persian_text import shape, wrap_logical_text

#: کمی کمتر از عرض کامل: اگر اندازه‌گیری ما با اندازه‌گیری خودِ Kivy (hinting/kerning)
#: چند پیکسل فرق کند، Kivy خطی را که ما ساخته‌ایم دوباره نشکند (که وارونگی را برای همان
#: یک خط برمی‌گرداند).
WRAP_SAFETY = 0.98


class PersianLabel(Label):
    def __init__(self, **kwargs):
        raw = kwargs.pop('text', '')
        super().__init__(**kwargs)
        self.raw_text = ''
        self._core_label = None
        self._core_key = None
        self._measure_failed = False
        self._applied = False
        # هر چیزی که عرض خط یا اندازه‌ی متن را عوض می‌کند باید دوباره بشکند.
        self.bind(text_size=self._reflow, font_size=self._reflow,
                  font_name=self._reflow, bold=self._reflow)
        self.set_text(raw)

    def set_text(self, raw_text):
        # فاز۱۰: GameWidget هر فریم (۶۰بار/ثانیه) همان متن HUD را دوباره می‌دهد؛ با شکستن خط RTL
        # (اندازه‌گیری هر خط) این روی گوشی گران است. متن یکسان => هیچ کاری.
        if self._applied and raw_text == self.raw_text:
            return
        self._applied = True
        self.raw_text = raw_text
        self._reflow()

    def _measure_logical(self, line):
        """عرض پیکسلی یک خط منطقی بعد از shape، با همان فونتی که رسم می‌شود."""
        key = (self.font_size, self.font_name, self.bold)
        if self._core_label is None or self._core_key != key:
            from kivy.core.text import Label as CoreLabel
            self._core_label = CoreLabel(font_size=self.font_size, font_name=self.font_name,
                                         bold=self.bold)
            self._core_key = key
        return self._core_label.get_extents(shape(line))[0]

    def _reflow(self, *_args):
        raw = self.raw_text
        width = self.text_size[0] if self.text_size else None
        if not raw or not width or width <= 0 or self._measure_failed:
            self.text = shape(raw)
            return
        try:
            lines = wrap_logical_text(raw, width * WRAP_SAFETY, self._measure_logical)
        except Exception as exc:  # noqa: BLE001 -- هر خطای اندازه‌گیری -> رفتار قبلی، نه کرش
            self._measure_failed = True
            Logger.warning('LaserRicochet: RTL line-wrap measurement failed (%r); '
                           'falling back to unwrapped text', exc)
            self.text = shape(raw)
            return
        self.text = '\n'.join(shape(line) for line in lines)


class PersianButton(Button):
    #: فاز۱۰: تابع بدون‌آرگومانی که main.py ست می‌کند (پخش صدای «button_tap»)؛ None => سکوت.
    #: روی کلاس است تا هر دکمه‌ی برنامه بدون سیم‌کشی تکی صدا بدهد.
    tap_sound = None

    def on_press(self, *args):
        hook = PersianButton.tap_sound
        if hook is not None:
            try:
                hook()
            except Exception as exc:  # noqa: BLE001 -- صدا هرگز نباید لمس را بشکند
                Logger.warning('LaserRicochet: button tap sound failed (%r)', exc)
        return super().on_press()

    def __init__(self, **kwargs):
        raw = kwargs.pop('text', '')
        super().__init__(**kwargs)
        self.raw_text = ''
        self.set_text(raw)

    def set_text(self, raw_text):
        self.raw_text = raw_text
        self.text = shape(raw_text)
