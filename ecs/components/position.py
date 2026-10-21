from ecs.component import Component


class Position(Component):
    """موقعیت مکانی -- در سیستم مختصات بومی Kivy
    (محور Y رو به بالا، مبدأ گوشه‌ی پایین-چپ صفحه؛ بدون هیچ تبدیلی)."""
    __slots__ = ('x', 'y')

    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y
