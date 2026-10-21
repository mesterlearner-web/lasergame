"""
هسته‌ی ECS -- کلاس World

World نگهدارنده‌ی تمام Entity ها، Component ها (به‌صورت ایندکس‌شده
برای Query سریع بر اساس نوع Component) و System هاست. همچنین
Object Pooling برای Entity ها را مدیریت می‌کند تا از GC Pause
جلوگیری شود (طبق فلسفه‌ی بهینه‌سازی فایل مرجع، بخش ۵.۱).

نکته‌ی مهم درباره‌ی world.entities:
این لیست شامل همه‌ی Entity هایی است که تا حالا ساخته شده‌اند -- حتی
آن‌هایی که الان در Pool و غیرفعالند. برای گرفتن فقط Entity های
فعال، همیشه از world.get_entities_with(...) استفاده کنید، نه
پیمایش مستقیم world.entities.
"""

from ecs.entity import Entity


class World:
    def __init__(self):
        self.entities = []
        self.systems = []
        self._entity_pool = []
        # ایندکس: component_type -> set(Entity) -- برای Query سریع بدون
        # نیاز به پیمایش کامل لیست entities در هر فریم
        self._component_index = {}

    # ---------- مدیریت Entity ----------

    def create_entity(self):
        """یک Entity جدید می‌سازد یا یکی را از Pool برمی‌گرداند."""
        if self._entity_pool:
            entity = self._entity_pool.pop()
            entity.active = True
        else:
            entity = Entity()
            self.entities.append(entity)
        return entity

    def destroy_entity(self, entity):
        """Entity را غیرفعال کرده و به Pool برمی‌گرداند."""
        if not entity.active:
            return
        entity.active = False
        for component_type in list(entity.components.keys()):
            bucket = self._component_index.get(component_type)
            if bucket is not None:
                bucket.discard(entity)
        entity.components.clear()
        self._entity_pool.append(entity)

    # ---------- مدیریت Component ----------

    def add_component(self, entity, component_type, **kwargs):
        """راه توصیه‌شده برای افزودن کامپوننت -- هم به Entity اضافه
        می‌کند هم در ایندکس World ثبت می‌کند تا Query ها درست کار کنند."""
        component = entity.add_component(component_type, **kwargs)
        self._component_index.setdefault(component_type, set()).add(entity)
        return component

    def remove_component(self, entity, component_type):
        entity.remove_component(component_type)
        bucket = self._component_index.get(component_type)
        if bucket is not None:
            bucket.discard(entity)

    def get_entities_with(self, *component_types):
        """Entity های فعالی که همه‌ی component_types داده‌شده را دارند."""
        if not component_types:
            return []
        sets = []
        for ct in component_types:
            bucket = self._component_index.get(ct)
            if not bucket:
                return []  # اگر یکی از کامپوننت‌ها هیچ عضوی ندارد، نتیجه خالی است
            sets.append(bucket)
        common = sets[0]
        for s in sets[1:]:
            common = common & s
        return [e for e in common if e.active]

    # ---------- مدیریت System ----------

    def add_system(self, system):
        self.systems.append(system)
        self.systems.sort(key=lambda s: s.priority)

    def update(self, dt):
        for system in self.systems:
            system.update(dt, self)

    # ---------- پاکسازی کامل (هنگام خروج از صحنه) ----------

    def cleanup(self):
        for entity in self.entities:
            entity.components.clear()
            entity.active = False
        self.entities.clear()
        self._entity_pool.clear()
        self._component_index.clear()
