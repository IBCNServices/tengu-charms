import logging

from ..rpc import BaseRPC
from ..exc import LoginRequired

log = logging.getLogger(__name__)


class RPC(BaseRPC):

    def check_op(self, op):
        if not self._auth and not op.get("Request") == "Login":
            raise LoginRequired()

        if 'Params' not in op:
            op['Params'] = {}

        if 'Version' not in op:
            if hasattr(self, 'version'):
                op['Version'] = self.version
            else:
                raise KeyError('Operation is missing "Version": {}'.format(op))

        op['RequestId'] = self._request_id
        self._request_id += 1
        return op

    def check_error(self, result):
        return result.get('Error')

    def get_response(self, result):
        return result['Response']

    def login_args(self, user, password):
        return {
            "Type": "Admin",
            "Request": "Login",
            "Version": 0,
            "Params": {"AuthTag": user,
                       "Password": password}}
