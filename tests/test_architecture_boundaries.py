"""M1 — structural guards for the modular-monolith boundaries.

These are intentionally simple static checks. They protect the decisions that
matter in this release: cross-cutting infrastructure in ``app.core`` must not
reach into feature code, domain rules in ``app.domains`` must not reach for HTTP
request state or route handlers, and the application factory must only wire
components together.
"""

import ast
from pathlib import Path
import re

from app import create_app, db, login_manager, migrate
from app.core.extensions import db as core_db
from app.core.extensions import login_manager as core_login_manager
from app.core.extensions import migrate as core_migrate


ROOT = Path(__file__).resolve().parent.parent


def _module_path(module):
    if module == 'app':
        return ROOT / 'app' / '__init__.py'
    return ROOT / Path(*module.split('.')).with_suffix('.py')


def _imports(module):
    """Yield every imported module name anywhere in ``module``."""
    tree = ast.parse(_module_path(module).read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            yield node.module or ''


def _top_level_imports(module):
    tree = ast.parse(_module_path(module).read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            yield node.module or ''


class TestCoreBoundary:
    CORE_MODULES = (
        'app.core.config',
        'app.core.extensions',
        'app.core.logging',
        'app.core.security',
        'app.core.errors',
        'app.core.responses',
    )
    # Provider integrations, the shared User table, and read-only curriculum
    # lookups for error-page copy are allowed: they back infrastructure hooks,
    # not business-rule decisions. Route/domain services remain forbidden.
    ALLOWED_APP_IMPORTS = {
        'app.version', 'app.core', 'app.models',
        'app.gemini', 'app.rate_limit',
        'app.curriculum', 'app.ml_pathway',
    }
    FORBIDDEN_PREFIXES = (
        'app.routes', 'app.domains', 'app.services',
        'app.pathway_scope', 'app.practice_arena', 'app.leaderboard',
    )

    def test_core_never_imports_route_or_domain_code(self):
        for module in self.CORE_MODULES:
            for imported in _imports(module):
                assert not imported.startswith(self.FORBIDDEN_PREFIXES), (
                    f'{module} imports feature module {imported}'
                )
                if (
                    imported.startswith('app.')
                    and imported not in self.ALLOWED_APP_IMPORTS
                    and not imported.startswith('app.core')
                ):
                    raise AssertionError(
                        f'{module} imports unexpected app module {imported}'
                    )

    def test_extensions_are_shared_singletons(self):
        assert db is core_db
        assert login_manager is core_login_manager
        assert migrate is core_migrate


class TestDomainBoundary:
    DOMAIN_MODULES = ('app.domains.learning.context',)
    FORBIDDEN_PREFIXES = (
        'app.routes', 'app.services', 'flask', 'flask_login',
    )
    FORBIDDEN_IMPORTS = {
        'app.gemini', 'app.openrouter', 'app.services.tutor',
    }

    def test_domains_do_not_import_http_or_provider_code(self):
        for module in self.DOMAIN_MODULES:
            for imported in _imports(module):
                assert not imported.startswith(self.FORBIDDEN_PREFIXES), (
                    f'{module} imports {imported}'
                )
                assert imported not in self.FORBIDDEN_IMPORTS, (
                    f'{module} imports {imported}'
                )

    def test_learning_context_has_no_route_handler_symbols(self):
        source = _module_path('app.domains.learning.context').read_text(
            encoding='utf-8'
        )
        for symbol in ('current_user', 'request.', 'session[', 'Blueprint', 'jsonify'):
            assert symbol not in source


class TestFactoryBoundary:
    def test_factory_module_has_no_top_level_feature_imports(self):
        forbidden = ('app.routes', 'app.domains', 'app.services', 'app.models')
        for imported in _top_level_imports('app'):
            assert not imported.startswith(forbidden), (
                f'app/__init__.py imports {imported} at module scope'
            )

    def test_factory_registers_blueprints_in_one_function(self):
        source = _module_path('app').read_text(encoding='utf-8')
        assert 'def _register_blueprints(app):' in source
        assert 'app.register_blueprint(' in source


class TestTutorResolverOwnership:
    def test_tutor_and_lesson_route_use_the_single_resolver(self):
        for module in ('app.services.tutor', 'app.routes.lessons'):
            source = _module_path(module).read_text(encoding='utf-8')
            assert 'from app.domains.learning.context import' in source or (
                'from app.domains.learning.context import (' in source
            )
            assert 'resolve_learning_context(' in source

    def test_tutor_context_does_not_take_its_domain_from_dashboard_focus(self):
        source = _module_path('app.services.tutor').read_text(encoding='utf-8')
        assert not re.search(
            r"active_domain['\"]\s*:\s*destination_for\(", source
        )
        assert 'dashboard_focus=destination' in source

    def test_app_still_starts_after_the_core_extraction(self):
        app = create_app()
        assert len(app.blueprints) == 21
        assert 'process-ai-jobs' in app.cli.commands
