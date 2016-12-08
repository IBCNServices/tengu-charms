import base64
import json
import logging
import os

from ..rpc import BaseRPC
from ..exc import LoginRequired, EnvError

log = logging.getLogger(__name__)


class RPC(BaseRPC):

    def check_op(self, op):
        if (not self._auth and
                op.get("request") not in (
                    "Login", "RedirectInfo")):
            raise LoginRequired()

        if 'params' not in op:
            op['params'] = {}

        if 'version' not in op:
            if hasattr(self, 'version'):
                op['version'] = self.version
            else:
                raise KeyError('Operation is missing "Version": {}'.format(op))

        op['request-id'] = self._request_id
        self._request_id += 1
        return op

    def check_error(self, result):
        return result.get('error')

    def get_response(self, result):
        return result['response']

    def login_args(self, user, password):
        d = {
            "type": "Admin",
            "request": "Login",
            "version": 3,
            "params": {
                "auth-tag": user,
                "credentials": password,
                "macaroons": [],
            }
        }

        # If we have a user and password, proceed directly to
        # user/pass authentication with the api server.
        if user and password:
            return d

        # Otherwise (in a shared controller scenario, password
        # will be blank), try macaroon authentication.
        with open(os.path.expanduser('~/.go-cookies'), 'r') as f:
            cookies = json.load(f)

        base64_macaroons = [
            c['Value'] for c in cookies
            if c['Name'].startswith('macaroon-') and c['Value'] and
            c['CanonicalHost'] in self.endpoint
        ]

        json_macaroons = [
            json.loads(base64.b64decode(value).decode('utf-8'))
            for value in base64_macaroons
        ]
        d["params"]["macaroons"] = json_macaroons
        if json_macaroons:
            d["params"]["auth-tag"] = ''

        return d

    def redirect_info(self):
        d = {
            "type": "Admin",
            "request": "RedirectInfo",
            "version": 3,
        }
        try:
            return self._rpc(d)
        except EnvError as e:
            if e.message == 'not redirected':
                return None
            raise
