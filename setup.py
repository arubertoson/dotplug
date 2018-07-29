#!/usr/bin/env python

from distutils.core import setup

setup(
    name='dotplug',
    version='0.0.1',
    description='Python Distribution Utilities',
    author='Marcus Albertsson',
    author_email='marcus.arubertoson@gmail.com',
    url='https://github.com/arubertoson/dotplug',
    packages=['dotplug'],
    license='MIT',
    install_requires=[
        'aiohttp',
        'aiofiles',
        'uvloop',
    ],
    entry_points={
        'console_scripts': ['dot=dotplug:_main'],
    },
)
