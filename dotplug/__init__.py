"""
Entry Point
"""
import asyncio

from dotplug.main import main
from dotplug.console import ncurses


def _main():

    with ncurses():
        asyncio.run(main())
        input("")
