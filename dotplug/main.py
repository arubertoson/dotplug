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

from dotplug.tasks import mktask
# XXX: Utils
from dotplug.archive import ensure_archive
from dotplug.console import run, TaskBar, TaskStatus

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
    return TaskStatus.NOT_INSTALLED


# XXX:
# Move all functionality not related to running the actual process to other
# modules, this module should be dedicated to the producer consumer pattern


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
                task.message.clear()

            bar.message.write("Installing ...")
            await asyncio.sleep(2)
            result = await bar.loader.wait_for(task.install)

            bar.message.write("Creating Symlinks ...")
            await asyncio.sleep(2)
            if task.link is not None:
                result = await bar.loader.wait_for(task.make_links())

            await task.update_current()
            bar.message.clear()
            bar.message.write("Done")
        else:
            bar.message.write("Already Installed")
        bar.set_state(TaskStatus.SUCCESSFUL)


async def producer(q):
    """
    Producer creates our worker tasks
    """
    # XXX:
    # Hard coded for now, will be able to specify config setting in an rc file
    # located in the XDG_CONFIG_HOME directory
    #
    # * archive location
    # * install root location
    # * max threads
    # * config file location (unless given an absolute path will look here)
    #
    config = 'dotplug.json'
    with resources.open_text('dotplug.data', f'{config}') as f:
        data = json.loads(f.read())
        for idx, each in enumerate(data):
            task = mktask(each)
            # Each task get assigned a task that it'll own.
            task.bar = TaskBar(task.name, CONSOLE_MARGIN, idx + CONSOLE_MARGIN)
            await q.put(task)


async def consumer(q, seen):
    """
    Consume tasks in the queue until the queue is empty

    If the task grabbed from the queue still has unfinised dependencies put
    the task at the back of the queue, rinse and repeat until evrything is
    done.
    """
    while not q.empty():
        task = await q.get()

        # If task depends on other tasks we make sure that the task is only
        # operated on if all dependensies have been completed. Otherwise it
        # goes back into the products
        if task.depend and not all(d in seen for d in task.depend):
            # Put a little delay here to not hit the CPU to hard
            await asyncio.sleep(0.5)
            await q.put(task)
        else:
            await asyncio.create_task(install(task))
            seen.add(task.name)

        q.task_done()


async def main():
    # Assign a queue with a set size
    q = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)

    seen = set()

    p = producer(q)
    c = [consumer(q, seen) for x in range(MAX_QUEUE_SIZE)]

    return await asyncio.gather(p, *c)
