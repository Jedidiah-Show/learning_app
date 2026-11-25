"""Cooperative shutdown for standalone worker processes (M7).

Workers must stop cleanly on SIGTERM (the signal used by process managers and
container schedulers) and SIGINT. The helper installs handlers only for the
current process's main thread and exposes an ``Event`` for bounded waits, so
no worker sleeps through a stop request.
"""

import signal
import threading


class WorkerStop:
    """One stop signal shared by a worker's polling loop and heartbeat code."""

    def __init__(self):
        self._event = threading.Event()
        self._installed = False

    @property
    def signaled(self):
        return self._event.is_set()

    def handle(self, signum=None, frame=None):
        """Signal handler: flip the flag without doing unsafe work in-process."""
        self._event.set()

    def install(self):
        """Install SIGTERM/SIGINT handlers; safe to call more than once."""
        if self._installed:
            return self
        signal.signal(signal.SIGTERM, self.handle)
        signal.signal(signal.SIGINT, self.handle)
        self._installed = True
        return self

    def should_stop(self):
        return self._event.is_set()

    def wait(self, seconds):
        """Return True when stop was requested within ``seconds``."""
        return self._event.wait(max(0.0, float(seconds)))
