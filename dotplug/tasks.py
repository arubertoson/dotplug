"""
This module contains the Application containers
"""
import os
import json
import tempfile
import shutil
import asyncio

from dataclasses import dataclass, field

from dotplug.console import TaskBar
from dotplug.archive import untar

ARCHIVE_DIRECTORY = os.environ['_BASE_ARCHIVES']
INSTALL_LOCATION = os.environ['_BASE_OPT']


@dataclass
class Links:
    dest: str
    targets: list

    def __post_init__(self):
        dest = self.dest
        if dest in os.environ:
            self.dest = os.environ[dest]

    def make_from(self, srcdir):
        dest = self.dest

        for target in self.targets:
            trgt = os.path.join(srcdir, target)
            src = os.path.join(dest, target)

            # Remove already existing links
            try:
                os.remove(src)
            except FileNotFoundError:
                pass

            os.symlink(trgt, src)


@dataclass
class BaseApp:
    name: str
    version: str
    type: str
    build: str
    link: Links
    repo: str
    force: bool = False
    bar: TaskBar = None

    def __post_init__(self):
        if not isinstance(self.link, Links):
            self.link = Links(**self.link)

    @property
    def url(self):
        return self.repo.format(version=self.version, type=self.type)

    @property
    def archive(self):
        return os.path.join(
            ARCHIVE_DIRECTORY,
            self.name,
            f'{self.name}-{self.version}.{self.type}',
        )

    @property
    def dest(self):
        return os.path.join(
            INSTALL_LOCATION,
            self.name,
            self.version,
        )

    def make_links(self):
        self.link.make_from(self.dest)


@dataclass
class AppImage(BaseApp):
    def install(self):
        app = os.path.join(self.dest, self.name)
        shutil.copyfile(self.archive, app)
        os.chmod(app, 0o755)

    def mklinks(self):
        self.link.make_from(self.dest)


@dataclass
class AppBinary(BaseApp):
    """
    Binarys usually comes as a package that we need to unpack to a location.
    """

    def install(self):
        untar(self.archive, self.dest)

    def mklinks(self):
        self.link.make_from(os.path.join(self.dest, 'bin'))


@dataclass
class AppSource(BaseApp):
    """
    Sources we have to build ourselves with provided build flags.
    """

    cmds: list = field(default_factory=list)

    async def install(self):
        # with tempfile.TemporaryDirectory() as tmp:
        tmp = f'/tmp/dotplug/{self.name}'
        if os.path.exists(tmp):
            shutil.rmtree(tmp)

        untar(self.archive, tmp)
        os.chdir(tmp)

        for cmd in self.cmds:
            proc = await asyncio.create_subprocess_shell(
                cmd.format(self),
                shell=True,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, stderr = await proc.communicate()

    def mklinks(self):
        self.link.make_from(os.path.join(self.dest, 'bin'))


def mkapp(data):
    """
    App Factory
    """
    cls = {
        'appimage': AppImage,
        'binary': AppBinary,
        'source': AppSource,
    }[data['build']]
    return cls(**data)


if __name__ == '__main__':
    from importlib import resources
    with resources.open_text('data', 'dotplug.json') as f:
        tasks = json.loads(f.read())

    print(dir(AppSource.install))
    # for each in tasks:

    # print(dir(each.install))
    # task = BaseApp(**each)
    # print(task.url)
    # print(task.dest)
    # print(task.archive)

    # task.make_links()
