"""
This module contains curses implementation
"""
import asyncio
import curses
import contextlib

from enum import IntEnum


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

        yield
    finally:
        curses.echo()
        curses.endwin()


def refresh_bar(method):
    """
    Forces redraw on screen with objects having a bar
    """

    @functools.wraps(method)
    def wrapper(inst, *args, **kw):
        method(inst, *args, **kw)
        inst._refresh()

    return wrapper


class Colors(IntEnum):
    GREEN = 10
    RED = 20
    ORANGE = 30


class TitleBar:
    def __init__(x, y):
        pass


class ProgressBar:
    def __init__(x, y):
        pass

    def update(self, value):
        pass


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
    def write(self, msg, x=0):
        self._bar.addstr(0, x, msg)

    def clear(self):
        self._bar.erase()


class StatusBar(BaseBar):
    """
    Status bar class
    """

    def __init__(self, x, y, width=3):
        super().__init__(x, y, width)
        self._status = None

    @property
    def status(self):
        return self._status

    def waiting(self):
        pass

    def working(self):
        pass

    def done(self):
        pass


class LoaderBar(BaseBar):
    """
    Loader bar class
    """

    def __init__(self, x, y, width=6, sym='>'):
        super().__init__(x, y, width)

        self._loader = ['  {}', ' {} ', '{}  ']

    def idle(self):
        self.write(' - ')

    def update(self):
        res = self._loader.pop()
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


class TaskBar(BaseBar):
    """
    Task Bar Format:

        [Status][Name][Loader][Message]

    """

    def __init__(self, name, x, y, margin=12):
        super().__init__(x, y, margin)

        self._ = name
        self._x = x
        self._y = y
        self._margin = margin

        # Static
        _static = curses.newwin(1, margin, y, x)
        curses.init_pair(156 + 1, 156, -1)
        _static.addstr(0, 0, name, curses.color_pair(157))
        _static.addstr(0, margin - 2, '|')
        _static.refresh()

        # Loader
        loader_margin = (x + margin)
        loader_width = 6
        _loader = curses.newwin(1, loader_width, y, loader_margin)

        # Status
        status_margin = (loader_margin + loader_width)
        status_width = 60
        _status = curses.newwin(1, 0, y, status_margin)
        _status.addstr(0, 0, '| Status')
        _status.addstr(0, status_width - 2, ']')
        _status.refresh()

        # Assign
        self._static = _static
        self._loader = _loader
        self._status = _status

        self.set_loader_idle()

    @property
    def name(self):
        return self._name

    @property
    def height(self):
        return self._y

    @property
    def width(self):
        return self._x

    @property
    def loader(self):
        return self._loader

    @property
    def status(self):
        return self._status
