"""
tools/generate_icons.py  (فاز ۱۰)

تولید آیکن برنامه (assets/icon.png، ۵۱۲×۵۱۲) و صفحه‌ی ورود (assets/presplash.png، ۵۱۲×۵۱۲ روی
رنگ زمینه‌ی ثابت). قبلاً APK آیکن/presplash پیش‌فرض Kivy را داشت.

طرح: پس‌زمینه‌ی تیره‌ی گرادیانی، یک پرتو لیزر که از پایین-چپ شلیک و بین دو آینه کمانه می‌کند و به
یک هدف (حلقه‌ی هم‌مرکز) می‌رسد. رنگ‌ها از core/color_palette.py (حالت پیش‌فرض) -- با فallback.

وابستگی: Pillow (فقط ابزار زمان توسعه؛ خروجی commit می‌شود).
اجرا:  python tools/generate_icons.py
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SIZE = 512
BG_TOP = (14, 14, 32)
BG_BOTTOM = (6, 6, 16)
#: همان رنگ در buildozer.spec (android.presplash_color) -- باید یکی بمانند.
PRESPLASH_COLOR = '#060610'

LASER = (255, 60, 80)
LASER_GLOW = (255, 60, 80)
MIRROR = (120, 200, 255)
TARGET = (255, 204, 0)


def _gradient():
    img = Image.new('RGB', (SIZE, SIZE))
    px = img.load()
    for y in range(SIZE):
        t = y / (SIZE - 1)
        c = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3))
        for x in range(SIZE):
            px[x, y] = c
    return img


def _scene_points():
    # مسیر: اسلحه (پایین-چپ) -> آینه‌ی راست -> آینه‌ی چپ -> هدف (بالا-راست)
    gun = (110, 420)
    m1 = (400, 300)
    m2 = (140, 190)
    target = (370, 100)
    return gun, m1, m2, target


def draw_icon():
    base = _gradient().convert('RGBA')
    gun, m1, m2, target = _scene_points()

    glow = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.line([gun, m1, m2, target], fill=LASER_GLOW + (200,), width=34, joint='curve')
    glow = glow.filter(ImageFilter.GaussianBlur(16))
    base = Image.alpha_composite(base, glow)

    d = ImageDraw.Draw(base)

    # هدف: سه حلقه‌ی هم‌مرکز
    tx, ty = target
    for r, w in ((58, 9), (38, 9), (18, 0)):
        if w:
            d.ellipse([tx - r, ty - r, tx + r, ty + r], outline=TARGET + (255,), width=w)
        else:
            d.ellipse([tx - r, ty - r, tx + r, ty + r], fill=TARGET + (255,))

    # آینه‌ها: خط ضخیم مایل با لبه‌ی روشن
    def mirror(center, angle_dx, angle_dy):
        cx, cy = center
        p1 = (cx - angle_dx, cy - angle_dy)
        p2 = (cx + angle_dx, cy + angle_dy)
        d.line([p1, p2], fill=(40, 90, 130, 255), width=26)
        d.line([p1, p2], fill=MIRROR + (255,), width=14)

    mirror(m1, 40, 70)
    mirror(m2, 70, 25)

    # خود پرتو، روشن‌تر روی هاله
    d.line([gun, m1, m2, target], fill=(255, 235, 235, 255), width=10, joint='curve')
    d.line([gun, m1, m2, target], fill=LASER + (255,), width=6, joint='curve')

    # اسلحه
    gx, gy = gun
    d.ellipse([gx - 34, gy - 34, gx + 34, gy + 34], fill=(150, 150, 175, 255))
    d.ellipse([gx - 16, gy - 16, gx + 16, gy + 16], fill=(60, 60, 80, 255))

    return base.convert('RGB')


def draw_presplash(icon):
    # آیکن در مرکز روی رنگ ثابت؛ p4a خودش بزرگ/کوچک و وسط‌چین می‌کند.
    bg = Image.new('RGB', (SIZE, SIZE), PRESPLASH_COLOR)
    small = icon.resize((320, 320), Image.LANCZOS)
    bg.paste(small, ((SIZE - 320) // 2, (SIZE - 320) // 2))
    return bg


def main():
    out_dir = os.path.join(ROOT, 'assets')
    os.makedirs(out_dir, exist_ok=True)
    icon = draw_icon()
    icon.save(os.path.join(out_dir, 'icon.png'), optimize=True)
    draw_presplash(icon).save(os.path.join(out_dir, 'presplash.png'), optimize=True)
    for n in ('icon.png', 'presplash.png'):
        print(n, os.path.getsize(os.path.join(out_dir, n)) // 1024, 'KB')
    return 0


if __name__ == '__main__':
    sys.exit(main())
