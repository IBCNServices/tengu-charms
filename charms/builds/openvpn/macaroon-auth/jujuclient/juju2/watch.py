from ..watch import (
    BaseWatcher,
    BaseTimeoutWatcher,
    BaseWaitForNoMachines,
    BaseWaitForUnits,
)
from .rpc import RPC


class Watcher(BaseWatcher, RPC):
    version = 1

    def start_args(self):
        return {
            'type': 'Client',
            'request': 'WatchAll',
            'params': {}}

    def next_args(self):
        return {
            'type': 'AllWatcher',
            'request': 'Next',
            'id': self.watcher_id}

    def stop_args(self):
        return {
            'type': 'AllWatcher',
            'request': 'Stop',
            'id': self.watcher_id}

    def get_watcher_id(self, result):
        return result['watcher-id']

    def get_deltas(self, result):
        return result['deltas']


class TimeoutWatcher(BaseTimeoutWatcher, Watcher):
    pass


class WaitForNoMachines(BaseWaitForNoMachines):
    """
    Wait for all non state servers to be terminated.
    """

    def get_machine_id(self, data):
        return data['id']

    def complete(self):
        return not self.machines


class WaitForUnits(BaseWaitForUnits):
    """Wait for units of the environment to reach a particular goal state.

    """
    def get_unit_name(self, data):
        return data['name']

    def get_unit_status(self, data):
        return data['status']
