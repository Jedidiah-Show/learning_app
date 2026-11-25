"""Restore a database backup with an explicit destructive-action gate (M5).

Postgres uses ``pg_restore``; SQLite replaces the target file atomically after
copying the verified backup to a temporary sibling. Both modes require
``--confirm`` for an actual restore and refuse to run without a non-empty
backup file.

Usage::

    python -m scripts.restore_database --backup backups/ruach-....dump --dry-run
    python -m scripts.restore_database --backup backups/ruach-....dump --confirm
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import uuid

from scripts.backup_database import build_pg_command, parse_target


def restore_plan(*, backup_path: Path, database_url: str) -> dict:
    """Validate inputs and return the redacted restore plan."""
    backup = Path(backup_path).expanduser().resolve()
    if not backup.is_file():
        raise FileNotFoundError(f'Backup not found: {backup}')
    if backup.stat().st_size == 0:
        raise ValueError('Backup file is empty')
    target = parse_target(database_url)
    expected_suffix = '.dump' if target.kind == 'postgres' else '.sqlite3'
    if backup.suffix != expected_suffix:
        raise ValueError(f'{target.kind} restore expects a {expected_suffix} backup')
    if target.kind == 'postgres':
        command, extra_env, display = build_pg_command(database_url, backup)
        command[0] = 'pg_restore'
        command.remove('--format=custom')
        command.remove('--file')
        command.remove(str(backup))
        flags = [
            '--clean', '--if-exists', '--no-owner', '--no-privileges',
            '--single-transaction', '--exit-on-error',
        ]
        command += flags + [str(backup)]
        display = display.replace('pg_dump', 'pg_restore', 1)
        display = display.replace('--format=custom ', '')
        display = display.replace(f'--file {backup} ', '')
        display += ' ' + ' '.join(flags)
        return {
            'target': target.display,
            'backup': str(backup),
            'command': display,
            'argv': command,
            'env': extra_env,
            'kind': 'postgres',
        }
    if target.path is None or backup == target.path.resolve():
        raise ValueError('Backup and SQLite target must be different files')
    return {
        'target': target.display,
        'backup': str(backup),
        'command': f'replace {target.path} with {backup}',
        'kind': 'sqlite',
        'target_path': target.path,
    }


def execute_restore(plan: dict) -> dict:
    """Apply a validated plan. Callers must already have checked --confirm."""
    result = {
        'target': plan['target'],
        'backup': plan['backup'],
        'kind': plan['kind'],
        'restored': True,
    }
    if plan['kind'] == 'postgres':
        env = dict(os.environ)
        env.update(plan['env'])
        subprocess.run(plan['argv'], check=True, env=env)
        result['command'] = plan['command']
        return result
    target = Path(plan['target_path'])
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f'.{target.name}.restore-{uuid.uuid4().hex[:8]}')
    try:
        shutil.copyfile(plan['backup'], temporary)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    result['command'] = plan['command']
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backup', required=True, help='Path to the backup file.')
    parser.add_argument(
        '--database-url', default=os.environ.get('DATABASE_URL'),
        help='Defaults to DATABASE_URL.',
    )
    parser.add_argument(
        '--confirm', action='store_true',
        help='Required to replace data; without it the command is a dry run.',
    )
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    try:
        plan = restore_plan(
            backup_path=Path(args.backup), database_url=args.database_url
        )
    except (ValueError, FileNotFoundError) as error:
        parser.exit(1, f'Restore refused: {error}\n')

    if args.dry_run or not args.confirm:
        print(f"Restore plan: {plan['command']}")
        print('No data was changed. Re-run with --confirm to restore.')
        return 0
    try:
        result = execute_restore(plan)
    except (OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Restore failed: {error}\n')
    print(f"Restored {result['target']} from {result['backup']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
