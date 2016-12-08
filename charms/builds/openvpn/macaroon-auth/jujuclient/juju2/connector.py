import os
import socket
import subprocess
import yaml

from ..connector import BaseConnector
from .. import utils


class Connector(BaseConnector):
    """Abstract out the details of connecting to state servers.

    Covers
    - finding state servers, credentials, certs for a named env.
    - verifying state servers are listening
    - connecting an environment or websocket to a state server.

    """

    def url_root(self):
        return "/model"

    def juju_home(self):
        return os.path.expanduser(
            os.environ.get('JUJU_DATA', '~/.local/share/juju'))

    def _parse_env_name(self, env_name):
        """Given an environment name such as is returned from `juju switch`,
        return a tuple of (controller_name, model_name, owner). In many cases
        owner is set to None.

        Handles any of these formats::

            controller:model
            controller:user@local/model

        """
        owner = None
        if ':' in env_name:
            controller_name, remainder = env_name.split(':')
        else:
            raise Exception('Invalid environment name: %s', env_name)

        if '/' in remainder:
            owner, model_name = remainder.split('/')
        else:
            model_name = remainder

        return controller_name, model_name, owner

    def parse_env(self, env_name):
        """Provide API and access details for a juju2 model.

        """
        # The juju2 model access parameters are spread across multiple
        # locations. Use commands to collect as much of this data as
        # possible and use files only when required.
        jhome = self.juju_home()

        controller_name, model_name, owner = self._parse_env_name(env_name)
        controller = self.get_controller(controller_name)
        model = self.get_model(controller_name, model_name, owner)
        account = self.get_account(jhome, controller_name)

        return jhome, {
            'user': account['user'],
            'password': account.get('password', ''),
            'environ-uuid': model['model-uuid'],
            'server-uuid': controller['uuid'],
            'state-servers': controller['api-endpoints'],
            'ca-cert': controller['ca-cert'],
        }

    def get_controller(self, controller_name):
        """Return info for the specified or current controller.

        """
        output = utils.check_output(
            ['juju', 'list-controllers', '--format=yaml'])

        data = yaml.safe_load(output)
        try:
            return data['controllers'][controller_name]
        except KeyError:
            raise Exception(
                "Controller '{}' not found in `juju list-controllers`".format(
                    controller_name))

    def get_model(self, controller_name, model_name, owner):
        """Return info for the specified or current model.

        """
        if owner is None:
            model = '{}:{}'.format(controller_name, model_name)
        else:
            model = '{}:{}/{}'.format(controller_name, owner, model_name)
        try:
            # post beta16 format
            output = utils.check_output(
                ['juju', 'show-model', model, '--format=yaml'])
        except subprocess.CalledProcessError:
            # pre beta16 format
            output = utils.check_output(
                ['juju', 'show-model', '-m', model, '--format=yaml'])
        return yaml.safe_load(output)[model_name]

    def get_account(self, jhome, controller_name):
        """Return user info for the specified controller.

        """
        # The password is not available from the cli, so parse a file for it.
        account_filename = os.path.join(jhome, 'accounts.yaml')

        try:
            with open(account_filename) as fh:
                data = yaml.safe_load(fh.read())
                return data['controllers'][controller_name]
        except Exception:
            raise Exception(
                "Couldn't find account for {} in {}".format(
                    controller_name, account_filename))

    def is_server_available(self, server):
        """Given address/port, return true/false if it's up.

        """
        address, port = self.split_host_port(server)
        try:
            socket.create_connection((address, port), 3)
            return True
        except socket.error as err:
            if err.errno in self.retry_conn_errors:
                return False
            else:
                raise
