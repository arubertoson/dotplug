#!/usr/bin/env python3
"""
Using the producer/consumer pattern we generate the tasks we need to run and
limit the amount of work we can do at the same time.
"""
import os
import json
import shutil
import asyncio
from collections import defaultdict

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
        if not task.not_dest:
            state = await ensure_dest(task)
        else:
            state = TaskStatus.NOT_INSTALLED

        if not state == TaskStatus.ALREADY_INSTALLED:
            if task.type is not None:
                await ensure_archive(task)

            bar.message.write("Installing ...")
            await bar.loader.wait_for(task.install)

            bar.message.write("Creating Symlinks ...")
            if task.link is not None:
                await bar.loader.wait_for(task.make_links())

            bar.message.clear()
            bar.message.write("Done")
        else:
            bar.message.write("Already Installed")
        bar.set_state(TaskStatus.SUCCESSFUL)


async def _install_block(block):
    for app in block:
        await asyncio.create_task(install(app))


async def producer(q):
    """
    Producer creates our worker tasks
    """
    # XXX:
    # Temporary solution, there will be an rc file to contain information
    # regariding installation location.
    config = 'dotplug.json'
    with resources.open_text('data', f'{config}') as f:
        apps = {}
        for idx, each in enumerate(json.loads(f.read())):
            app = mkapp(each)
            app.bar = TaskBar(app.name, CONSOLE_MARGIN, idx + CONSOLE_MARGIN)
            apps[app.name] = app

    # Create install blocks of dependencies
    copy = apps.copy()
    depends = defaultdict(list)

    for name, node in copy.items():
        if not node.depend:
            depends[name].append(node)
            apps.pop(name)

    for name, node in apps.items():
        for dep in node.depend:
            if node not in depends[dep]:
                depends[dep].append(node)

    for block in depends.values():
        await q.put(_install_block(block))


async def consumer(q):
    while not q.empty():
        item = q.get_nowait()
        await asyncio.sleep(1)
        await item
        q.task_done()


async def main():
    # XXX:
    # argsparser to query necessary inputs, should be able to create a task
    # from the argsparser options and pass it along. Should only handle one
    # task or a config file of tasks.
    q = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)

    p = producer(q)
    c = [consumer(q) for x in range(MAX_QUEUE_SIZE)]

    return await asyncio.gather(p, *c)


if __name__ == '__main__':
    # producer()
    with ncurses() as screen:
        asyncio.run(main())
        input("")
