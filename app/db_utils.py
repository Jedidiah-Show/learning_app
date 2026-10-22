"""Small database helpers shared by generated-content caches."""

from sqlalchemy.exc import IntegrityError

from app import db


def add_or_get(model, instance, **identity):
    """Insert a unique cache row, returning the row another request may have won."""
    try:
        with db.session.begin_nested():
            db.session.add(instance)
            db.session.flush()
        return instance
    except IntegrityError:
        existing = model.query.filter_by(**identity).first()
        if existing is None:
            raise
        return existing
