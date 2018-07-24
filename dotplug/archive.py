"""
This module contains functionality relating to archives
"""
import os
import tarfile

import aiohttp
import aiofiles


def untar(archive, dest):
    """
    Unpacks the tarfile to our install location
    """
    with tarfile.open(archive) as tar:
        members = []
        for m in tar:
            if not m.isreg():
                continue
            members.append(m)

        prefix = os.path.commonprefix([m.name for m in members])
        for m in members:
            m.name = os.path.relpath(m.name, prefix)
        tar.extractall(dest, members=members)


def validate_tar(archive):
    """
    Ensure we are working with a non corrupt tarfile
    """
    try:
        with tarfile.open(archive) as tar:
            for m in tar:
                if m.isreg():
                    check = tar.extractfile(m.name)
                    for chunk in iter(lambda: check.read(1024), b''):
                        pass
    except (EOFError):
        res = False
    else:
        res = True
    return res


async def download(session, task):
    """
    Download repo given from the task url
    """
    archive, bar = task.archive, task.bar
    async with session.get(task.url) as response:
        size = int(response.headers.get('content-length', 0))

        # Download archive if does not exist
        dirname = os.path.dirname(archive)
        if not os.path.exists(dirname):
            os.makedirs(os.path.dirname(archive))

        async with aiofiles.open(archive, mode='wb') as f:
            total = 0
            async for chunk in response.content.iter_chunked(1024):
                await f.write(chunk)
                total += len(chunk)

                bar.message.write(f'{total}/{size} ... Downloading')
            bar.message.clear()


async def ensure_archive(task):
    """
    Ensure that the taks archive exists and we have something to act upon.
    """
    archive, bar = task.archive, task.bar

    # Download archive if it doesn't exist
    if os.path.exists(archive):
        if not task.type == 'appimage':
            bar.message.write('Validating Archive ... ')
            valid = await bar.loader.wait_for(validate_tar, archive)
        valid = True
    else:
        valid = False

    if not valid:
        async with aiohttp.ClientSession() as session:
            await download(session, task)
