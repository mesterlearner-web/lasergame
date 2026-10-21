"""
هسته‌ی ECS -- کلاس پایه‌ی System

System فقط منطق است؛ روی مجموعه‌ای از Entity ها که کامپوننت‌های
مشخصی دارند عمل می‌کند. هر زیرکلاس باید required_components و
priority را تعریف کند و update() را پیاده‌سازی کند.

ترتیب اولویت استاندارد پروژه (طبق فایل مرجع):
Input=10, Timer=20, Physics=30, Raycast=40, Collision=50,
Animation=60, Particle=70, Audio=80, Render=90, UI=100
"""


class System:
    """کلاس پایه‌ی همه‌ی سیستم‌ها."""

    #: ترتیب اجرا در World.update -- عدد کمتر = زودتر اجرا می‌شود
    priority = 0

    #: تاپل کلاس‌های Component که این سیستم روی‌شان کار می‌کند
    required_components = ()

    def get_entities(self, world):
        """همه‌ی Entity های فعالی که required_components را دارند."""
        return world.get_entities_with(*self.required_components)

    def update(self, dt, world):
        raise NotImplementedError
