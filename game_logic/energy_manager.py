"""
game_logic/energy_manager.py  (فاز ۴)

طبق بخش ۵.۱۱ فایل مرجع: «بدون تغییر از بخش۴ (EnergyManager)، به‌علاوه‌ی
رفع ابهام نام‌گذاری: ... چون سیستم واقعی پیوسته است نه روزانه.»

⚠️ نکته‌ی مستندسازی: متن کامل بخش۴ (که خودِ `EnergyManager` قبلاً در
آن طراحی شده بود) در این جلسه در دسترس نیست -- فقط همین یک خط تأکیدی
(«پیوسته، نه روزانه») از فایل مرجع در دسترسه. مقادیر `max_energy=۵` و
`regen_seconds_per_unit=۹۰۰` (۱۵ دقیقه) اعداد placeholder معقول‌اند
(الگوی رایج در پازل‌های موبایل مشابه)، نه از سند اصلی؛ اگه متن دقیق
بخش۴ بعداً در دسترس قرار گرفت، این اعداد باید با آن جایگزین بشن.

نکته‌ی پیاده‌سازی مهم («واقعاً پیوسته»): این پیاده‌سازی زمان باقی‌مانده
(کسر زمانی که هنوز به یک واحد کامل نرسیده) رو گم نمی‌کنه. اگه
last_update رو ساده‌لوحانه هر بار برابر با «الان» می‌ذاشتیم، هر فراخوانی
update() که وسط یک دوره‌ی بازآفرینی اتفاق می‌افته باعث می‌شد اون کسر
زمانی برای همیشه از دست بره -- یعنی نرخ واقعی بازآفرینی کندتر از عدد
تنظیم‌شده می‌شد. به‌جاش، last_update فقط به‌اندازه‌ی زمانِ واقعاً
«مصرف‌شده» برای واحدهای کامل جلو می‌ره، نه تا «الان».
"""
import time as _time

DEFAULT_MAX_ENERGY = 5
DEFAULT_REGEN_SECONDS_PER_UNIT = 900.0  # ۱۵ دقیقه -- placeholder، بالا توضیح داده شد


class EnergyManager:
    def __init__(self, current_energy=None, max_energy=DEFAULT_MAX_ENERGY,
                 regen_seconds_per_unit=DEFAULT_REGEN_SECONDS_PER_UNIT, last_update=None):
        self.max_energy = max_energy
        self.current_energy = max_energy if current_energy is None else current_energy
        self.regen_seconds_per_unit = regen_seconds_per_unit
        self.last_update = _time.time() if last_update is None else last_update

    @staticmethod
    def _resolve_now(now):
        return _time.time() if now is None else now

    def update(self, now=None):
        """موجودی رو با زمان واقعی سنکرون می‌کنه. باید همیشه با یک
        `now` صریح صدا زده بشه (برای تست‌پذیری)؛ در بازی واقعی، `now`
        همیشه `time.time()` جاریه."""
        now = self._resolve_now(now)
        if self.current_energy >= self.max_energy:
            self.last_update = now
            return
        elapsed = max(0.0, now - self.last_update)
        units_gained = int(elapsed // self.regen_seconds_per_unit)
        if units_gained > 0:
            self.current_energy = min(self.max_energy, self.current_energy + units_gained)
            self.last_update += units_gained * self.regen_seconds_per_unit
            if self.current_energy >= self.max_energy:
                self.last_update = now

    def consume(self, amount=1, now=None):
        """اگر انرژی کافی نباشه، هیچ تغییری نمی‌ده و False برمی‌گردونه."""
        now = self._resolve_now(now)
        self.update(now)
        if self.current_energy < amount:
            return False
        self.current_energy -= amount
        return True

    def apply_regen_speed_upgrade(self, multiplier):
        """طبق بخش ۵.۱۰ -- از ShopManager._apply_item_effect برای
        دسته‌ی 'upgrades' با upgrade_type='regen_speed' صدا زده می‌شه.
        multiplier<1 یعنی بازآفرینی سریع‌تر (زمان کمتر برای هر واحد)."""
        if multiplier <= 0:
            raise ValueError("multiplier باید مثبت باشد")
        self.regen_seconds_per_unit *= multiplier

    def seconds_until_next_unit(self, now=None):
        now = self._resolve_now(now)
        self.update(now)
        if self.current_energy >= self.max_energy:
            return 0.0
        return max(0.0, self.regen_seconds_per_unit - (now - self.last_update))

    def seconds_until_full(self, now=None):
        now = self._resolve_now(now)
        self.update(now)
        if self.current_energy >= self.max_energy:
            return 0.0
        units_needed = self.max_energy - self.current_energy
        return self.seconds_until_next_unit(now) + (units_needed - 1) * self.regen_seconds_per_unit

    def to_dict(self):
        return {
            'current_energy': self.current_energy,
            'max_energy': self.max_energy,
            'regen_seconds_per_unit': self.regen_seconds_per_unit,
            'last_update': self.last_update,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            current_energy=data.get('current_energy'),
            max_energy=data.get('max_energy', DEFAULT_MAX_ENERGY),
            regen_seconds_per_unit=data.get('regen_seconds_per_unit', DEFAULT_REGEN_SECONDS_PER_UNIT),
            last_update=data.get('last_update'),
        )
