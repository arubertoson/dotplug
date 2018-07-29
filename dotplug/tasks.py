"""
This module contains the Application containers
"""
import os
import shutil
import asyncio

from dotplug.archive import untar, unzip

# XXX:
# Better handling of global variables, as it stands this will raise a keyerror
# if not set - which is not ideal
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

            if not os.path.exists(trgt):
                continue

            # Remove already existing links
            try:
                os.remove(src)
            except FileNotFoundError:
                pass

            os.symlink(trgt, src)

    async def update_current(self):
        dest = self.dest
        if not os.path.exists(dest):
            return

        current = os.path.join(os.path.dirname(self.dest), 'current')
        if os.path.islink(current):
            os.remove(current)

        os.symlink(dest, current, target_is_directory=True)


# XXX:
# Installing needs to have proper exitcodes we can handle, currently if an
# install failes nothing happends and the program trots along happily


class AppImage(BaseApp):
    def install(self):
        app = os.path.join(self.dest, self.name)
        shutil.copyfile(self.archive, app)
        os.chmod(app, 0o755)


class AppCommand(BaseApp):
    def __init__(self, *args, cmds=None, **kw):
        super().__init__(*args, **kw)
        self.cmds = cmds

    async def command(self):
        clear = self.bar.message.clear
        write = self.bar.message.write

        for cmds in self.cmds:
            cwd = cmds.get('cwd')
            if cwd is not None:
                cwd = os.path.join(os.getcwd(), cwd)

            # Update Env
            env = cmds.get('env')
            if env is not None:
                _os_env = os.environ.copy()
                for k, v in env.items():
                    v = os.path.expandvars(v)
                    _os_env[k] = v
                env = _os_env

            for cmd in cmds.get('cmds', []):
                command = cmd.format(self)

                # XXX:
                # Really need a better way to handle messages
                clear()
                write(command)
                await asyncio.sleep(2)

                proc = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                    env=env,
                    cwd=cwd,
                )
                stdout, stderr = await proc.communicate()

            # XXX:
            # If build fail we need to communicate that
            # if not proc.returncode == 0:
            #     #     # self.bar.message.write(stderr)
            #     print(stderr)
            #     await asyncio.sleep(2)

    async def install(self):
        await self.command()


class AppBinary(AppCommand):
    """
    Binarys usually comes as a package that we need to unpack to a location.
    """

    async def install(self):
        untar(self.archive, self.dest)
        if self.cmds:
            # Some commands are run from the destination folder whereas some
            # other commands are just standalone commands
            try:
                os.chdir(self.dest)
            except FileNotFoundError:
                pass
            await self.command()


class AppSource(AppCommand):
    """
    Sources we have to build ourselves with provided build flags.
    """

    async def install(self):
        # XXX:
        # need proper cleanup after build and install is complete
        tmp = f'/tmp/dotplug/{self.name}'
        if os.path.exists(tmp):
            shutil.rmtree(tmp)

        # XXX:
        # Need a better way to handle types
        func = {
            'tar': untar,
            'zip': unzip,
        }[self.type]

        func(self.archive, tmp)
        os.chdir(tmp)

        await self.command()


def mktask(data):
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
