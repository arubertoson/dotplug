#!/usr/bin/env python3
"""
Using the producer/consumer pattern we generate the tasks we need to run and
limit the amount of work we can do at the same time.
"""
import os
import json
import shutil
import asyncio

from importlib import resources

from dotplug.tasks import mkapp
from dotplug.archive import ensure_archive
from dotplug.console import ncurses, run, TaskBar, TaskStatus

MAX_QUEUE_SIZE = 6
CONSOLE_MARGIN = 4


# XXX:
# Just in  general the write messages needs to be hanled better, it should be
# easy to unsubscripe from curses without hacing to change lines all over.
async def ensure_dest(task):
    """
    Dispatch to correct install function
    """
    version, dest, bar = task.version, task.dest, task.bar

    if os.path.exists(dest):
        if task.force:
            shutil.rmtree(dest)
        else:
            bar.message.write(f'Already Installed {version}')
            return TaskStatus.ALREADY_INSTALLED
    os.makedirs(dest)
    return TaskStatus.NOT_INSTALLED


async def install(task):
    """
    Perform all steps necessary for app installation
    """
    with run(task.bar) as bar:
        state = await ensure_dest(task)

        if not state == TaskStatus.ALREADY_INSTALLED:
            await ensure_archive(task)

            bar.message.write("Installing ...")
            await bar.loader.wait_for(task.install)

            bar.message.write("Creating Symlinks ...")
            await bar.loader.wait_for(task.mklinks)

            bar.message.clear()
            bar.message.write("Done")
        else:
            bar.message.write("Already Installed")
        bar.set_state(TaskStatus.SUCCESSFUL)


def producer():
    """
    Producer creates our worker tasks
    """

    # XXX:
    # Temporary solution, there will be an rc file to contain information
    # regariding installation location.
    config = 'dotplug.json'
    with resources.open_text('data', f'{config}') as f:
        apps = json.loads(f.read())

    # XXX:
    # The queue system needs some more research, I really want to make it work
    tasks = []
    for idx, app in enumerate(apps):
        app = mkapp(app)
        app.bar = TaskBar(app.name, CONSOLE_MARGIN, idx + CONSOLE_MARGIN)

        # await q.put(install(app))
        tasks.append(install(app))
    return tasks


async def main():
    # XXX:
    # argsparser to query necessary inputs, should be able to create a task
    # from the argsparser options and pass it along. Should only handle one
    # task or a config file of tasks.
    # q = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)

    tasks = producer()
    return await asyncio.gather(*tasks)
    # return await asyncio.gather(producer(q), consume(q))
    # await asyncio.gather(consume(q), producer(q))


if __name__ == '__main__':
    with ncurses() as screen:
        asyncio.run(main())
        input("")
