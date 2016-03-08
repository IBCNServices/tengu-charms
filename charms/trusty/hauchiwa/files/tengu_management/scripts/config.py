""" Config module"""
import os
from os.path import expanduser
import yaml
# self written modules and classes
from output import fail # pylint: disable=F0401


class Config(dict):
    """ Objects from this class represent a tengu config. """
    def __init__(self, config_path, default_path=None):
        """ Open config from config_path.
        If config does not exist, create new one from default_path
        if config_path == None, then saving config will not do anything."""
        self.config_path = config_path
        self.default_path = default_path
        if not os.path.isdir(tengu_dir()):
            os.makedirs(tengu_dir())
        if config_path is not None and os.path.isfile(self.config_path):
            src = self.config_path
        else:
            src = default_path
        try:
            with open(src, "r") as src_file:
                super(Config, self).__init__(yaml.load(src_file))
        except Exception:
            fail("failed opening config. Is there a config file at %s ?" % src)
            raise
        self.save()

    def save(self):
        """ Save config to config_path if _in_memory = false """
        # don't save if we don't have a place to save it yet
        if self.config_path:
            if not os.path.isdir(os.path.dirname(self.config_path)):
                os.makedirs(os.path.dirname(self.config_path))
            with open(self.config_path, 'w') as config_file:
                config_file.write(yaml.dump(dict(self.iteritems())))

    @property
    def dir(self):
        """ Returns the directory where the config is located"""
        return os.path.dirname(self.config_path)


def get_absolute_path(path):
    """ If path is absolute, give back path.
    If path is relative, give back absolute path from script_dir """
    if path is None:
        return path
    if path.startswith('/'):
        return path
    else:
        return '{}/{}'.format(script_dir(), path)


def script_dir():
    """ Directory where scripts are located """
    return os.path.realpath(os.path.dirname(__file__))


def tengu_dir():
    """ Tengu config directory """
    return expanduser("~/.tengu")


def config_exists(config_path):
    """ Does the config file exist? """
    return os.path.isfile(config_path)
