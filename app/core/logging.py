"""Application logging configuration (no request bodies or secrets logged)."""

import logging
import os

from app.version import APP_VERSION

_WORKER_HANDLER_MARKER = '_ruach_worker_handler'
_WORKER_FILTER_MARKER = '_ruach_context_filter'


def _log_level():
    level_name = os.environ.get('LOG_LEVEL', 'INFO').strip().upper()
    level = logging.getLevelName(level_name)
    if not isinstance(level, int):
        level = logging.INFO
    return level


def _json_logging_enabled() -> bool:
    return os.environ.get('LOG_FORMAT', '').strip().lower() == 'json'


def _worker_formatter() -> logging.Formatter:
    if _json_logging_enabled():
        from app.core.observability import JsonFormatter
        return JsonFormatter()
    return logging.Formatter(
        '%(asctime)s %(levelname)s ruach app=%(name)s %(message)s'
    )


def configure_logging(app):
    """Apply a single consistent log format to each application instance.

    Repeated ``create_app`` calls (common in tests) create a fresh logger, so
    the marker is per-logger.  Log levels are configurable through ``LOG_LEVEL``
    and never include credentials or learner content.
    """
    app.logger.setLevel(_log_level())
    if getattr(app.logger, '_ruach_logging_configured', False):
        return
    formatter = _worker_formatter()
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


def configure_worker_logging(level=None, app=None):
    """Configure structured logging for module/worker loggers outside Flask.

    ``level`` may also be a Flask app (``configure_worker_logging(app)``) for
    worker bootstraps that pass their app instance; its ``LOG_LEVEL`` config
    value is then honoured when present.

    ``logging.getLogger(__name__)`` in workers/services is a child of Flask's
    ``app`` logger, which has ``propagate = False`` and its own handler; without
    care those records stop there, and loggers outside that tree have no
    handler at all (INFO vanishes, errors use plaintext ``lastResort``). This
    helper installs exactly one marked root handler and restyles the ``app``
    logger's handlers with the same format policy as the web app (JSON when
    ``LOG_FORMAT=json``), plus a filter that adds current job/correlation
    context. It is idempotent and safe to call from every worker bootstrap.
    """
    if level is not None and not isinstance(level, (str, int)):
        # Support configure_worker_logging(app) from worker bootstraps.
        app, level = level, None
    if level is None and app is not None:
        try:
            level = app.config.get('LOG_LEVEL')
        except (AttributeError, TypeError):
            level = None
    resolved = _log_level() if level is None else level
    if isinstance(resolved, str):
        resolved = logging.getLevelName(resolved.strip().upper())
    if not isinstance(resolved, int):
        resolved = logging.INFO

    from app.core.observability import WorkerContextFilter

    def _apply(handler, formatter):
        handler.setFormatter(formatter)
        if not any(
            getattr(existing, _WORKER_FILTER_MARKER, False)
            for existing in handler.filters
        ):
            context_filter = WorkerContextFilter()
            setattr(context_filter, _WORKER_FILTER_MARKER, True)
            handler.addFilter(context_filter)

    formatter = _worker_formatter()

    # ``logging.getLogger('app.workers.base')`` is a child of Flask's ``app``
    # logger, which has propagate=False and its own handler. Restyle those
    # handlers in place; otherwise worker records stop there and never reach
    # the root handler below.
    app_logger = logging.getLogger('app')
    app_logger.setLevel(resolved)
    for handler in app_logger.handlers:
        handler.setLevel(resolved)
        _apply(handler, formatter)

    root = logging.getLogger()
    root.setLevel(resolved)
    handler = next(
        (candidate for candidate in root.handlers
         if getattr(candidate, _WORKER_HANDLER_MARKER, False)),
        None,
    )
    if handler is None:
        handler = logging.StreamHandler()
        setattr(handler, _WORKER_HANDLER_MARKER, True)
        root.addHandler(handler)
    handler.setLevel(resolved)
    _apply(handler, formatter)
    return handler


__all__ = ['configure_logging', 'configure_worker_logging']
