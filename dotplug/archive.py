"""
This module contains functionality relating to archives
"""
import os
import abc
import tarfile
import zipfile
import asyncio

import aiohttp
import aiofiles


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
            validator = {
                'tar': validate_tar,
                'zip': validate_zip,
            }[task.type]
            valid = await bar.loader.wait_for(validator, archive)
        valid = True
    else:
        valid = False

    if not valid:
        async with aiohttp.ClientSession() as session:
            await download(session, task)


class AIOCompressedFile(abc.ABC):
    """
    Base Object for Compressed File Archives
    """
    magic = None
    file_type = None
    mime_type = None
    proper_extensio = None

    def __init__(self, filename):
        self.filename = filename
        self.accessor = self.open

    @classmethod
    def is_magic(cls, data):
        return data.startswith(cls.magic)

    async def __aenter__(self):
        await self.open()

    async def __aexit__(self, *args):
        return asyncio.create_task(self.close())

    @abc.abstractmethod
    def open(self):
        return None

    @abc.abstractmethod
    def close(self):
        return None

    @abc.abstractmethod
    def validate(self):
        return None

    @abc.abstractmethod
    def unpack(self, location):
        return None


class ZipFile(zipfile.ZipFile):
    """
    Override on the extract method in ZipFile

    Currently ZipFile does not retain the proper permissions, this override
    deals with that issue
    """

    def extract(self, member, path=None, pwd=None):
        if not isinstance(member, zipfile.ZipInfo):
            member = self.getinfo(member)

        if path is None:
            path = os.getcwd()

        ret_val = self._extract_member(member, path, pwd)
        # XXX:
        # Currently just make everything executable, this is not optimal but a
        # workaround that is currently needed
        os.chmod(ret_val, 0o755)
        return ret_val


class ZipArchive(ArchiveFile):
    magic = '\x50\x4b\x03\x04'
    file_type = 'zip'

    def open(self):
        return ZipFile(self.filename)

    def unpack(self, location):
        """
        Unpacks the zipfile to provided dest location

        If the archive contains a top directory, it will be ignored
        """
        relpath = os.path.relpath

        with ZipFile(archive) as z:
            prefix = os.path.commonprefix(z.namelist())
            for m in z.filelist:
                if m.is_dir() or m.filename in ('.', '/'):
                    continue
                m.filename = relpath(m.filename, prefix)
                z.extract(m, path=dest)


def unzip(archive, dest):
    """
    Unpacks the zipfile to provided dest location
    """
    relpath = os.path.relpath

    with ZipFile(archive) as z:
        prefix = os.path.commonprefix(z.namelist())
        for m in z.filelist:
            if m.is_dir() or m.filename in ('.', '/'):
                continue
            m.filename = relpath(m.filename, prefix)
            z.extract(m, path=dest)


def untar(archive, dest):
    """
    Unpacks the tarfile to provided dest location
    """
    relpath = os.path.relpath

    try:
        with tarfile.open(archive) as tar:
            members = [m for m in tar if m.isreg()]

            prefix = os.path.commonprefix([m.name for m in members])
            for m in members:
                m.name = relpath(m.name, prefix)
            tar.extractall(dest, members=members)
    except tarfile.ReadError as e:
        raise tarfile.ReadError('{} is bad archive'.format(archive))


def validate_zip(archive):
    """
    Ensure we are working with a non corrupt zipfile
    """
    with ZipFile(archive) as z:
        if z.testzip() is not None:
            return False
    return True


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
