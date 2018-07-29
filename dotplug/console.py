"""
This module contains curses implementation
"""
import inspect
import asyncio
import curses
import functools
import contextlib

from enum import IntEnum


@contextlib.asynccontextmanager
async def write(bar):
    try:
        yield bar.write
    finally:
        pass


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


@contextlib.contextmanager
def run(task_bar):
    try:
        task_bar.running()
        yield task_bar
    finally:
        task_bar.done()


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
    def write(self, msg, x=0, color=ColorPair.WHITE):
        self._bar.addstr(0, x, msg[:self._x - 1], curses.color_pair(color))

    def clear(self):
        self._bar.erase()


class TaskStatus(IntEnum):
    IDLE = 1
    RUNNING = 2
    DONE = 3
    SUCCESSFUL = 4
    FAILED = -1
    ALREADY_INSTALLED = 100
    NOT_INSTALLED = 200


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

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value: TaskStatus):
        self._status = value

    @set_status(TaskStatus.IDLE)
    def waiting(self):
        self.write('*', color=ColorPair.WHITE)

    @set_status(TaskStatus.RUNNING)
    def running(self):
        self.write('+', color=ColorPair.ORANGE)

    @set_status(TaskStatus.DONE)
    def done(self, color=ColorPair.ORANGE):
        self.write('-', color=color)


class LoaderBar(BaseBar):
    """
    Loader bar class
    """

    def __init__(self, x, y, width=4, sym='>'):
        super().__init__(x, y, width)

        self._loader = ['{}  ', ' {} ', '  {}']
        self._sym = sym

    def idle(self):
        self.clear()
        self.write('-')

    def update(self):
        res = self._loader.pop(0)
        self.write(res.format(self._sym))
        self._loader.append(res)

    async def wait_for(self, coro, *args):
        if inspect.iscoroutinefunction(coro):
            coro = coro()

        if asyncio.iscoroutine(coro):
            future = asyncio.create_task(coro)
        else:
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(None, coro, *args)

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
        _message = BaseBar(_loader.x + _loader.width, y, 60)

        _message.write(initial_message)

        # Assign
        self._name = name + ":"
        self._namebar = _namebar
        self._status = _status
        self._loader = _loader
        self._message = _message

        # Initial Status
        self.waiting()

    def waiting(self):
        self._status.waiting()
        self._loader.idle()
        self._namebar.write(self._name, color=ColorPair.GREEN)

    def running(self):
        self._status.running()
        self._namebar.write(self._name, color=ColorPair.ORANGE)

    def done(self, msg=''):
        if self.status.status == TaskStatus.SUCCESSFUL:
            color = ColorPair.GREEN
        else:
            color = ColorPair.RED
        self._status.done(color)
        self._namebar.write(self._name, color=color)

    def set_state(self, state: TaskStatus):
        self._status.status = state

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
