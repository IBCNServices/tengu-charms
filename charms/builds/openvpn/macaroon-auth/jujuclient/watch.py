from contextlib import contextmanager
import signal
import socket
import time

from .rpc import BaseRPC
from .exc import (
    EnvError,
    UnitErrors,
    TimeoutError,
)


class TimeoutWatchInProgress(Exception):
    pass


class BaseWatcher(BaseRPC):

    _auth = True
    version = 0

    def __init__(self, conn, auto_reconnect=True):
        self.conn = conn
        self.watcher_id = None
        self.running = False
        self.auto_reconnect = auto_reconnect
        # For debugging, attach the wrapper
        self.context = None

    def start_args(self):
        raise NotImplementedError()

    def next_args(self):
        raise NotImplementedError()

    def stop_args(self):
        raise NotImplementedError()

    def get_watcher_id(self, result):
        raise NotImplementedError()

    def get_deltas(self, result):
        raise NotImplementedError()

    def start(self):
        result = self._rpc(self.start_args())
        self.watcher_id = self.get_watcher_id(result)
        self.running = True
        return result

    def next(self):
        if self.watcher_id is None:
            self.start()
        if not self.running:
            raise StopIteration("Stopped")
        try:
            result = self._rpc(self.next_args())
        except EnvError as e:
            if "state watcher was stopped" in e.message:
                if not self.auto_reconnect:
                    raise
                if not self.reconnect():
                    raise
                return next(self)
            raise
        return self.get_deltas(result)

    # py3 compat
    __next__ = next

    def reconnect(self):
        self.watcher_id = None
        self.running = False
        return super(BaseWatcher, self).reconnect()

    def stop(self):
        if not self.conn.connected:
            return
        try:
            result = self._rpc(self.stop_args())
        except (EnvError, socket.error):
            # We're about to close the connection.
            result = None
        self.conn.close()
        self.watcher_id = None
        self.running = False
        return result

    def set_context(self, context):
        self.context = context
        return self

    def __iter__(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc, v, t):
        self.stop()


class BaseTimeoutWatcher(object):
    # A simple non concurrent watch using signals..

    def __init__(self, *args, **kw):
        super(BaseTimeoutWatcher, self).__init__(*args, **kw)
        self.start_time = time.time()
        self._timeout = 0

    def time_remaining(self):
        """Return number of seconds until this watch times out.

        """
        return int(self._timeout - (time.time() - self.start_time))

    def set_timeout(self, timeout):
        self.start_time = time.time()
        self._timeout = timeout

    def next(self):
        with self._set_alarm(self.time_remaining()):
            return super(BaseTimeoutWatcher, self).next()

    # py3 compat
    __next__ = next

    @classmethod
    @contextmanager
    def _set_alarm(cls, timeout):
        if timeout < 0:
            raise TimeoutError()

        try:
            handler = signal.getsignal(signal.SIGALRM)
            if callable(handler):
                if handler.__name__ == '_set_alarm':
                    raise TimeoutWatchInProgress()
                raise RuntimeError(
                    "Existing signal handler found %r" % handler)
            signal.signal(signal.SIGALRM, cls._on_alarm)
            signal.alarm(timeout)
            yield None
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, signal.SIG_DFL)

    @classmethod
    def _on_alarm(cls, x, frame):
        raise TimeoutError()


class WatchWrapper(object):

    def __init__(self, watch):
        self.watch = watch

    def run(self, callback=None):
        seen_initial = False
        with self.watch.set_context(self):
            for change_set in self.watch:
                for change in change_set:
                    self.process(*change)
                    if seen_initial and callable(callback):
                        callback(*change)
                if self.complete() is True:
                    self.watch.stop()
                    break
                seen_initial = True

    def process(self):
        """process watch events."""

    def complete(self):
        """watch wrapper complete """


class BaseWaitForUnits(WatchWrapper):
    """
    Wait for units of the environment to reach a particular goal state.
    """
    def __init__(self, watch, state='started', service=None):
        super(BaseWaitForUnits, self).__init__(watch)
        self.units = {}
        self.goal_state = state
        self.service = service

    def get_unit_name(self, data):
        raise NotImplementedError()

    def get_unit_status(self, data):
        raise NotImplementedError()

    def process(self, entity_type, change, data):
        if entity_type != "unit":
            return

        unit_name = self.get_unit_name(data)
        if change == "remove" and unit_name in self.units:
            del self.units[unit_name]
        else:
            self.units[unit_name] = data

    def complete(self):
        state = {'pending': [], 'errors': []}

        for k, v in list(self.units.items()):
            status = self.get_unit_status(v)
            if status == "error":
                state['errors'] = [v]
            elif status != self.goal_state:
                state['pending'] = [v]

        if not state['pending'] and not state['errors']:
            return True

        if state['errors'] and not self.goal_state == "removed":
            raise UnitErrors(state['errors'])

        return state['pending']


class BaseWaitForNoMachines(WatchWrapper):
    """
    Wait for all non state servers to be terminated.
    """

    def __init__(self, watch, initial_machines=None):
        super(BaseWaitForNoMachines, self).__init__(watch)
        self.machines = initial_machines or {}

    def get_machine_id(self, data):
        raise NotImplementedError()

    def complete(self):
        raise NotImplementedError()

    def process(self, entity_type, change, data):
        if entity_type != 'machine':
            return

        machine_id = self.get_machine_id(data)
        if change == 'remove' and machine_id in self.machines:
            del self.machines[machine_id]
        else:
            self.machines[machine_id] = data
