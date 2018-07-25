"""
Entry Point
"""
import asyncio

from dotplug.main import main
from dotplug.console import ncurses


def _main():

    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    with ncurses():
        asyncio.run(main())
        input("")
