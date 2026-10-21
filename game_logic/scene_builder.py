"""
game_logic/scene_builder.py

منطق ساخت صحنه و تبدیل Entity های ECS به فرمت موردنیاز موتور
Raycasting -- عمداً کاملاً مستقل از Kivy نگه داشته شده تا بدون
هیچ وابستگی گرافیکی‌ای قابل تست باشد (main.py فقط این توابع را
صدا می‌زند، منطق واقعی اینجاست).
"""

from ecs.components.position import Position
from ecs.components.mirror import Mirror
from ecs.components.target import Target
from ecs.components.obstacle import Obstacle
from ecs.components.portal import Portal
from ecs.components.prism import Prism
from ecs.components.black_hole import BlackHole

TARGET_RADIUS = 40.0
GUN_Y = 180.0  # نزدیک پایین صفحه -- طبق قرارداد مختصات Y-رو-به-بالا (فایل مرجع، بخش ۲.۲)


def build_scene_from_level(world, level):
    """یک Level واقعی (بارگذاری‌شده از JSON) را در world می‌سازد.
    برمی‌گرداند (gun_x, gun_y)."""
    return level.populate_world(world)


def build_test_scene(world, screen_width, screen_height):
    """یک آینه و یک هدف نمونه برای فاز ۱ می‌سازد و (gun_x, gun_y) را برمی‌گرداند."""
    gun_x = screen_width / 2.0

    mirror_entity = world.create_entity()
    world.add_component(
        mirror_entity, Mirror,
        x1=screen_width * 0.20, y1=screen_height * 0.45,
        x2=screen_width * 0.55, y2=screen_height * 0.62,
        mirror_type='normal', reflectivity=1.0,
    )

    target_entity = world.create_entity()
    world.add_component(target_entity, Position, x=screen_width * 0.25, y=screen_height * 0.85)
    world.add_component(
        target_entity, Target,
        hp=1, max_hp=1, move_pattern='static',
        origin_x=screen_width * 0.25, origin_y=screen_height * 0.85,
        radius=TARGET_RADIUS,
    )

    return gun_x, GUN_Y


def entities_to_surfaces(world):
    """تبدیل Entity های ECS به لیست دیکشنری‌های موردنیاز raycast.cast().

    - آینه‌ها و موانع -> shape='segment'
    - هدف‌ها          -> shape='circle'  (فقط اگر hp>0)
    """
    surfaces = []

    for e in world.get_entities_with(Mirror):
        m = e.get_component(Mirror)
        surfaces.append({
            'shape': 'segment', 'type': m.mirror_type,
            'x1': m.x1, 'y1': m.y1, 'x2': m.x2, 'y2': m.y2,
            'id': e.id,
        })

    for e in world.get_entities_with(Obstacle):
        o = e.get_component(Obstacle)
        surfaces.append({
            'shape': 'segment', 'type': 'obstacle',
            'x1': o.x1, 'y1': o.y1, 'x2': o.x2, 'y2': o.y2,
            'id': e.id,
        })

    for e in world.get_entities_with(Position, Target):
        pos = e.get_component(Position)
        tgt = e.get_component(Target)
        if tgt.hp <= 0:
            continue
        surfaces.append({
            'shape': 'circle', 'type': 'target',
            'x': pos.x, 'y': pos.y, 'radius': tgt.radius,
            'id': e.id,
        })

    for e in world.get_entities_with(Position, Portal):
        pos = e.get_component(Position)
        pt = e.get_component(Portal)
        surfaces.append({
            'shape': 'circle', 'type': 'portal',
            'x': pos.x, 'y': pos.y, 'radius': pt.radius,
            'exit_x': pt.exit_x, 'exit_y': pt.exit_y, 'exit_angle': pt.exit_angle,
            'id': e.id,
        })

    for e in world.get_entities_with(Position, Prism):
        pos = e.get_component(Position)
        pr = e.get_component(Prism)
        surfaces.append({
            'shape': 'circle', 'type': 'prism',
            'x': pos.x, 'y': pos.y, 'radius': pr.radius,
            'id': e.id,
        })

    for e in world.get_entities_with(Position, BlackHole):
        pos = e.get_component(Position)
        bh = e.get_component(BlackHole)
        surfaces.append({
            'shape': 'circle', 'type': 'black_hole',
            'x': pos.x, 'y': pos.y, 'radius': bh.radius,
            'emit_x': bh.emit_x, 'emit_y': bh.emit_y,
            'id': e.id,
        })

    return surfaces
