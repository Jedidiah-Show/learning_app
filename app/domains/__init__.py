"""Domain modules for the RUACH modular monolith.

Domains own business rules. They may use ``app.core`` and ``app.infrastructure``
interfaces, but must not import route handlers. Specialisation internals
(``ai_engineering`` / ``machine_learning``) are intentionally kept independent;
only genuinely shared curriculum and learning-context code is shared.
"""
