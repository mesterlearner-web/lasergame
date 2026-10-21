"""
هسته‌ی ECS -- کلاس Entity

Entity فقط یک شناسه‌ست؛ هیچ داده یا منطقی ندارد.
داده‌ها در Component ها نگه داشته می‌شوند، منطق در System ها.
"""


class Entity:
    """نماینده‌ی یک شیء بازی. فقط یک ظرف برای Component هاست."""

    _next_id = 0

    __slots__ = ('id', 'components', 'active')

    def __init__(self):
        self.id = Entity._next_id
        Entity._next_id += 1
        self.components = {}
        self.active = True

    def add_component(self, component_type, **kwargs):
        """یک کامپوننت جدید می‌سازد و به این Entity اضافه می‌کند.

        نکته: برای ثبت صحیح در ایندکس World (تا Query ها کار کنند)،
        باید از World.add_component استفاده شود، نه مستقیماً از این متد.
        """
        component = component_type(**kwargs)
        self.components[component_type] = component
        return component

    def get_component(self, component_type):
        return self.components.get(component_type)

    def has_component(self, component_type):
        return component_type in self.components

    def has_components(self, *component_types):
        return all(ct in self.components for ct in component_types)

    def remove_component(self, component_type):
        self.components.pop(component_type, None)

    def __repr__(self):
        comp_names = [c.__name__ for c in self.components]
        return f"<Entity id={self.id} active={self.active} components={comp_names}>"
