from ..watch import (
    BaseWatcher,
    BaseTimeoutWatcher,
    BaseWaitForNoMachines,
    BaseWaitForUnits,
)
from .rpc import RPC


class Watcher(BaseWatcher, RPC):
    version = 0

    def start_args(self):
        return {
            'Type': 'Client',
            'Request': 'WatchAll',
            'Params': {}}

    def next_args(self):
        return {
            'Type': 'AllWatcher',
            'Request': 'Next',
            'Id': self.watcher_id}

    def stop_args(self):
        return {
            'Type': 'AllWatcher',
            'Request': 'Stop',
            'Id': self.watcher_id}

    def get_watcher_id(self, result):
        return result['AllWatcherId']

    def get_deltas(self, result):
        return result['Deltas']


class TimeoutWatcher(BaseTimeoutWatcher, Watcher):
    pass


class WaitForNoMachines(BaseWaitForNoMachines):
    """
    Wait for all non state servers to be terminated.
    """

    def get_machine_id(self, data):
        return data['Id']

    def complete(self):
        return list(self.machines.keys()) == ['0']


class WaitForUnits(BaseWaitForUnits):
    """Wait for units of the environment to reach a particular goal state.

    """
    def get_unit_name(self, data):
        return data['Name']

    def get_unit_status(self, data):
        return data['Status']
