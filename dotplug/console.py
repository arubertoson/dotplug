"""
This module contains curses implementation
"""
import asyncio
import curses
import functools
import contextlib

from enum import Enum, IntEnum


class ColorPair(IntEnum):
    WHITE = 1
    BLACK = 2
    GREEN = 3
    RED = 4
    BLUE = 5
    ORANGE = 6


class _Colors:
    # We use 0-255 range to calculate rgb values
    _COLOR_MAPPING = {
        ColorPair.WHITE: (232, 232, 232),
        ColorPair.BLACK: (33, 33, 33),
        ColorPair.RED: (244, 67, 54),
        ColorPair.GREEN: (129, 199, 132),
        ColorPair.BLUE: (66, 165, 245),
        ColorPair.ORANGE: (255, 167, 38),
    }

    def __iter__(cls):
        return iter(cls._COLOR_MAPPING.items())

    def __getattr__(cls, attr):
        try:
            return cls._COLOR_MAPPING[attr]
        except KeyError:
            return super().__getattribute__(attr)


Colors = _Colors()


def init_colors():
    for num, rgb in Colors:
        curses.init_color(num, *(int(1000 * (i / 255)) for i in rgb))
        curses.init_pair(num, num, -1)


@contextlib.contextmanager
def ncurses():
    global stdscr
    try:
        stdscr = curses.initscr()
        curses.noecho()

        # Make colors available
        curses.start_color()
        curses.use_default_colors()
        init_colors()

        # Don't draw cursor
        curses.curs_set(False)

        yield stdscr
    finally:
        curses.echo()
        curses.endwin()


def refresh_bar(method):
    """
    Refresh Decorator

    Forces redraw on screen with objects having a bar
    """

    @functools.wraps(method)
    def wrapper(inst, *args, **kw):
        method(inst, *args, **kw)
        inst._bar.refresh()

    return wrapper


class BaseBar:
    """
    Base bar class
    """

    def __init__(self, x, y, width):
        self._x = x
        self._y = y
        self._width = width
        self._bar = curses.newwin(1, width, y, x)

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def width(self):
        return self._width

    @property
    def bar(self):
        return self._bar

    @refresh_bar
    def write(self, msg, x=0, color=None):
        self._bar.addstr(0, x, msg, curses.color_pair(color
                                                      or ColorPair.WHITE))

    def clear(self):
        self._bar.erase()


class TaskStatus(IntEnum):
    IDLE = 1
    RUNNING = 2
    DONE = 3
    SUCCESSFULE = 4
    FAILED = -1


def set_status(status):
    def _set_status(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kw):

            self._status = status
            return method(self, *args, **kw)

        return wrapper

    return _set_status


class StatusBar(BaseBar):
    """
    Status bar class
    """

    def __init__(self, x, y, width=3):
        super().__init__(x, y, width)
        self._status = None

    def status(self):
        return self._status

    @set_status(TaskStatus.IDLE)
    def waiting(self):
        self.write('*', color=ColorPair.WHITE)

    @set_status(TaskStatus.RUNNING)
    def executing(self):
        self.write('>', color=ColorPair.BLUE)

    @set_status(TaskStatus.DONE)
    def done(self):
        self.write('-', color=ColorPair.ORANGE)


class LoaderBar(BaseBar):
    """
    Loader bar class
    """

    def __init__(self, x, y, width=6, sym='>'):
        super().__init__(x, y, width)

        self._loader = ['{}  ', ' {} ', '  {}']

    def idle(self):
        self.write(' - ')

    def update(self):
        res = self._loader.pop(0)
        self._write(res)
        self._loader.append(res)

    async def wait_for(self, coro):
        future = asyncio.ensure_future(coro)

        while True:
            if future.done():
                break

            self.update()

            await asyncio.sleep(0.2)

        self.idle()
        return future.result()


class TaskBar:
    """
    Task Bar Format:

        {Status}{Name}{Loader}{Message}

    """

    def __init__(self, name, x, y, initial_message=''):

        # Setup Task Modules
        _status = StatusBar(x, y)
        _namebar = BaseBar(_status.width + _status.x, y, 12)

        _loader = LoaderBar(_namebar.width + _namebar.x, y)
        _loader.idle()

        _message = BaseBar(_loader.x + _loader.width, y, 60)
        _message.write(initial_message)

        # Assign
        self._name = name
        self._namebar = _namebar
        self._status = _status
        self._loader = _loader
        self._message = _message

        # Initial Status
        self.waiting()

    def waiting(self):
        self._status.waiting()
        self._namebar.write(self._name, color=ColorPair.GREEN)

    def finish(self, msg, installed=True):
        color = ColorPair.GREEN if installed else ColorPair.RED
        self._status.done(color=color)
        self._namebar.write(self._name, color=color)

    @property
    def height(self):
        return self._y

    @property
    def width(self):
        return self._x

    @property
    def name(self):
        return self._namebar

    @property
    def loader(self):
        return self._loader

    @property
    def status(self):
        return self._status

    @property
    def message(self):
        return self._message
