"""
This module contains the Application containers
"""
import os
import json
import shutil
import asyncio

from dotplug.archive import untar

ARCHIVE_DIRECTORY = os.environ['_BASE_ARCHIVES']
INSTALL_LOCATION = os.environ['_BASE_OPT']
DEFAULT_USER_BIN = 'XDG_BIN_HOME'


class BaseApp:
    def __init__(
            self,
            name,
            version,
            build,
            type=None,
            repo=None,
            link=None,
            depend=None,
            bar=None,
            force=False,
            not_dest=False,
    ):

        self.name = name
        self.version = version
        self.type = type
        self.build = build
        self.repo = repo
        self.force = force
        self.bar = bar

        self.not_dest = not_dest
        self.link = link

        depend = depend or set()
        if not isinstance(depend, set):
            depend = set(depend)
        self.depend = depend

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return str(self)

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

    async def make_links(self):
        src = self.link.get('src')
        targets = self.link.get('targets')
        dest = self.link.get('dest', None)

        if dest is None:
            dest = os.environ[DEFAULT_USER_BIN]

        try:
            src = src.format(self)
        except KeyError:
            pass

        try:
            src = src.format(**os.environ)
        except KeyError:
            pass

        for target in targets:
            trgt = os.path.join(src, target)
            src = os.path.join(dest, target)

            # Remove already existing links
            try:
                os.remove(src)
            except FileNotFoundError:
                pass

            os.symlink(trgt, src)


class AppImage(BaseApp):
    def install(self):
        app = os.path.join(self.dest, self.name)
        shutil.copyfile(self.archive, app)
        os.chmod(app, 0o755)


class AppBinary(BaseApp):
    """
    Binarys usually comes as a package that we need to unpack to a location.
    """

    def install(self):
        untar(self.archive, self.dest)


class AppCommand(BaseApp):
    def __init__(self, cmds, *args, **kw):
        super().__init__(*args, **kw)
        self.cmds = cmds

    async def command(self):
        for cmd in self.cmds:
            proc = await asyncio.create_subprocess_shell(
                cmd.format(self),
                shell=True,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, stderr = await proc.communicate()

    async def install(self):
        await self.command()


class AppSource(AppCommand):
    """
    Sources we have to build ourselves with provided build flags.
    """

    async def install(self):
        # with tempfile.TemporaryDirectory() as tmp:
        tmp = f'/tmp/dotplug/{self.name}'
        if os.path.exists(tmp):
            shutil.rmtree(tmp)

        untar(self.archive, tmp)
        os.chdir(tmp)

        await self.command()


def mkapp(data):
    """
    App Factory
    """
    cls = {
        'appimage': AppImage,
        'binary': AppBinary,
        'source': AppSource,
        'command': AppCommand,
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
