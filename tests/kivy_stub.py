"""
tests/kivy_stub.py  (فاز ۸ -- فقط تست، داخل APK نمی‌رود)

یک «Kivy ساختگی» برای اجرای سربی (headless) کد UI در جایی که Kivy نصب نیست (sandbox
توسعه، یا CI قبل از خرج‌کردن ۴۰ دقیقه بیلد).

⚠️ دامنه‌ی صادقانه: این stub *کد خودِ ما* را اجرا می‌کند -- نه Kivy واقعی را. می‌گیرد:
خطای import، NameError/AttributeError در کد صفحه‌ها، فراخوانی اشتباه APIهای داخلی
پروژه (مثل `challenge.PARTICIPATION_REWARD`ای که در فاز۷ فقط با بازبینی دستی پیدا
شد)، kwarg ناموجود (TypeError، دقیقاً مثل Kivy واقعی)، و استثنا در handlerها (روی
گوشی هر استثنا در یک callback کل برنامه را می‌بندد). نمی‌گیرد: ظاهر، layout واقعی،
عملکرد، رفتار OpenGL/SDL.

عمداً *سخت‌گیر* است (نه permissive): ویژگی یا kwarg ناشناخته خطا می‌دهد، نه این‌که
بی‌صدا پذیرفته شود -- تنها همین، غلط تایپی واقعی را می‌گیرد. اگر stub چیزی را رد
کرد که Kivy واقعی دارد، همین‌جا به فهرست اضافه می‌شود (ثابت‌های `_PROPS` هر کلاس).

سطح API دقیقاً همان است که پروژه استفاده می‌کند (با grep استخراج شده): ۲۰ import،
add_widget/bind/setter/schedule_*/collide_point/canvas.*/get_screen/...
"""
import os
import sys
import tempfile
import types

DENSITY = 1.0


def set_density(value):
    global DENSITY
    DENSITY = float(value)


def dp(value):
    return value * DENSITY


# ------------------------------------------------------------------ canvas

_canvas_stack = []


class _Instruction:
    """Color/Rectangle/Line/...؛ هر ویژگی را می‌پذیرد (مثل خانواده‌ی graphics واقعی)."""

    def __init__(self, *args, **kwargs):
        self._args = args
        for key, value in kwargs.items():
            setattr(self, key, value)
        if _canvas_stack:
            _canvas_stack[-1].children.append(self)


class Color(_Instruction):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.rgba = tuple(args) if args else (1, 1, 1, 1)


class Rectangle(_Instruction):
    pass


class Line(_Instruction):
    pass


class Ellipse(_Instruction):
    pass


class PushMatrix(_Instruction):
    pass


class PopMatrix(_Instruction):
    pass


class Translate(_Instruction):
    """مثل Translate واقعی: x, y و مختصر `xy`."""

    def __init__(self, x=0, y=0, z=0, **kwargs):
        super().__init__(**kwargs)
        self.x, self.y, self.z = x, y, z

    @property
    def xy(self):
        return (self.x, self.y)

    @xy.setter
    def xy(self, value):
        self.x, self.y = value


class InstructionGroup(_Instruction):
    def __init__(self, **kwargs):
        self.children = []
        super().__init__(**kwargs)

    def add(self, instruction):
        self.children.append(instruction)

    def remove(self, instruction):
        if instruction in self.children:
            self.children.remove(instruction)

    def clear(self):
        self.children.clear()


class _Canvas(InstructionGroup):
    def __init__(self, nested=True):
        super().__init__()
        if nested:
            self.before = _Canvas(nested=False)
            self.after = _Canvas(nested=False)

    def __enter__(self):
        _canvas_stack.append(self)
        return self

    def __exit__(self, *exc):
        _canvas_stack.pop()
        return False


# ------------------------------------------------------------------ widgets

class Widget:
    _PROPS = {'x', 'y', 'width', 'height', 'pos', 'size', 'size_hint', 'size_hint_x', 'size_hint_y',
              'size_hint_min', 'size_hint_max', 'pos_hint', 'center_x', 'center_y', 'center',
              'right', 'top', 'opacity', 'disabled', 'id', 'cls'}

    @classmethod
    def _valid_props(cls):
        props = set()
        for klass in cls.__mro__:
            props |= getattr(klass, '_PROPS', set()) if '_PROPS' in klass.__dict__ else set()
        return props

    def __init__(self, **kwargs):
        object.__setattr__(self, '_binds', {})
        self.children = []
        self.parent = None
        self.canvas = _Canvas()
        self.x, self.y = 0, 0
        self.width, self.height = 100, 100
        self.size_hint_x, self.size_hint_y = 1, 1
        self.pos_hint = {}
        self.opacity = 1.0
        self.disabled = False
        self.ctor_kwargs = dict(kwargs)
        self._init_defaults()
        valid = self._valid_props()
        for key, value in kwargs.items():
            if key.startswith('on_'):
                self.bind(**{key: value})
            elif key in valid:
                setattr(self, key, value)
            else:
                raise TypeError(f"Properties ['{key}'] passed to __init__ may not be existing property "
                                f"names on {type(self).__name__} (kivy_stub: add to _PROPS only if the REAL "
                                "Kivy class has this property)")

    def _init_defaults(self):
        pass

    # --- geometry (properties so pos/size/center stay consistent) ---
    @property
    def pos(self):
        return (self.x, self.y)

    @pos.setter
    def pos(self, value):
        self.x, self.y = value[0], value[1]

    @property
    def size(self):
        return (self.width, self.height)

    @size.setter
    def size(self, value):
        self.width, self.height = value[0], value[1]

    @property
    def right(self):
        return self.x + self.width

    @right.setter
    def right(self, value):
        self.x = value - self.width

    @property
    def top(self):
        return self.y + self.height

    @top.setter
    def top(self, value):
        self.y = value - self.height

    @property
    def center_x(self):
        return self.x + self.width / 2.0

    @center_x.setter
    def center_x(self, value):
        self.x = value - self.width / 2.0

    @property
    def center_y(self):
        return self.y + self.height / 2.0

    @center_y.setter
    def center_y(self, value):
        self.y = value - self.height / 2.0

    @property
    def center(self):
        return (self.center_x, self.center_y)

    @center.setter
    def center(self, value):
        self.center_x, self.center_y = value

    @property
    def size_hint(self):
        return (self.size_hint_x, self.size_hint_y)

    @size_hint.setter
    def size_hint(self, value):
        self.size_hint_x, self.size_hint_y = value

    # --- property observation: bind(pos=cb) -> cb(instance, value) on every set ---
    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        callbacks = self.__dict__.get('_binds', {}).get(name)
        if callbacks:
            current = getattr(self, name)
            for callback in list(callbacks):
                callback(self, current)

    def bind(self, **kwargs):
        for name, callback in kwargs.items():
            self._binds.setdefault(name, []).append(callback)

    def unbind(self, **kwargs):
        for name, callback in kwargs.items():
            if callback in self._binds.get(name, []):
                self._binds[name].remove(callback)

    def setter(self, name):
        return lambda instance, value: setattr(self, name, value)

    def dispatch(self, event, *args):
        handler = getattr(self, event, None)
        result = handler(*args) if callable(handler) else None
        for callback in list(self._binds.get(event, [])):
            if callback(self, *args):
                return True
        return bool(result)

    # --- tree ---
    def add_widget(self, widget, index=0, canvas=None):
        widget.parent = self
        self.children.insert(index, widget)
        # مثل Kivy واقعی: canvas فرزند داخل canvas والد (یا before/after آن) قرار می‌گیرد.
        # به همین دلیل `parent.canvas.clear()` فرزندان را هم از درخت رسم حذف می‌کند -- رفتاری
        # که استاب قبلاً مدل نمی‌کرد و باگ ناپدیدشدن HUD را پنهان نگه می‌داشت.
        target = self.canvas.before if canvas == 'before' else self.canvas.after if canvas == 'after' else self.canvas
        target.add(widget.canvas)

    def remove_widget(self, widget):
        if widget in self.children:
            self.children.remove(widget)
            widget.parent = None
            for group in (self.canvas, self.canvas.before, self.canvas.after):
                group.remove(widget.canvas)

    def clear_widgets(self, children=None):
        for child in list(children if children is not None else self.children):
            self.remove_widget(child)

    def walk(self):
        yield self
        for child in list(self.children):
            yield from child.walk()

    def collide_point(self, x, y):
        return self.x <= x <= self.right and self.y <= y <= self.top

    def on_touch_down(self, touch):
        for child in list(self.children):
            if child.dispatch('on_touch_down', touch):
                return True
        return False

    def on_touch_move(self, touch):
        return False

    def on_touch_up(self, touch):
        return False


class Label(Widget):
    _PROPS = {'text', 'font_size', 'font_name', 'color', 'bold', 'italic', 'halign', 'valign',
              'text_size', 'markup', 'shorten', 'max_lines', 'padding', 'padding_x', 'padding_y',
              'line_height', 'texture_size', 'texture', 'outline_width', 'outline_color',
              'shorten_from', 'split_str', 'strip', 'font_family', 'mipmap'}

    def _init_defaults(self):
        self.text = ''
        self.font_size = '15sp'
        self.font_name = 'Roboto'
        self.color = [1, 1, 1, 1]
        self.halign = 'auto'
        self.valign = 'bottom'
        self.text_size = (None, None)
        self.texture_size = [0, 0]
        self.padding = (0, 0)
        self.bold = False


class Button(Label):
    _PROPS = {'background_color', 'background_normal', 'background_down', 'background_disabled_normal',
              'background_disabled_down', 'border', 'state', 'always_release', 'min_state_time'}

    def _init_defaults(self):
        super()._init_defaults()
        self.background_color = [1, 1, 1, 1]
        self.state = 'normal'

    def on_press(self):
        pass

    def on_release(self):
        pass


class BoxLayout(Widget):
    _PROPS = {'orientation', 'spacing', 'padding', 'minimum_width', 'minimum_height', 'minimum_size'}

    def _init_defaults(self):
        self.orientation = 'horizontal'
        self.spacing = 0
        self.padding = [0, 0, 0, 0]


class GridLayout(Widget):
    _PROPS = {'cols', 'rows', 'spacing', 'padding', 'row_default_height', 'row_force_default',
              'col_default_width', 'col_force_default', 'cols_minimum', 'rows_minimum',
              'minimum_width', 'minimum_height', 'minimum_size'}

    def _init_defaults(self):
        self.spacing = 0
        self.padding = [0, 0, 0, 0]


class ScrollView(Widget):
    _PROPS = {'scroll_x', 'scroll_y', 'do_scroll_x', 'do_scroll_y', 'bar_width', 'bar_color',
              'bar_inactive_color', 'bar_margin', 'scroll_distance', 'scroll_timeout', 'scroll_type',
              'effect_cls', 'always_overscroll', 'smooth_scroll_end'}

    def _init_defaults(self):
        self.scroll_x, self.scroll_y = 0.0, 1.0

    def add_widget(self, widget, index=0, canvas=None):
        if self.children:
            raise Exception('ScrollView accept only one widget')
        super().add_widget(widget, index, canvas)


class ScreenManagerException(Exception):
    pass


class Screen(Widget):
    _PROPS = {'name', 'manager', 'transition_progress', 'transition_state'}

    def _init_defaults(self):
        self.name = ''
        self.manager = None

    def on_pre_enter(self, *args):
        pass

    def on_enter(self, *args):
        pass

    def on_pre_leave(self, *args):
        pass

    def on_leave(self, *args):
        pass


class NoTransition:
    pass


class ScreenManager(Widget):
    _PROPS = {'current', 'transition', 'screens', 'screen_names', 'current_screen', 'previous'}

    def _init_defaults(self):
        self.screens = []
        self.transition = NoTransition()
        self._current = None

    @property
    def screen_names(self):
        return [s.name for s in self.screens]

    @property
    def current_screen(self):
        return self.get_screen(self._current) if self._current else None

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, name):
        if name == self._current:
            return
        screen = self.get_screen(name)
        old = self.get_screen(self._current) if self._current else None
        if old is not None:
            old.dispatch('on_pre_leave')
        screen.dispatch('on_pre_enter')
        self._current = name
        screen.dispatch('on_enter')
        if old is not None:
            old.dispatch('on_leave')

    def add_widget(self, widget, index=0, canvas=None):
        if not isinstance(widget, Screen):
            raise ScreenManagerException('ScreenManager accepts only Screen widget.')
        if widget.name in self.screen_names:
            raise ScreenManagerException(f'Name {widget.name!r} already used')
        widget.manager = self
        widget.parent = self
        self.screens.append(widget)
        if len(self.screens) == 1:
            self._current = widget.name   # مثل Kivy واقعی: اولین صفحه خودکار فعال می‌شود

    def has_screen(self, name):
        return name in self.screen_names

    def get_screen(self, name):
        for screen in self.screens:
            if screen.name == name:
                return screen
        raise ScreenManagerException(f'No Screen with name "{name}".')


# ------------------------------------------------------------------ Clock / Window / App ...

class _ClockEvent:
    def __init__(self, clock, callback, repeat):
        self.clock, self.callback, self.repeat = clock, callback, repeat

    def cancel(self):
        if self in self.clock._events:
            self.clock._events.remove(self)


class _Clock:
    def __init__(self):
        self._events = []

    def schedule_once(self, callback, timeout=0):
        event = _ClockEvent(self, callback, repeat=False)
        self._events.append(event)
        return event

    def schedule_interval(self, callback, interval):
        event = _ClockEvent(self, callback, repeat=True)
        self._events.append(event)
        return event

    def unschedule(self, target):
        for event in list(self._events):
            if event is target or event.callback == target:
                self._events.remove(event)

    def tick(self, dt=1 / 60.0, frames=1):
        for _ in range(frames):
            for event in list(self._events):
                if event not in self._events:
                    continue
                if not event.repeat:
                    self._events.remove(event)
                if event.callback(dt) is False and event.repeat and event in self._events:
                    self._events.remove(event)

    def reset(self):
        self._events.clear()


class _Window:
    def __init__(self):
        self.reset()

    def reset(self):
        self.size = (405, 720)
        self._binds = {}

    @property
    def width(self):
        return self.size[0]

    @property
    def height(self):
        return self.size[1]

    def bind(self, **kwargs):
        for name, callback in kwargs.items():
            self._binds.setdefault(name, []).append(callback)

    def fire_keyboard(self, key):
        """True اگر یکی از handlerها رویداد را مصرف کرد (یعنی Kivy برنامه را نمی‌بندد)."""
        for callback in list(self._binds.get('on_keyboard', [])):
            if callback(self, key, 0, None, []):
                return True
        return False


class _Logger:
    def __init__(self):
        self.records = []

    def _log(self, level, message, *args):
        self.records.append((level, (message % args) if args else message))

    def debug(self, message, *args):
        self._log('debug', message, *args)

    def info(self, message, *args):
        self._log('info', message, *args)

    def warning(self, message, *args):
        self._log('warning', message, *args)

    def error(self, message, *args):
        self._log('error', message, *args)

    def exception(self, message, *args):
        self._log('exception', message, *args)


class LabelBase:
    _fonts = {}

    @classmethod
    def register(cls, name, fn_regular, fn_italic=None, fn_bold=None, fn_bolditalic=None):
        for path in (fn_regular, fn_italic, fn_bold, fn_bolditalic):
            if path is not None and not os.path.isfile(path):
                raise IOError(f'File {path}s not found')   # همان پیام Kivy واقعی
        cls._fonts[name] = (fn_regular, fn_italic or fn_regular, fn_bold or fn_regular,
                            fn_bolditalic or fn_bold or fn_regular)


class SoundLoader:
    @staticmethod
    def load(filename):
        return None   # مثل Kivy واقعی وقتی فایل/loader نیست -- پروژه فایل صوتی ندارد (assets/audio/README.md)


class Animation:
    """جهش مستقیم به مقدار نهایی (بدون زمان)، سپس on_complete -- برای مشاهده‌ی وضعیت نهایی."""

    def __init__(self, **kwargs):
        self._props = {k: v for k, v in kwargs.items() if k not in ('d', 'duration', 't', 'transition')}
        self._on_complete = []

    def __add__(self, other):
        return _AnimationSequence([self, other])

    def __and__(self, other):
        return _AnimationSequence([self, other])

    def bind(self, **kwargs):
        if 'on_complete' in kwargs:
            self._on_complete.append(kwargs['on_complete'])

    def start(self, widget):
        for name, value in self._props.items():
            setattr(widget, name, value)
        for callback in self._on_complete:
            callback(self, widget)

    def stop(self, widget):
        pass

    def cancel(self, widget):
        pass

    @staticmethod
    def cancel_all(widget, *props):
        pass


class _AnimationSequence(Animation):
    def __init__(self, parts):
        super().__init__()
        self._parts = parts

    def start(self, widget):
        for part in self._parts:
            part.start(widget)
        for callback in self._on_complete:
            callback(self, widget)


class App:
    _running = None
    USER_DATA_BASE = None

    def __init__(self, **kwargs):
        self.root = None
        self.title = None
        self.stopped = False
        self._user_data_dir = None

    @staticmethod
    def get_running_app():
        return App._running

    @property
    def user_data_dir(self):
        if self._user_data_dir is None:
            base = App.USER_DATA_BASE or tempfile.mkdtemp(prefix='lr_userdata_')
            os.makedirs(base, exist_ok=True)
            self._user_data_dir = base
        return self._user_data_dir

    def build(self):
        return None

    def on_start(self):
        pass

    def on_stop(self):
        pass

    def on_pause(self):
        return True

    def on_resume(self):
        pass

    def stop(self):
        self.stopped = True

    def start_for_test(self):
        """معادل App.run() بدون حلقه‌ی رویداد: build() سپس on_start()."""
        App._running = self
        self.root = self.build()
        self.on_start()
        return self.root


# ------------------------------------------------------------------ installation

Clock = _Clock()
Window = _Window()
Logger = _Logger()


def _module(name, **attrs):
    mod = types.ModuleType(name)
    mod.__dict__.update(attrs)
    sys.modules[name] = mod
    return mod


def install():
    """kivy.* را با نسخه‌ی ساختگی در sys.modules می‌گذارد (قبل از import هر ماژول پروژه)."""
    if 'kivy' in sys.modules and getattr(sys.modules['kivy'], 'IS_STUB', False):
        return
    pkg = _module('kivy', IS_STUB=True)
    pkg.__path__ = []
    for sub in ('kivy.uix', 'kivy.core'):
        m = _module(sub)
        m.__path__ = []
    _module('kivy.app', App=App)
    _module('kivy.metrics', dp=dp)
    _module('kivy.clock', Clock=Clock)
    _module('kivy.logger', Logger=Logger)
    _module('kivy.utils', platform='linux')
    _module('kivy.animation', Animation=Animation)
    _module('kivy.graphics', Color=Color, Rectangle=Rectangle, Line=Line, Ellipse=Ellipse, Canvas=lambda: _Canvas(nested=False), PushMatrix=PushMatrix, PopMatrix=PopMatrix, Translate=Translate,
            InstructionGroup=InstructionGroup)
    _module('kivy.core.window', Window=Window)
    _module('kivy.core.text', LabelBase=LabelBase, DEFAULT_FONT='Roboto')
    _module('kivy.core.audio', SoundLoader=SoundLoader)
    _module('kivy.uix.widget', Widget=Widget)
    _module('kivy.uix.label', Label=Label)
    _module('kivy.uix.button', Button=Button)
    _module('kivy.uix.boxlayout', BoxLayout=BoxLayout)
    _module('kivy.uix.gridlayout', GridLayout=GridLayout)
    _module('kivy.uix.scrollview', ScrollView=ScrollView)
    _module('kivy.uix.screenmanager', Screen=Screen, ScreenManager=ScreenManager, NoTransition=NoTransition,
            ScreenManagerException=ScreenManagerException)


def reset(density=1.0, user_data_dir=None):
    """وضعیت سراسری stub را برای یک سناریوی تازه پاک می‌کند."""
    set_density(density)
    Clock.reset()
    Window.reset()
    Logger.records.clear()
    LabelBase._fonts.clear()
    App._running = None
    App.USER_DATA_BASE = user_data_dir
    _canvas_stack.clear()
