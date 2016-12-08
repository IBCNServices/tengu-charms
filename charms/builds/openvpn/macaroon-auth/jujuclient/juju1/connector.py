import os
import yaml

from ..exc import (
    EnvironmentNotBootstrapped,
)
from ..connector import BaseConnector


class Connector(BaseConnector):
    """Abstract out the details of connecting to state servers.

    Covers
    - finding state servers, credentials, certs for a named env.
    - verifying state servers are listening
    - connecting an environment or websocket to a state server.

    """

    def url_root(self):
        return "/environment"

    def juju_home(self):
        return os.path.expanduser(
            os.environ.get('JUJU_HOME', '~/.juju'))

    def parse_env(self, env_name):
        jhome = self.juju_home()

        # Look in the cache file first.
        cache_file = os.path.join(jhome, 'environments', 'cache.yaml')
        jenv = os.path.join(jhome, 'environments', '%s.jenv' % env_name)

        if os.path.exists(cache_file):
            try:
                return jhome, self.environment_from_cache(env_name, cache_file)
            except EnvironmentNotBootstrapped:
                pass
                # Fall through to getting the info from the jenv
        if not os.path.exists(jenv):
            raise EnvironmentNotBootstrapped(env_name)
        return jhome, self.environment_from_jenv(jenv)

    def environment_from_cache(self, env_name, cache_filename):
        with open(cache_filename) as fh:
            data = yaml.safe_load(fh.read())
            try:
                # environment holds:
                #   user, env-uuid, server-uuid
                environment = data['environment'][env_name]
                server = data['server-data'][environment['server-uuid']]
                return {
                    'user': environment['user'],
                    'password': server['identities'][environment['user']],
                    'environ-uuid': environment['env-uuid'],
                    'server-uuid': environment['server-uuid'],
                    'state-servers': server['api-endpoints'],
                    'ca-cert': server['ca-cert'],
                }
            except KeyError:
                raise EnvironmentNotBootstrapped(env_name)

    def environment_from_jenv(self, jenv):
        with open(jenv) as fh:
            data = yaml.safe_load(fh.read())
            return data
