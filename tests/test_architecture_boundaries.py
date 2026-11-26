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
        'app.core.observability',
        'app.core.security',
        'app.core.errors',
        'app.core.responses',
        'app.core.exceptions',
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
    DOMAIN_MODULES = (
        'app.domains.identity.service',
        'app.domains.learning.service',
        'app.domains.learning.context',
        'app.domains.ai_engineering.service',
        'app.domains.ai_engineering.evaluation',
        'app.domains.machine_learning.service',
        'app.domains.machine_learning.competencies',
        'app.domains.machine_learning.evaluation',
        'app.domains.machine_learning.report',
        'app.domains.assessment.service',
        'app.domains.workspace.service',
    )
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

    def test_ai_domain_never_imports_ml_domain(self):
        ai_modules = (
            'app.domains.ai_engineering.service',
            'app.domains.ai_engineering.evaluation',
        )
        prohibited = ('app.domains.machine_learning', 'app.ml_pathway')
        for module in ai_modules:
            for imported in _imports(module):
                assert not imported.startswith(prohibited), (
                    f'{module} imports prohibited ML module {imported}'
                )

    def test_ml_domain_never_imports_ai_domain(self):
        ml_modules = (
            'app.domains.machine_learning.service',
            'app.domains.machine_learning.competencies',
            'app.domains.machine_learning.evaluation',
            'app.domains.machine_learning.report',
        )
        prohibited = ('app.domains.ai_engineering', 'app.ai_pathway')
        for module in ml_modules:
            for imported in _imports(module):
                assert not imported.startswith(prohibited), (
                    f'{module} imports prohibited AI module {imported}'
                )

    def test_core_exceptions_is_decoupled(self):
        for imported in _imports('app.core.exceptions'):
            assert not imported.startswith(('flask', 'werkzeug', 'app.routes', 'app.services')), (
                f'app.core.exceptions imports framework module {imported}'
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
        # Includes the Shared Foundations read API blueprint.
        assert len(app.blueprints) == 24
        assert 'process-ai-jobs' in app.cli.commands
        assert 'process-submissions' in app.cli.commands
        assert 'judge-worker-health' in app.cli.commands
        assert 'run-scheduled-jobs' in app.cli.commands


class TestRouteBoundaryGuardrails:
    """Prevent route hotspots from regrowing domain logic unchecked."""

    # Large route modules are allowed only while decomposition is in progress.
    # Reduce this allowlist as logic moves into app/services or app/domains.
    LARGE_ROUTE_ALLOWLIST = {
        'app/routes/main.py': 1600,
        'app/routes/projects.py': 1500,
        'app/routes/admin_portal.py': 1400,
        'app/routes/auth.py': 1300,
        'app/routes/lessons.py': 1300,
        'app/routes/calendar.py': 1200,
        'app/routes/practice_arena.py': 1100,
        'app/routes/ml_specialization.py': 900,
    }

    def test_large_routes_have_explicit_size_budgets(self):
        routes_dir = ROOT / 'app' / 'routes'
        for path in sorted(routes_dir.glob('*.py')):
            if path.name.startswith('_'):
                continue
            rel = f'app/routes/{path.name}'
            line_count = len(path.read_text(encoding='utf-8').splitlines())
            if rel in self.LARGE_ROUTE_ALLOWLIST:
                assert line_count <= self.LARGE_ROUTE_ALLOWLIST[rel], (
                    f'{rel} grew to {line_count} lines; decompose before raising its budget'
                )
            else:
                assert line_count <= 700, (
                    f'{rel} is {line_count} lines; extract domain logic into services'
                )

    def test_project_completion_gate_lives_in_service(self):
        route_source = _module_path('app.routes.projects').read_text(encoding='utf-8')
        service_source = _module_path('app.services.project_completion').read_text(
            encoding='utf-8'
        )
        assert 'def _project_passes_completion_gate(' not in route_source
        assert 'project_passes_completion_gate' in service_source
        assert 'from app.services.project_completion import' in route_source
