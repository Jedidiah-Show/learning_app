"""Registry of executable AI job handlers (M2.5)."""

from typing import Callable, Dict

Handler = Callable[..., dict]

_HANDLERS: Dict[str, Handler] = {}


def register_handler(job_type: str, handler: Handler = None):
    """Register a handler directly or as a decorator."""
    if not isinstance(job_type, str) or not job_type.strip():
        raise ValueError('job_type must be a non-empty string')

    def decorator(view):
        _HANDLERS[job_type] = view
        return view

    if handler is None:
        return decorator
    return decorator(handler)


def handler_for(job_type: str):
    try:
        return _HANDLERS[job_type]
    except KeyError as error:
        raise ValueError(f'No handler registered for job type {job_type!r}') from error


def registered_types():
    """Return handler names, loading built-ins on first use."""
    if not _HANDLERS:
        load_default_handlers()
    return tuple(sorted(_HANDLERS))


def load_default_handlers() -> None:
    """Import handler modules so their decorators run once."""
    from app.workers import handlers  # noqa: F401
