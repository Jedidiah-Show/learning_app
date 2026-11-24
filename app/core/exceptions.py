"""Consistent domain exception hierarchy for RUACH LMS.

These exceptions represent domain and business-logic failures, completely
decoupled from HTTP/Flask request state. They are translated into appropriate
HTTP status codes and responses by :mod:`app.core.errors`.
"""


class RuachDomainError(Exception):
    """Base exception for all domain and business-rule errors."""
    def __init__(self, message, code=None):
        super().__init__(message)
        self.message = message
        self.code = code or 'domain_error'


class EntityNotFoundError(RuachDomainError):
    """Raised when an entity or resource cannot be found."""
    def __init__(self, entity_name, entity_id=None, message=None):
        self.entity_name = entity_name
        self.entity_id = entity_id
        msg = message or f"{entity_name} with id '{entity_id}' not found."
        super().__init__(msg, code='not_found')


class AuthorizationError(RuachDomainError):
    """Raised when an operation violates access or role policies."""
    def __init__(self, message="You do not have permission to perform this action."):
        super().__init__(message, code='forbidden')


class ValidationError(RuachDomainError):
    """Raised when input fails domain validation or invariant checks."""
    def __init__(self, message, field=None):
        self.field = field
        super().__init__(message, code='validation_error')


class ConflictError(RuachDomainError):
    """Raised when an operation conflicts with existing state (e.g. duplicate or invalid lifecycle transition)."""
    def __init__(self, message):
        super().__init__(message, code='conflict')


class WorkloadExecutionError(RuachDomainError):
    """Raised when a sandboxed or background execution workload fails or exceeds resource limits."""
    def __init__(self, message, profile=None):
        self.profile = profile
        super().__init__(message, code='execution_error')
