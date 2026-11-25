"""Minimal shared pytest support.

Pytest markers are registered in ``pytest.ini`` (no duplicate registration here).
The only helper below is an opt-in context manager for tests that want a
throwaway SQLite database. Most existing tests already juggle ``DATABASE_URL``
in their own ``setUp``/``tearDown``; this fixture deliberately changes nothing
unless a test asks for it, so it cannot collide with that pattern.
"""

from contextlib import contextmanager
import os
import tempfile

import pytest


@pytest.fixture
def throwaway_database_url():
    """Yield a factory pointing ``DATABASE_URL`` at a temporary SQLite file.

    Usage::

        def test_something(throwaway_database_url):
            with throwaway_database_url() as url:
                ...

    The previous value (including "unset") is restored on exit.
    """

    @contextmanager
    def _database_url(name='test.db'):
        temp_dir = tempfile.TemporaryDirectory(prefix='ruach-pytest-')
        previous = os.environ.get('DATABASE_URL')
        from pathlib import Path

        os.environ['DATABASE_URL'] = f"sqlite:///{Path(temp_dir.name) / name}"
        try:
            yield os.environ['DATABASE_URL']
        finally:
            if previous is None:
                os.environ.pop('DATABASE_URL', None)
            else:
                os.environ['DATABASE_URL'] = previous
            temp_dir.cleanup()

    return _database_url
