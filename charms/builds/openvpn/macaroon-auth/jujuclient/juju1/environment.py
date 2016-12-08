import os

from ..environment import BaseEnvironment

from . import connector
from . import facades
from . import rpc
from . import watch


class Environment(BaseEnvironment, rpc.RPC):
    version = 0

    def __init__(self, *args, **kw):
        super(Environment, self).__init__(*args, **kw)

        self.service = facades.Service(self)

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
        return "environment-{}".format(self.uuid)

    @property
    def juju_home(self):
        return os.environ.get('JUJU_HOME', '~/.juju')

    @property
    def url_root(self):
        return '/environment'

    def get_facades(self):
        return self._info.get('Facades')

    def get_facade_name(self, facade_dict):
        return facade_dict['Name']

    def get_facade_versions(self, facade_dict):
        return facade_dict['Versions']
