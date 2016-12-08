import copy
import logging
import json
import time

from .exc import (
    AlreadyConnected,
    EnvError,
)

log = logging.getLogger(__name__)


class BaseRPC(object):
    _upgrade_retry_delay_secs = 1
    _upgrade_retry_count = 60
    _auth = False
    _request_id = 1
    _debug = False
    _reconnect_params = None

    conn = None

    def check_op(self, op):
        raise NotImplementedError()

    def check_error(self, result):
        raise NotImplementedError()

    def get_response(self, result):
        raise NotImplementedError()

    def login_args(self, user, password):
        raise NotImplementedError()

    def redirect_info(self):
        return None

    def _rpc(self, op):
        op = self.check_op(op)
        result = self._rpc_retry_if_upgrading(op)
        if self.check_error(result):
            # The backend disconnects us on err, bug: http://pad.lv/1160971
            self.conn.connected = False
            raise EnvError(result)
        return self.get_response(result)

    def _rpc_retry_if_upgrading(self, op):
        """If Juju is upgrading when the specified rpc call is made,
        retry the call."""
        retry_count = 0
        result = {'Response': ''}
        while retry_count <= self._upgrade_retry_count:
            result = self._send_request(op)
            error = self.check_error(result)
            if error and 'upgrade in progress' in error:
                log.info("Juju upgrade in progress...")
                retry_count += 1
                time.sleep(self._upgrade_retry_delay_secs)
                continue
            break
        return result

    def _send_request(self, op):
        if self._debug:
            log.debug("rpc request:\n%s" % (json.dumps(op, indent=2)))
        self.conn.send(json.dumps(op))
        raw = self.conn.recv()
        result = json.loads(raw)
        if self._debug:
            log.debug("rpc response:\n%s" % (json.dumps(result, indent=2)))
        return result

    def login(self, password, user="user-admin"):
        """Login gets shared to watchers for reconnect.

        """
        if self.conn and self.conn.connected and self._auth:
            raise AlreadyConnected()

        # Store for constructing separate authenticated watch connections.
        self._creds = {'password': password, 'user': user}
        result = self._rpc(self.login_args(user, password))
        self._auth = True
        self._info = copy.deepcopy(result)
        return result

    def set_reconnect_params(self, params):
        self._reconnect_params = params

    def reconnect(self):
        if self.conn:
            self._auth = False
            self.conn.close()
        if not self._reconnect_params:
            return False

        log.info("Reconnecting client")
        self.conn = self.connector().connect_socket_loop(
            self._reconnect_params['url'],
            self._reconnect_params['ca_cert'])
        self.login(self._reconnect_params['password'],
                   self._reconnect_params['user'])
        return True
