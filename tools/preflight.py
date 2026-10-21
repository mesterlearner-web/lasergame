"""
tools/preflight.py  (فاز ۸ -- فقط زمان توسعه/CI، داخل APK بسته‌بندی نمی‌شود)

بررسی‌های آفلاین پیکربندی بیلد. هدف: *هر چیزی* که بدون اجرای بیلد واقعی اندروید
قابل‌اثبات است، قبل از خرج‌کردن ۴۰ دقیقه‌ی بیلد CI اثبات شود -- و باگ‌های واقعی‌ای
که حین ساخت فاز۸ پیدا شدند (فونت فارسی نبود، python-bidi بدون pin بود، پوشه‌ی
asset با پسوند ثبت‌نشده بی‌صدا از APK بیرون می‌ماند، ...) نتوانند بی‌صدا برگردند.

⚠️ صادقانه: این‌ها *شبیه‌سازی* قواعد buildozer هستند (مثلاً simulate_bundle)، نه خودِ
buildozer. تأیید نهایی فقط اجرای واقعی روی GitHub Actions است؛ مرحله‌ی
`--bundle` در CI شبیه‌سازی را با خروجی واقعی buildozer تطبیق می‌دهد.

استفاده:
    python tools/preflight.py                      # همه‌ی بررسی‌ها
    python tools/preflight.py --bundle DIR         # تطبیق با پوشه‌ی واقعی buildozer
"""
import ast
import configparser
import io
import json
import os
import re
import sys
import tokenize

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from tools import font_coverage  # noqa: E402

#: وابستگی‌هایی که طبق فایل مرجع (بخش ۲.۱ / ۴) نباید برگردند. (با همان نرمال‌سازی
#: _req_name مقایسه می‌شوند: حروف کوچک و _ -> -؛ تست منفی نشان داد بدون این، kivent_core رد می‌شد.)
FORBIDDEN_REQUIREMENTS = {name.replace('_', '-') for name in
                          ('kivent', 'cymunk', 'kivent_core', 'kivent_cymunk')}

#: نام ماژول import -> نام requirement در buildozer.spec
IMPORT_TO_REQUIREMENT = {
    'kivy': 'kivy',
    'arabic_reshaper': 'arabic_reshaper',
    'bidi': 'python-bidi',
    'jnius': 'pyjnius',
    'android': 'android',
    'six': 'six',
}

#: p4a پکیج‌های pip را با --no-deps نصب می‌کند، پس وابستگی‌های pip باید صریح بیایند.
TRANSITIVE_PIP_DEPS = {'python-bidi': ['six']}

#: فقط برای اندروید/خودِ p4a -- در requirements.txt دسکتاپ لازم نیستند.
ANDROID_ONLY_REQUIREMENTS = {'python3', 'pyjnius', 'android'}

#: پسوند فایل‌هایی که عمداً داخل APK نمی‌روند (مستندات).
NON_BUNDLED_ASSET_EXTS = {'md'}

SRC_DIRS_NEVER_BUNDLED = ('tests', 'tools', 'native', 'docs', 'bin')


# ------------------------------------------------------------------ spec

def load_spec(path=None):
    """دقیقاً مثل خودِ buildozer می‌خواند: ConfigParser با interpolation پیش‌فرض و
    حساس به حروف کلید (optionxform=str)."""
    path = path or os.path.join(PROJECT_ROOT, 'buildozer.spec')
    parser = configparser.ConfigParser(allow_no_value=True)
    parser.optionxform = str
    with open(path, encoding='utf-8') as fh:
        parser.read_file(fh)
    return parser


def _list(spec, key, section='app'):
    raw = spec.get(section, key, fallback='') or ''
    return [item.strip() for item in raw.split(',') if item.strip()]


def _req_name(requirement):
    return re.split(r'[=<>!~ ]', requirement, maxsplit=1)[0].lower().replace('_', '-')


def parse_requirements(spec):
    """{نام نرمال‌شده: عبارت کامل} -- نام نرمال: حروف کوچک و _ -> -."""
    return {_req_name(r): r for r in _list(spec, 'requirements')}


def check_spec(spec, project_root=PROJECT_ROOT):
    problems = []
    app = spec['app']

    for key in ('title', 'package.name', 'package.domain', 'source.dir', 'version',
                'requirements', 'orientation', 'android.api', 'android.minapi', 'android.archs'):
        if not (app.get(key) or '').strip():
            problems.append(f"کلید لازم buildozer.spec خالی/ناموجود است: {key}")
    if problems:
        return problems

    # --- تصمیم‌های فایل مرجع بخش ۲.۳ ---
    if app['android.api'].strip() != '34':
        problems.append(f"android.api باید 34 باشد (فایل مرجع ۲.۳)، الان {app['android.api']}")
    if app['android.minapi'].strip() != '24':
        problems.append(f"android.minapi باید 24 باشد (فایل مرجع ۲.۳)، الان {app['android.minapi']}")
    if app['android.archs'].strip() != 'arm64-v8a':
        problems.append(f"android.archs باید فقط arm64-v8a باشد (فایل مرجع ۲.۳)، الان {app['android.archs']}")
    if app.get('android.ndk_api') and int(app['android.ndk_api']) > int(app['android.minapi']):
        problems.append("android.ndk_api نباید از android.minapi بزرگ‌تر باشد")
    if app.get('orientation', '').strip() != 'portrait':
        problems.append("orientation باید portrait باشد")
    if (app.get('android.accept_sdk_license') or '').strip().lower() != 'true':
        problems.append("android.accept_sdk_license باید True باشد (وگرنه بیلد CI منتظر ورودی می‌ماند)")
    if not (app.get('android.ndk') or '').strip():
        problems.append("android.ndk صریحاً pin نشده (پیش‌فرض buildozer بین نسخه‌ها فرق می‌کند)")

    # --- p4a باید pin باشد (قابل‌تکرار)، نه شاخه‌ی متحرک ---
    branch = (app.get('p4a.branch') or '').strip()
    if not branch:
        problems.append("p4a.branch تعیین نشده: بیلد وابسته به master متحرک می‌شود")
    elif branch in ('master', 'main', 'develop'):
        problems.append(f"p4a.branch={branch!r} شاخه‌ی متحرک است؛ به یک tag (مثل v2024.01.21) pin کنید")

    # --- requirements ---
    reqs = parse_requirements(spec)
    for name in ('python3', 'kivy', 'arabic-reshaper', 'python-bidi', 'six'):
        if name not in reqs:
            problems.append(f"requirements: «{name}» لازم است ولی نیست")
    for name in FORBIDDEN_REQUIREMENTS & set(reqs):
        problems.append(f"requirements: «{name}» طبق فایل مرجع (بخش ۲.۱) نباید برگردد")
    if 'kivy' in reqs and '==' not in reqs['kivy']:
        problems.append("kivy باید به نسخه‌ی دقیق pin شود (kivy==2.3.0)")
    if 'arabic-reshaper' in reqs and '==' not in reqs['arabic-reshaper']:
        problems.append("arabic_reshaper باید pin شود")
    if reqs.get('python-bidi', '').replace(' ', '') != 'python-bidi==0.4.2':
        problems.append("python-bidi باید دقیقاً ==0.4.2 باشد (نسخه‌های ۰.۵+ Rust‌اند و wheel اندروید ندارند؛ "
                        f"الان: {reqs.get('python-bidi')!r})")
    for parent, children in TRANSITIVE_PIP_DEPS.items():
        for child in children:
            if parent in reqs and child not in reqs:
                problems.append(f"requirements: «{parent}» به «{child}» وابسته است و p4a با --no-deps نصب می‌کند، "
                                f"پس «{child}» باید صریح بیاید")

    # --- منابع بسته‌بندی ---
    exts = {e.lower() for e in _list(spec, 'source.include_exts')}
    for ext in ('py', 'json', 'ttf', 'ogg'):
        if ext not in exts:
            problems.append(f"source.include_exts: «{ext}» لازم است (فونت/داده/صدا از APK بیرون می‌ماند)")
    excluded = set(_list(spec, 'source.exclude_dirs'))
    for d in ('tests', 'tools'):
        if d not in excluded:
            problems.append(f"source.exclude_dirs: «{d}» باید باشد (نباید داخل APK برود)")

    # --- مجوزها ---
    perms = set(_list(spec, 'android.permissions'))
    for perm in ('VIBRATE', 'POST_NOTIFICATIONS'):
        if perm not in perms:
            problems.append(f"android.permissions: «{perm}» لازم است")

    # --- استیج اعلان‌های native: یا هر دو یا هیچ‌کدام ---
    add_src = (app.get('android.add_src') or '').strip()
    hook = (app.get('p4a.hook') or '').strip()
    if bool(add_src) != bool(hook):
        problems.append("android.add_src و p4a.hook باید با هم فعال شوند (receiver بدون patch مانیفست "
                        "یا برعکس بی‌اثر/خطرناک است)")
    if add_src and not os.path.isdir(os.path.join(project_root, add_src)):
        problems.append(f"android.add_src اشاره به پوشه‌ی ناموجود: {add_src}")
    if hook and not os.path.isfile(os.path.join(project_root, hook)):
        problems.append(f"p4a.hook اشاره به فایل ناموجود: {hook}")
    return problems


def check_requirements_txt(spec, project_root=PROJECT_ROOT):
    """pin‌های requirements.txt (دسکتاپ) باید با requirements اندروید در spec یکی باشند."""
    problems = []
    path = os.path.join(project_root, 'requirements.txt')
    if not os.path.isfile(path):
        return ["requirements.txt وجود ندارد"]
    txt = {}
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.split('#', 1)[0].strip()
            if line:
                txt[_req_name(line)] = line.replace(' ', '')
    spec_reqs = parse_requirements(spec)
    for name, spec_req in spec_reqs.items():
        if name in ANDROID_ONLY_REQUIREMENTS:
            continue
        if name not in txt:
            problems.append(f"«{name}» در buildozer.spec هست ولی در requirements.txt نیست")
            continue
        spec_pin = spec_req.replace(' ', '').lower().replace('_', '-')
        txt_pin = txt[name].lower().replace('_', '-')
        if '==' in spec_pin and spec_pin != txt_pin:
            problems.append(f"pin ناهم‌خوان برای «{name}»: spec={spec_pin} requirements.txt={txt_pin}")
    for name in txt:
        if name not in spec_reqs:
            problems.append(f"«{name}» در requirements.txt هست ولی در requirements بیلد اندروید نیست")
    return problems


# ------------------------------------------------------------------ imports

def _iter_project_py(project_root, include_tests=False):
    # include_tests=True یعنی «هر کدی که CI روی پایتون ۳.۱۱ اجرا/import می‌کند»: tests/ و tools/
    # (test_phase10 مولد صدا را import می‌کند؛ قبلاً tools/ از بررسی ۳.۱۱ بیرون می‌ماند).
    skip = set(SRC_DIRS_NEVER_BUNDLED) - ({'tests', 'tools'} if include_tests else set())
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in skip and d != '__pycache__']
        for name in sorted(files):
            if name.endswith('.py'):
                yield os.path.join(root, name)


def check_third_party_imports(spec, project_root=PROJECT_ROOT):
    """هر import غیر-stdlib و غیر-پروژه‌ای در کد اجرایی باید requirement متناظر داشته باشد."""
    problems = []
    stdlib = set(sys.stdlib_module_names)
    project_tops = {d for d in os.listdir(project_root)
                    if os.path.isdir(os.path.join(project_root, d))
                    and os.path.exists(os.path.join(project_root, d, '__init__.py'))}
    project_tops |= {os.path.splitext(f)[0] for f in os.listdir(project_root) if f.endswith('.py')}
    reqs = parse_requirements(spec)
    for path in _iter_project_py(project_root):
        with open(path, encoding='utf-8') as fh:
            tree = ast.parse(fh.read())
        rel = os.path.relpath(path, project_root)
        for node in ast.walk(tree):
            modules = []
            if isinstance(node, ast.Import):
                modules = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = [node.module]
            for module in modules:
                top = module.split('.')[0]
                if top in stdlib or top in project_tops:
                    continue
                requirement = IMPORT_TO_REQUIREMENT.get(top)
                if requirement is None:
                    problems.append(f"{rel}: import «{top}» نه stdlib است نه پروژه و نه در "
                                    "IMPORT_TO_REQUIREMENT -- requirement آن مشخص نیست")
                elif _req_name(requirement) not in reqs:
                    problems.append(f"{rel}: import «{top}» نیازمند requirement «{requirement}» است "
                                    "که در buildozer.spec نیست")
    return problems


# ------------------------------------------------------------------ bundle

def simulate_bundle(spec, project_root=PROJECT_ROOT):
    """شبیه‌سازی قواعد کپی منبع buildozer (include_exts / exclude_dirs / فایل‌ها و
    پوشه‌های پنهان) -- مجموعه‌ی مسیرهای نسبی‌ای که داخل APK می‌روند."""
    include_exts = {e.lower() for e in _list(spec, 'source.include_exts')}
    exclude_dirs = [d.lower() for d in _list(spec, 'source.exclude_dirs')]
    bundled = set()
    for root, dirs, files in os.walk(project_root, followlinks=True):
        rel_root = os.path.relpath(root, project_root)
        rel_root = '' if rel_root == '.' else rel_root
        if any(part.startswith('.') for part in rel_root.split(os.sep) if part):
            continue
        filtered_root = (rel_root.lower() + '/') if rel_root else '/'
        if rel_root and any(filtered_root.startswith(x) for x in exclude_dirs):
            continue
        for name in files:
            if name.startswith('.'):
                continue
            ext = os.path.splitext(name)[1][1:].lower()
            if ext and include_exts and ext not in include_exts:
                continue
            bundled.add(os.path.join(rel_root, name).replace(os.sep, '/'))
    return bundled


def required_bundle_files(project_root=PROJECT_ROOT):
    """فایل‌هایی که *باید* در APK باشند: همه‌ی کد پایتون اجرایی + هر چیز زیر assets/
    و data/ (به‌جز مستندات). با این تعریف، هر نوع asset جدیدی که در include_exts
    فراموش شود خودکار شکست می‌خورد."""
    required = set()
    for path in _iter_project_py(project_root):
        required.add(os.path.relpath(path, project_root).replace(os.sep, '/'))
    for top in ('assets', 'data'):
        for root, dirs, files in os.walk(os.path.join(project_root, top)):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for name in files:
                ext = os.path.splitext(name)[1][1:].lower()
                if ext in NON_BUNDLED_ASSET_EXTS or name.startswith('.') or name.startswith('save.db'):
                    continue
                required.add(os.path.relpath(os.path.join(root, name), project_root).replace(os.sep, '/'))
    return required


def check_bundle(spec, project_root=PROJECT_ROOT):
    problems = []
    bundled = simulate_bundle(spec, project_root)
    for rel in sorted(required_bundle_files(project_root) - bundled):
        problems.append(f"داخل APK نمی‌رود ولی لازم است: {rel}")
    for rel in sorted(bundled):
        top = rel.split('/')[0]
        if top in SRC_DIRS_NEVER_BUNDLED:
            problems.append(f"نباید داخل APK برود ولی می‌رود: {rel}")
    if 'main.py' not in bundled:
        problems.append("main.py داخل APK نمی‌رود")
    return problems


def verify_bundle_dir(bundle_dir, project_root=PROJECT_ROOT):
    """مقایسه‌ی خروجی *واقعی* buildozer (.buildozer/android/app) با فایل‌های لازم."""
    if not os.path.isdir(bundle_dir):
        return [f"پوشه‌ی بیلد پیدا نشد: {bundle_dir} (فرض مسیر ممکنه غلط باشه؛ لاگ بیلد رو ببینید)"]
    actual = set()
    for root, _dirs, files in os.walk(bundle_dir):
        for name in files:
            actual.add(os.path.relpath(os.path.join(root, name), bundle_dir).replace(os.sep, '/'))
    problems = [f"در خروجی واقعی buildozer نیست: {rel}"
                for rel in sorted(required_bundle_files(project_root) - actual)]
    problems += [f"نباید در خروجی واقعی باشد: {rel}" for rel in sorted(actual)
                 if rel.split('/')[0] in SRC_DIRS_NEVER_BUNDLED]
    return problems


# ------------------------------------------------------------------ python 3.11

def check_python311_compat(project_root=PROJECT_ROOT):
    """p4a v2024.01.21 پایتون ۳.۱۱ دارد. روی ۳.۱۲ تست‌ها پاس می‌شوند حتی اگر کد
    syntax فقط-۳.۱۲ (مثل f-string با نقل‌قول تودرتوی هم‌نوع، PEP 701) داشته باشد."""
    problems = []
    for path in _iter_project_py(project_root, include_tests=True):
        rel = os.path.relpath(path, project_root)
        with open(path, encoding='utf-8') as fh:
            src = fh.read()
        try:
            ast.parse(src, feature_version=(3, 11))
        except SyntaxError as exc:
            problems.append(f"{rel}: syntax ناسازگار با ۳.۱۱: {exc}")
            continue
        if not hasattr(tokenize, 'FSTRING_START'):
            continue  # روی خودِ ۳.۱۱، ast.parse بالا همه‌چیز را گرفته
        quotes, depth = [], []
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            text = tok.string
            if tok.type == tokenize.FSTRING_START:
                quotes.append(text[-3:] if text[-3:] in ('"""', "'''") else text[-1])
                depth.append(0)
            elif tok.type == tokenize.FSTRING_END:
                quotes.pop()
                depth.pop()
            elif quotes and tok.type == tokenize.OP and text == '{':
                depth[-1] += 1
            elif quotes and tok.type == tokenize.OP and text == '}':
                depth[-1] -= 1
            elif (quotes and depth[-1] > 0 and tok.type == tokenize.STRING
                  and len(quotes[-1]) == 1 and text.lstrip('rbuRBU')[:1] == quotes[-1]):
                problems.append(f"{rel}:{tok.start[0]}: f-string با نقل‌قول تودرتوی هم‌نوع (فقط ۳.۱۲+)")
    return problems


# ------------------------------------------------------------------ dp()

_SIZE_KWARGS = {'height', 'width', 'spacing', 'padding', 'size', 'row_default_height',
                'col_default_width', 'bar_width', 'minimum_height'}
_GRAPHICS_CALLS = {'Line', 'Ellipse', 'Rectangle', 'Color', 'InstructionGroup', 'Mesh', 'Triangle', 'Quad', 'Point'}
_POSITION_ATTRS = {'top', 'right', 'x', 'y', 'center_x', 'center_y', 'width', 'height'}


def _nonzero_number(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value != 0
    if isinstance(node, (ast.Tuple, ast.List)):
        return any(_nonzero_number(e) for e in node.elts)
    return False


def check_raw_pixel_sizes(project_root=PROJECT_ROOT):
    """ابعاد ویجت باید با dp() بیایند. روی دسکتاپ density=1 است (پیکسل=dp، پس همه‌چیز
    درست دیده می‌شد)؛ روی گوشی ۴۴۰dpi چگالی ≈۲.۷ است: نوار ۶۴ پیکسلی ≈۳.۷ میلی‌متر
    می‌شود با متنی که `sp` (مقیاس‌شونده) است و از خودش بزرگ‌تر درمی‌آید."""
    problems = []
    ui_root = os.path.join(project_root, 'ui')
    for path in _iter_project_py(ui_root):
        rel = os.path.relpath(path, project_root)
        with open(path, encoding='utf-8') as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fname = ast.unparse(node.func).split('.')[-1]
                if fname in _GRAPHICS_CALLS:
                    continue
                for kw in node.keywords:
                    if kw.arg in _SIZE_KWARGS and _nonzero_number(kw.value):
                        problems.append(f"{rel}:{node.lineno}: {fname}({kw.arg}={ast.unparse(kw.value)}) پیکسل خام")
                if (fname == 'setdefault' and len(node.args) == 2 and isinstance(node.args[0], ast.Constant)
                        and node.args[0].value in _SIZE_KWARGS and _nonzero_number(node.args[1])):
                    problems.append(f"{rel}:{node.lineno}: setdefault({node.args[0].value!r}, "
                                    f"{ast.unparse(node.args[1])}) پیکسل خام")
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if (isinstance(target, ast.Attribute) and target.attr in _SIZE_KWARGS
                            and _nonzero_number(node.value)):
                        problems.append(f"{rel}:{node.lineno}: {ast.unparse(target)} = "
                                        f"{ast.unparse(node.value)} پیکسل خام")
            elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
                sides = (node.left, node.right)
                has_pos_attr = any(isinstance(s, ast.Attribute) and s.attr in _POSITION_ATTRS for s in sides)
                has_raw = any(isinstance(s, ast.Constant) and isinstance(s.value, (int, float))
                              and not isinstance(s.value, bool) and abs(s.value) >= 4 for s in sides)
                if has_pos_attr and has_raw:
                    problems.append(f"{rel}:{node.lineno}: افست موقعیت با عدد خام: {ast.unparse(node)}")
    return problems


# ------------------------------------------------------------------ fonts / workflow / native

def check_fonts(project_root=PROJECT_ROOT):
    from utils.fonts import resolve_font_family
    family = resolve_font_family(os.path.join(project_root, 'assets', 'fonts'))
    if family is None:
        return ["هیچ فونت فارسی‌دار در assets/fonts نیست؛ همه‌ی متن فارسی مربع نشان داده می‌شود"]
    problems = []
    strings = font_coverage.collect_ui_strings(project_root)
    for path in sorted(set(family)):
        missing = font_coverage.missing_codepoints(path, project_root, strings=strings)
        if missing:
            problems.append(f"{os.path.basename(path)}: {len(missing)} گلیف لازم ندارد، مثل "
                            + ', '.join(font_coverage.describe(cp) for cp in missing[:4]))
    license_files = [f for f in os.listdir(os.path.join(project_root, 'assets', 'fonts'))
                     if f.lower().startswith('license')]
    if not license_files:
        problems.append("مجوز فونت (LICENSE*) کنار فونت‌ها نیست؛ بازتوزیع فونت مستلزم همراه‌بودن مجوز است")
    return problems


def check_workflow(project_root=PROJECT_ROOT):
    try:
        import yaml
    except ImportError:
        return None  # SKIP -- PyYAML نصب نیست
    path = os.path.join(project_root, '.github', 'workflows', 'build-apk.yml')
    if not os.path.isfile(path):
        return [".github/workflows/build-apk.yml وجود ندارد"]
    with open(path, encoding='utf-8') as fh:
        doc = yaml.safe_load(fh)
    problems = []
    triggers = doc.get('on', doc.get(True)) or {}
    for needed in ('push', 'workflow_dispatch'):
        if needed not in triggers:
            problems.append(f"workflow: trigger «{needed}» لازم است")
    jobs = doc.get('jobs', {})
    for job in ('preflight', 'build'):
        if job not in jobs:
            problems.append(f"workflow: job «{job}» لازم است")
    if problems:
        return problems
    if 'preflight' not in (jobs['build'].get('needs') or []) and jobs['build'].get('needs') != 'preflight':
        problems.append("workflow: job «build» باید به preflight وابسته باشد (fail-fast قبل از بیلد سنگین)")
    text = open(path, encoding='utf-8').read()
    if "python-version: '3.11'" not in text:
        problems.append("workflow: پایتون ۳.۱۱ نیست (نسخه‌ی پایتون داخل APK)")
    if 'upload-artifact' not in text:
        problems.append("workflow: آپلود artifact ندارد")
    if re.search(r'\|\s*tee', text) and 'shell: bash' not in text:
        problems.append("workflow: pipe به tee بدون shell: bash (pipefail) شکست buildozer را پنهان می‌کند")
    if re.search(r'\byes\s*\|', text):
        problems.append("workflow: «yes | buildozer» با pipefail به SIGPIPE می‌خورد؛ accept_sdk_license کافی است")
    return problems


def check_native_staging(spec, project_root=PROJECT_ROOT):
    """کد native (جاوا + hook) اگر در native/ هست باید سالم باشد؛ فعال‌بودنش در spec
    اختیاری است (استیج‌شده)."""
    native = os.path.join(project_root, 'native')
    if not os.path.isdir(native):
        return []
    problems = []
    java = os.path.join(native, 'android', 'java', 'org', 'laserricochet', 'notify', 'ReminderReceiver.java')
    hook = os.path.join(native, 'p4a_hook.py')
    for path in (java, hook, os.path.join(native, 'README.md')):
        if not os.path.isfile(path):
            problems.append(f"native/: فایل لازم نیست: {os.path.relpath(path, project_root)}")
    if os.path.isfile(hook):
        with open(hook, encoding='utf-8') as fh:
            names = {n.name for n in ast.parse(fh.read()).body if isinstance(n, ast.FunctionDef)}
        for fn in ('after_apk_build', 'patch_manifest_text'):
            if fn not in names:
                problems.append(f"native/p4a_hook.py: تابع «{fn}» تعریف نشده")
    return problems


def check_campaign_levels(project_root=PROJECT_ROOT, total_levels=None):
    """فاز۹: ۱۰۰ فایل مرحله‌ی کمپین باید پیوسته و سالم باشند. بررسی *ساختاری* سبک است؛ اثبات حل‌پذیری
    (سنگین) در tests/test_phase9.py روی همین فایل‌هاست. فایل حذف‌شده/خراب‌شده بی‌صدا مرحله را از
    بازی می‌انداخت چون LevelManager همه‌ی level_*.json موجود را بارگذاری می‌کند."""
    if total_levels is None:
        from game_logic.difficulty_manager import TOTAL_LEVELS as total_levels
    levels_dir = os.path.join(project_root, 'assets', 'levels')
    if not os.path.isdir(levels_dir):
        return ["assets/levels وجود ندارد"]
    expected = {f'level_{i:03d}.json': i for i in range(1, total_levels + 1)}
    present = {f for f in os.listdir(levels_dir) if f.startswith('level_') and f.endswith('.json')}
    problems = [f"فایل مرحله ناموجود: {name}" for name in sorted(set(expected) - present)]
    problems += [f"فایل مرحله‌ی اضافه یا با نام نامعتبر: {name}" for name in sorted(present - set(expected))]
    for name in sorted(present & set(expected)):
        try:
            with open(os.path.join(levels_dir, name), encoding='utf-8') as handle:
                data = json.load(handle)
        except (OSError, ValueError) as exc:
            problems.append(f"{name}: JSON نامعتبر ({exc})")
            continue
        if data.get('level_id') != expected[name]:
            problems.append(f"{name}: level_id داخل فایل ({data.get('level_id')}) با نام فایل نمی‌خواند")
        if not data.get('targets'):
            problems.append(f"{name}: هیچ هدفی ندارد")
        if not isinstance(data.get('time_limit'), (int, float)) or data['time_limit'] <= 0:
            problems.append(f"{name}: time_limit نامعتبر")
        if not isinstance(data.get('laser_start'), dict):
            problems.append(f"{name}: laser_start ندارد")
    return problems


# ------------------------------------------------------------------ runner

CHECKS = (
    ('buildozer.spec', lambda spec: check_spec(spec)),
    ('requirements.txt همخوان با spec', lambda spec: check_requirements_txt(spec)),
    ('importهای شخص‌ثالث ↔ requirements', lambda spec: check_third_party_imports(spec)),
    ('محتوای APK (شبیه‌سازی)', lambda spec: check_bundle(spec)),
    ('سازگاری پایتون ۳.۱۱', lambda spec: check_python311_compat()),
    ('ابعاد UI با dp()', lambda spec: check_raw_pixel_sizes()),
    ('فونت فارسی', lambda spec: check_fonts()),
    ('workflow', lambda spec: check_workflow()),
    ('کد native (استیج)', lambda spec: check_native_staging(spec)),
    ('مراحل کمپین (۱۰۰ فایل)', lambda spec: check_campaign_levels()),
)


def run_all(spec=None):
    spec = spec or load_spec()
    return [(name, fn(spec)) for name, fn in CHECKS]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['--bundle']:
        target = argv[1] if len(argv) > 1 else os.path.join(PROJECT_ROOT, '.buildozer', 'android', 'app')
        problems = verify_bundle_dir(target)
        print(f"تطبیق با خروجی واقعی buildozer: {target}")
        for p in problems:
            print(f"  ✗ {p}")
        print("  ✓ همه‌ی فایل‌های لازم هست" if not problems else f"  {len(problems)} مشکل")
        return 1 if problems else 0

    failed = 0
    for name, problems in run_all():
        if problems is None:
            print(f"  --   {name}  (SKIP: PyYAML نصب نیست)")
        elif problems:
            failed += 1
            print(f"  FAIL {name}")
            for p in problems:
                print(f"         - {p}")
        else:
            print(f"  OK   {name}")
    print(f"\n=== preflight: {'همه‌چیز سالم' if not failed else str(failed) + ' بررسی ناموفق'} ===")
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
