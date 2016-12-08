import errno
import logging
import os
import re
import socket
import ssl
import time
import warnings

import websocket

from .exc import EnvError

try:
    SSL_VERSION = ssl.PROTOCOL_TLSv1_2
except AttributeError:
    SSL_VERSION = ssl.PROTOCOL_TLSv1
    warnings.warn(
        'This version of Python does not support TLSv1.2. Please use Python '
        '2.7.9+ or 3.4+ instead. Attempting to use TLSv1 - may not work with '
        'all versions of Juju.', RuntimeWarning)

log = logging.getLogger(__name__)


class BaseConnector(object):
    """Abstract out the details of connecting to state servers.

    Covers
    - finding state servers, credentials, certs for a named env.
    - verifying state servers are listening
    - connecting an environment or websocket to a state server.

    """

    retry_conn_errors = (errno.ETIMEDOUT, errno.ECONNREFUSED, errno.ECONNRESET)

    def url_root(self):
        raise NotImplementedError()

    def juju_home(self):
        raise NotImplementedError()

    def parse_env(self, env_name):
        raise NotImplementedError()

    def run(self, cls, env_name):
        """Given an environment name, return an authenticated client to it."""
        jhome, data = self.parse_env(env_name)
        cert_path = self.write_ca(env_name, data.get('ca-cert'))
        address = self.get_state_server(data)
        if not address:
            return
        return self.connect_env(
            cls, address, env_name, data['user'], data['password'],
            cert_path, data.get('environ-uuid'))

    def connect_env(self, cls, address, name, user, password,
                    cert_path=None, env_uuid=None):
        """Given environment info return an authenticated client to it."""
        endpoint = "wss://%s" % address
        if env_uuid:
            endpoint += self.url_root() + "/%s/api" % env_uuid
        env = cls(endpoint, name=name, ca_cert=cert_path, env_uuid=env_uuid)
        if not user.startswith('user-'):
            user = "user-%s" % user

        redirect_info = env.redirect_info()
        if not redirect_info:
            env.login(user=user, password=password)
            return env

        cert_path = self.write_ca(name, redirect_info['ca-cert'])
        servers = [
            s for servers in redirect_info['servers']
            for s in servers if s["scope"] == 'public'
        ]
        for server in servers:
            endpoint = "wss://{value}:{port}".format(**server)
            if env_uuid:
                endpoint += self.url_root() + "/%s/api" % env_uuid
            env = cls(
                endpoint, name=name, ca_cert=cert_path, env_uuid=env_uuid)
            try:
                result = env.login(user=user, password=password)
                if 'discharge-required-error' in result:
                    continue
                return env
            except EnvError:
                continue

    @classmethod
    def connect_socket(cls, endpoint, cert_path=None):
        """Return a websocket connection to an endpoint."""
        log.debug("Connecting to %s", endpoint)

        sslopt = cls.get_ssl_config(cert_path)
        return websocket.create_connection(
            endpoint, origin=endpoint, sslopt=sslopt)

    @staticmethod
    def get_ssl_config(cert_path=None):
        sslopt = {'ssl_version': SSL_VERSION}
        if cert_path:
            sslopt['ca_certs'] = cert_path
            # ssl.match_hostname is broken for us, need to disable per
            # https://github.com/liris/websocket-client/issues/105
            # when that's available, we can just selectively disable
            # the host name match, for now we have to disable cert
            # checking :-(
            sslopt['check_hostname'] = False
        else:
            sslopt['cert_reqs'] = ssl.CERT_NONE
        return sslopt

    def connect_socket_loop(self, endpoint, cert_path=None, timeout=120):
        """Retry websocket connections to an endpoint till its connected."""
        t = time.time()
        while (time.time() > t + timeout):
            try:
                return self.connect_socket(endpoint, cert_path)
            except socket.error as err:
                if err.errno not in self.retry_conn_errors:
                    raise
                time.sleep(1)
                continue

    def write_ca(self, cert_name, cert):
        """Write ssl ca to the given directory.

        """
        if not cert:
            return None

        cert_dir = os.path.join(self.juju_home(), 'jclient')
        if not os.path.exists(cert_dir):
            os.mkdir(cert_dir)

        cert_name = cert_name.replace(os.path.sep, '_')
        cert_path = os.path.join(cert_dir, '%s-cacert.pem' % cert_name)
        with open(cert_path, 'w') as ca_fh:
            ca_fh.write(cert)
        return cert_path

    def get_state_server(self, data):
        """Given a list of state servers, return one that's listening."""
        for s in data['state-servers']:
            if self.is_server_available(s):
                return s

    @staticmethod
    def split_host_port(server):
        m = re.match('(.*):(.*)', server)
        if not m:
            raise ValueError("Not an ipaddr/port {!r}".format(server))
        address = m.group(1).strip("[]")
        port = m.group(2)
        return address, port

    def is_server_available(self, server):
        """ Given address/port, return true/false if it's up """
        address, port = self.split_host_port(server)
        try:
            socket.create_connection((address, port), 3)
            return True
        except socket.error as err:
            if err.errno in self.retry_conn_errors:
                return False
            else:
                raise
