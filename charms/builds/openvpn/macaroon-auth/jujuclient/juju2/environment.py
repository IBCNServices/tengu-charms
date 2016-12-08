import os

from ..environment import BaseEnvironment

from . import connector
from . import facades
from . import rpc
from . import watch


class Environment(BaseEnvironment, rpc.RPC):
    version = 1

    def __init__(self, *args, **kw):
        super(Environment, self).__init__(*args, **kw)

        self.service = facades.Application(self)

    @classmethod
    def connector(cls):
        return connector.Connector

    @classmethod
    def watch_module(cls):
        return watch

    @classmethod
    def facade_class(cls):
        return facades.APIFacade

    @property
    def tag(self):
        return "model-{}".format(self.uuid)

    @property
    def juju_home(self):
        return os.environ.get('JUJU_DATA', '~/.local/share/juju')

    @property
    def url_root(self):
        return '/model'

    def get_facades(self):
        return self._info.get('facades')

    def get_facade_name(self, facade_dict):
        return facade_dict['name']

    def get_facade_versions(self, facade_dict):
        return facade_dict['versions']

    def get_charm(self, charm_url):
        """Get information about a charm in the environment.

        """
        return self.charms.info(charm_url)
