"""
"""
import os
import json
import asyncio


class Links:
    """
    Handles the authoring of symlinks
    """


class Commands:
    """
    Command generator

    The command class generates async command built from given:
        * work directory
        * environment variables
        * flags

    """

    def __init__(self, cmds=None, flags=None, env=None, cwd=None):
        self.cmds = cmds or []
        self.flags = flags or {}
        self.env = env or {}
        self.cwd = cwd or '.'

    def _replace_cmd_flags(self, cmd):
        """
        Replace flags in commands by extra build flags
        """
        for flag, values in self.flags.items():
            cmd = cmd.format(**{flag: ' '.join(values)})
        return cmd

    def _update_env(self):
        """
        Update current environment with additional variables
        """
        if self.env is not None:
            _os_env = os.environ.copy()
            for k, v in self.env.items():
                v = os.path.expandvars(v)
                _os_env[k] = v
            return _os_env
        else:
            return {}

    def _set_cwd(self):
        """
        Get current work directory
        """
        if self.cwd is not None:
            return os.path.join(os.getcwd(), self.cwd)

    def __iter__(self):
        cwd = self._set_cwd()
        for cmd in self.cmds:
            cmd = self._replace_cmd_flags(cmd)
            env = self._update_env()
            yield asyncio.create_subprocess_shell(cmd, env=env, cwd=cwd)


class Description:
    """
    A part is simply a part of a recipe

    It can be any kind of dependency that is required to build the end result
    """

    def __init__(self, json_data):

        # Needed
        self.name = json_data['name']
        self.version = json_data['version']

        # XXX:
        # Type should be used in a factory to determine build type
        # Currently we have
        #   * appimage (application archive)
        #   * binaries (prebuilt binaries)
        #   * source (needs build step)
        self.type = json_data['type']

        # Optional
        self.envs = json_data.get('envs', {})
        self.links = json_data.get('links', [])
        self.depends = json_data.get('depends', [])
        self.commands = Commands(json_data.get('commands', []))

        # Immutable
        self._repo = json_data.get('repo,' '')

    @property
    def repo(self):
        return self._repo.format(version=self.version)

    @property
    def archive(self):
        """
        """
        # XXX:
        # Using mimetypes or whatever figure out what archive type we need to
        # use from archive module. Most likely best with an archive factory
        # The factory would figure out what type the archive is and use the
        # correct object to unpack
        # return os.path.join(
        #     ARCHIVE_DIRECTORY,
        #     self.name,
        #     f'{self.name}-{self.version}.{self.type},
        # )

    @property
    def destination(self):
        """
        """
        # return os.path.join(
        #     DOTROOT,
        #     self.name,
        #     self.version,
        # )

    def run(self):
        install = {
            'appimage': 'install app',
            'binary': 'install binary',
            'source': 'install source'
        }
        install()
        if self.commands:
            for cmd in self.commands:
                print(cmd)


def from_recipe(input_file):
    """
    Generate Tasks from a recipe json

    A recipe will look for available products and try to produce the final
    result.

    It has some special fields that let's you override the destination.
    """

    # XXX:
    # Since we should be able to override certain options through the command
    # line it would make sense to read the json earlier and override the
    # results there. This function should take a dict/parameeters and have
    # nothing to do with the actual generation of data to act upon.
    #
    # To continue it should have the necessary information to override task
    # state to. It exists soley generate and modify the description list and
    # pass it on.
    with open(input_file) as f:
        data = json.loads(f.read())

    destination = data.get('dest', None)


class Task:
    def __init__(self, description, bar=None):

        # Immutable
        self._desc = description
        self._bar = bar

    @property
    def desc(self):
        return self._desc

    @property
    def bar(self):
        return self._bar
