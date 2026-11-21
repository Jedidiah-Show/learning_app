"""Standalone entry point for the M3 judge worker.

Usage::

    python -m app.workers.judge_worker

The worker must run on a container-capable host with the pinned sandbox image
available locally. The Flask web process never invokes Docker directly.
"""

from app.services.judge_worker import main


if __name__ == '__main__':
    main()
