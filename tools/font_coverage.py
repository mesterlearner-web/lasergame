"""
tools/font_coverage.py  (فاز ۸ -- فقط زمان build/توسعه، داخل APK بسته‌بندی نمی‌شود)

بررسی می‌کند فونتِ بسته‌بندی‌شده *واقعاً* همه‌ی گلیف‌هایی را دارد که UI نیاز دارد.

چرا «حرف پایه داشتن» کافی نیست: Kivy (SDL2_ttf) هیچ shaping ای انجام نمی‌دهد --
`arabic_reshaper` متن را به کدپوینت‌های «Presentation Forms» (U+FB50..FDFF و
U+FE70..FEFF) تبدیل می‌کند و فونت باید *همان کدپوینت‌ها* را داشته باشد، نه فقط
حروف پایه‌ی U+0600..06FF. اگر یکی نباشد، فقط همان شکلِ حرف مربع می‌شود (باگی که
در تست دستی با چند کلمه‌ی ساده دیده نمی‌شود ولی در یک کلمه‌ی خاص ظاهر می‌شود).

«لازم» یعنی: هر کاراکتر غیر-ASCII رشته‌های UI + همه‌ی اشکال پیوسته‌ی (مجزا/آغازی/
میانی/پایانی) هر حرف عربی‌خط استفاده‌شده + لیگاچرهای لام‌الف (تنها لیگاچر اجباری
arabic_reshaper) + نیم‌فاصله (ZWNJ). لیگاچرهای اختیاری دوحرفی (لام+جیم و ...) عمداً
لازم حساب نمی‌شوند: arabic_reshaper در پیکربندی پیش‌فرض تولیدشان نمی‌کند.

بدون وابستگی به fontTools (روی CI نصب نیست): خواننده‌ی cmap فرمت‌های ۴ و ۱۲ اینجاست.
استفاده:  python tools/font_coverage.py [font.ttf ...]   (پیش‌فرض: فونت‌های assets/fonts)
"""
import ast
import json
import os
import re
import struct
import sys
import unicodedata

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ARABIC_RE = re.compile('[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
ZWNJ = 0x200C
LAM_ALEF_LIGATURES = tuple(range(0xFEF5, 0xFEFC + 1))
_SKIP_DIRS = {'tests', 'tools', 'native', 'docs', 'bin', '__pycache__'}


# ---------------------------------------------------------------- cmap reader

def read_cmap(path):
    """مجموعه‌ی کدپوینت‌هایی که فونت برایشان گلیف (غیر از .notdef) دارد.
    فرمت‌های ۴ (BMP) و ۱۲ (کامل) را می‌خواند؛ برای فایل‌های TTF/OTF-glyf معمول کافی است."""
    with open(path, 'rb') as fh:
        data = fh.read()
    num_tables = struct.unpack_from('>H', data, 4)[0]
    cmap_offset = None
    for i in range(num_tables):
        tag, _checksum, offset, _length = struct.unpack_from('>4sIII', data, 12 + 16 * i)
        if tag == b'cmap':
            cmap_offset = offset
            break
    if cmap_offset is None:
        raise ValueError(f"{path}: جدول cmap پیدا نشد")

    _version, n_sub = struct.unpack_from('>HH', data, cmap_offset)
    codepoints = set()
    for i in range(n_sub):
        platform_id, encoding_id, sub_off = struct.unpack_from('>HHI', data, cmap_offset + 4 + 8 * i)
        unicode_capable = platform_id == 0 or (platform_id == 3 and encoding_id in (1, 10))
        if not unicode_capable:
            continue
        base = cmap_offset + sub_off
        fmt = struct.unpack_from('>H', data, base)[0]
        if fmt == 4:
            codepoints |= _parse_format4(data, base)
        elif fmt == 12:
            codepoints |= _parse_format12(data, base)
    return codepoints


def _parse_format4(data, base):
    seg_count = struct.unpack_from('>H', data, base + 6)[0] // 2
    end_pos = base + 14
    start_pos = end_pos + seg_count * 2 + 2
    delta_pos = start_pos + seg_count * 2
    range_pos = delta_pos + seg_count * 2
    result = set()
    for s in range(seg_count):
        end_code = struct.unpack_from('>H', data, end_pos + 2 * s)[0]
        start_code = struct.unpack_from('>H', data, start_pos + 2 * s)[0]
        id_delta = struct.unpack_from('>h', data, delta_pos + 2 * s)[0]
        id_range_offset = struct.unpack_from('>H', data, range_pos + 2 * s)[0]
        for code in range(start_code, end_code + 1):
            if code == 0xFFFF:
                continue
            if id_range_offset == 0:
                glyph = (code + id_delta) & 0xFFFF
            else:
                glyph_pos = range_pos + 2 * s + id_range_offset + 2 * (code - start_code)
                glyph = struct.unpack_from('>H', data, glyph_pos)[0]
                if glyph != 0:
                    glyph = (glyph + id_delta) & 0xFFFF
            if glyph != 0:
                result.add(code)
    return result


def _parse_format12(data, base):
    n_groups = struct.unpack_from('>I', data, base + 12)[0]
    result = set()
    for g in range(n_groups):
        start, end, start_glyph = struct.unpack_from('>III', data, base + 16 + 12 * g)
        for code in range(start, end + 1):
            if start_glyph + (code - start) != 0:
                result.add(code)
    return result


# ---------------------------------------------------------- required codepoints

def _is_docstring(node, parent):
    return (isinstance(parent, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and parent.body and parent.body[0] is node)


def collect_ui_strings(project_root=PROJECT_ROOT):
    """همه‌ی ثابت‌های رشته‌ای کد (به‌جز docstring) + مقادیر رشته‌ای فایل‌های JSON داده/مرحله.
    این یک ابرمجموعه‌ی امن از «متنی که ممکنه نمایش داده بشه»ست."""
    strings = []
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in _SKIP_DIRS]
        for name in files:
            path = os.path.join(root, name)
            if name.endswith('.py'):
                with open(path, encoding='utf-8') as fh:
                    tree = ast.parse(fh.read())
                docstrings = set()
                for parent in ast.walk(tree):
                    for child in ast.iter_child_nodes(parent):
                        if (isinstance(child, ast.Expr) and isinstance(child.value, ast.Constant)
                                and isinstance(child.value.value, str) and _is_docstring(child, parent)):
                            docstrings.add(id(child.value))
                for node in ast.walk(tree):
                    if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                            and id(node) not in docstrings):
                        strings.append(node.value)
            elif name.endswith('.json'):
                with open(path, encoding='utf-8') as fh:
                    _collect_json_strings(json.load(fh), strings)
    return strings


def _collect_json_strings(obj, out):
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for value in obj.values():
            _collect_json_strings(value, out)
    elif isinstance(obj, list):
        for value in obj:
            _collect_json_strings(value, out)


def _joining_forms_index():
    """حرف پایه -> اشکال پیوسته‌ی تک‌حرفی‌اش (از دیتابیس خودِ Unicode، نه جدول دستی)."""
    index = {}
    for cp in list(range(0xFB50, 0xFDFF + 1)) + list(range(0xFE70, 0xFEFF + 1)):
        match = re.match(r'<(isolated|initial|medial|final)>\s+([0-9A-F]{4})$',
                         unicodedata.decomposition(chr(cp)))
        if match:
            index.setdefault(int(match.group(2), 16), set()).add(cp)
    return index


def required_codepoints(strings):
    index = _joining_forms_index()
    needed = {ZWNJ}
    saw_arabic_letter = False
    for text in strings:
        for ch in text:
            cp = ord(ch)
            needed.add(cp)
            if ARABIC_RE.match(ch):
                needed |= index.get(cp, set())
                saw_arabic_letter = saw_arabic_letter or ch.isalpha()
    if saw_arabic_letter:
        needed |= set(LAM_ALEF_LIGATURES)
    # کاراکترهای کنترلی (\n \t ...) گلیف نمی‌خوان
    return {cp for cp in needed if cp >= 0x20 and not (0x7F <= cp <= 0x9F)}


def missing_codepoints(font_path, project_root=PROJECT_ROOT, strings=None):
    strings = collect_ui_strings(project_root) if strings is None else strings
    have = read_cmap(font_path)
    return sorted(cp for cp in required_codepoints(strings) if cp not in have)


def describe(cp):
    return f"U+{cp:04X} {unicodedata.name(chr(cp), '?')}"


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        fonts_dir = os.path.join(PROJECT_ROOT, 'assets', 'fonts')
        argv = sorted(os.path.join(fonts_dir, f) for f in os.listdir(fonts_dir) if f.endswith('.ttf'))
    strings = collect_ui_strings()
    need = required_codepoints(strings)
    print(f"{len(strings)} رشته‌ی UI تحلیل شد؛ {len(need)} کدپوینت لازم.")
    bad = 0
    for path in argv:
        missing = missing_codepoints(path, strings=strings)
        status = 'OK' if not missing else f"{len(missing)} گلیف کم دارد"
        print(f"  {os.path.basename(path):28s} {status}")
        for cp in missing[:25]:
            print(f"      - {describe(cp)}")
        bad += bool(missing)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
