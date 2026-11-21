"""Application logging configuration (no request bodies or secrets logged)."""

import logging
import os

from app.version import APP_VERSION


def configure_logging(app):
    """Apply a single consistent log format to each application instance.

    Repeated ``create_app`` calls (common in tests) create a fresh logger, so
    the marker is per-logger.  Log levels are configurable through ``LOG_LEVEL``
    and never include credentials or learner content.
    """
    level_name = os.environ.get('LOG_LEVEL', 'INFO').strip().upper()
    level = logging.getLevelName(level_name)
    if not isinstance(level, int):
        level = logging.INFO
    app.logger.setLevel(level)
    if getattr(app.logger, '_ruach_logging_configured', False):
        return
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s ruach app=%(name)s %(message)s'
    )
    if app.logger.handlers:
        # Flask installs a default handler; restyle it rather than emitting
        # every message twice.
        for handler in app.logger.handlers:
            handler.setFormatter(formatter)
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        app.logger.addHandler(handler)
    app.logger.propagate = False
    app.logger._ruach_logging_configured = True
    app.logger.debug('Logging configured for RUACH %s', APP_VERSION)
