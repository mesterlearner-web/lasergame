"""
tools/generate_levels.py  (فاز ۹ -- فقط زمان توسعه، داخل APK بسته‌بندی نمی‌شود)

مراحل ۶ تا ۱۰۰ کمپین را با مولد رویه‌ای (game_logic/level_generator.py) تولید و به صورت فایل‌های
`assets/levels/level_NNN.json` می‌نویسد. چرا فایل (نه تولید در لحظه‌ی اجرا)؟
  * همه‌ی بازیکن‌ها دقیقاً همان ۱۰۰ مرحله را دارند، روی هر معماری/نسخه‌ی پایتون؛
  * قابل‌بازبینی و diff (بخشی از مرحله‌ها دستی‌اند، بقیه تولیدی -- همان قالب فشرده)؛
  * بدون هزینه‌ی تولید (تا ۸۵۰ میلی‌ثانیه برای مراحل استاد) هنگام ورود به مرحله روی گوشی؛
  * تست‌ها حل‌پذیری *فایل‌های واقعی* را می‌سنجند.
مولد نیمه‌دستی نیست: مراحل ۱ تا ۵ دستی‌اند و هرگز بازنویسی نمی‌شوند.

استفاده:
    python tools/generate_levels.py           # نوشتن level_006..100
    python tools/generate_levels.py --check   # فقط مقایسه: فایل‌ها با خروجی مولد یکی‌اند؟ (exit 1 اگر نه)
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from game_logic.difficulty_manager import TOTAL_LEVELS  # noqa: E402
from game_logic.level_generator import format_level_json, generate_level  # noqa: E402

FIRST_GENERATED = 6
LEVELS_DIR = os.path.join(ROOT, 'assets', 'levels')


def level_path(level_id):
    return os.path.join(LEVELS_DIR, f'level_{level_id:03d}.json')


def main(argv=None):
    check = '--check' in (sys.argv[1:] if argv is None else argv)
    differing, fallbacks, written = [], [], 0
    for level_id in range(FIRST_GENERATED, TOTAL_LEVELS + 1):
        data, info = generate_level(level_id, with_info=True)
        if info['fallback']:
            fallbacks.append(level_id)
        text = format_level_json(data)
        path = level_path(level_id)
        if check:
            current = open(path, encoding='utf-8').read() if os.path.isfile(path) else None
            if current != text:
                differing.append(level_id)
        else:
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(text)
            written += 1
    if fallbacks:
        print(f"⚠️ مولد برای این مراحل به fallback (شلیک مستقیم) رسید: {fallbacks}")
    if check:
        print(f"مقایسه: {'همه‌ی فایل‌ها با مولد یکی‌اند' if not differing else f'{len(differing)} فایل متفاوت: {differing[:10]}'}")
        return 1 if (differing or fallbacks) else 0
    print(f"{written} فایل نوشته شد ({FIRST_GENERATED}..{TOTAL_LEVELS})")
    return 1 if fallbacks else 0


if __name__ == '__main__':
    sys.exit(main())
