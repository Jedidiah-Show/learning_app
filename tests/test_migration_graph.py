"""Guards for the reconciled Alembic revision graph."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


ROOT = Path(__file__).resolve().parent.parent


def _script():
    config = Config()
    config.set_main_option('script_location', str(ROOT / 'migrations'))
    return ScriptDirectory.from_config(config)


def test_repository_has_one_migration_head():
    script = _script()
    heads = script.get_heads()
    assert len(heads) == 1, f'multiple migration heads: {heads}'


def test_reconciliation_migration_descends_from_m5_head():
    script = _script()
    revision = script.get_revision('m7n8o9p1q2r3')
    assert revision.down_revision == 'k6l7m8n9o0p1'


def test_revision_ids_are_unique():
    script = _script()
    revisions = list(script.walk_revisions())
    identifiers = [revision.revision for revision in revisions]
    assert len(identifiers) == len(set(identifiers))
    assert 'm7n8o9p1q2r3' in identifiers
    assert 'h1a2b3c4d5e6' in identifiers
    assert 'h4i5j6k7l8m9' in identifiers


def test_conflicting_draft_is_archived_not_discoverable():
    versions = ROOT / 'migrations' / 'versions'
    draft_name = '1a7665109d7c_drop_pathway_destination_column.py'
    assert not (versions / draft_name).exists()

    archive = ROOT / 'migrations' / 'archive' / f'{draft_name}.disabled'
    assert archive.is_file()
    assert "revision = '1a7665109d7c'" in archive.read_text(encoding='utf-8')
