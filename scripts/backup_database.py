"""Create a timestamped database backup (M5).

Postgres uses ``pg_dump`` custom format; SQLite uses the online backup API so
a live local database is copied consistently. Passwords are supplied through
``PGPASSWORD`` and never appear in argv or printed output.

Usage::

    python -m scripts.backup_database --dry-run
    python -m scripts.backup_database --output-dir /var/backups/ruach --retain 14
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import subprocess
from urllib.parse import parse_qsl, unquote, urlsplit


BACKUP_PREFIX = 'ruach-'

# libpq settings that may safely be forwarded from a DATABASE_URL query string
# (e.g. ``?sslmode=require``). Credentials and endpoints always come from the
# parsed URL itself; unknown keys are ignored rather than smuggled into argv.
PG_OPTION_KEYS = frozenset({
    'sslmode', 'sslrootcert', 'sslcert', 'sslkey', 'sslcrl', 'sslcrldir',
    'ssl_min_protocol_version', 'ssl_max_protocol_version', 'sslnegotiation',
    'channel_binding', 'connect_timeout', 'application_name', 'gssencmode',
    'gsslib', 'krbsrvname', 'target_session_attrs', 'service', 'options',
    'client_encoding', 'timezone',
})


def pg_option_env(options: dict) -> dict:
    """Translate libpq URL options into PG* environment variables."""
    env = {}
    for key, value in (options or {}).items():
        name = str(key).strip().lower().replace('-', '_')
        if name not in PG_OPTION_KEYS or not isinstance(value, str) or not value:
            continue
        if any(char in value for char in ('\x00', '\n', '\r')):
            continue
        env['PG' + name.upper()] = value
    return env


@dataclass(frozen=True)
class DatabaseTarget:
    kind: str
    host: str | None
    port: int | None
    username: str | None
    password: str | None
    database: str | None
    path: Path | None
    options: dict

    @property
    def display(self) -> str:
        if self.kind == 'sqlite':
            return f'sqlite:{self.path}'
        return (
            f'postgres:{self.username or "?"}@'
            f'{self.host or "local"}:{self.port or 5432}/{self.database or "?"}'
        )


def parse_target(url: str) -> DatabaseTarget:
    """Parse the supported DATABASE_URL forms without logging credentials."""
    if not url or not isinstance(url, str):
        raise ValueError('A database URL is required')
    split = urlsplit(url)
    scheme = split.scheme.lower()
    options = dict(parse_qsl(split.query))
    if scheme.startswith('postgres'):
        database = unquote(split.path).lstrip('/') or None
        if not database:
            raise ValueError('Postgres URL must include a database name')
        try:
            port = int(split.port) if split.port else None
        except ValueError as error:
            raise ValueError('Postgres URL has an invalid port') from error
        return DatabaseTarget(
            kind='postgres',
            host=unquote(split.hostname) if split.hostname else None,
            port=port,
            username=unquote(split.username) if split.username else None,
            password=unquote(split.password) if split.password else None,
            database=database,
            path=None,
            options=options,
        )
    if scheme == 'sqlite' or scheme.startswith('sqlite+'):
        raw = unquote(split.path)
        if not raw or raw.lstrip('/') == ':memory:':
            raise ValueError('SQLite backups require a file-backed database')
        path = Path(raw)
        if not path.is_absolute():
            # Flask-SQLAlchemy resolves sqlite:///relative.db against the
            # instance folder; operators should pass an absolute URL for
            # backups. Refuse ambiguity rather than copying the wrong file.
            raise ValueError('SQLite backup URL must use an absolute path')
        return DatabaseTarget(
            kind='sqlite', host=None, port=None, username=None, password=None,
            database=None, path=path, options=options,
        )
    raise ValueError(f'Unsupported database scheme {scheme!r}')


def build_pg_command(url: str, output_path: Path) -> tuple[list[str], dict, str]:
    """Return argv, PGPASSWORD environment fragment and redacted display."""
    target = parse_target(url)
    command = [
        'pg_dump', '--format=custom', '--no-owner', '--no-privileges',
        '--file', str(output_path),
    ]
    if target.host:
        command += ['--host', target.host]
    if target.port:
        command += ['--port', str(target.port)]
    if target.username:
        command += ['--username', target.username]
    command += ['--dbname', target.database]
    env = {'PGPASSWORD': target.password} if target.password else {}
    env.update(pg_option_env(target.options))
    return command, env, ' '.join(command)


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _backup_path(output_dir: Path, kind: str) -> Path:
    suffix = 'dump' if kind == 'postgres' else 'sqlite3'
    return output_dir / f'{BACKUP_PREFIX}{_timestamp()}.{suffix}'


def _apply_retention(output_dir: Path, suffix: str, retain: int | None) -> list[str]:
    if not retain or retain <= 0:
        return []
    candidates = sorted(
        (
            path for path in output_dir.glob(f'{BACKUP_PREFIX}*.{suffix}')
            if path.is_file()
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    removed = []
    for path in candidates[retain:]:
        path.unlink()
        removed.append(path.name)
    return removed


def create_backup(
    *,
    database_url: str,
    output_dir: Path,
    retain: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Create one backup and optionally prune older ones."""
    target = parse_target(database_url)
    output_dir = Path(output_dir)
    destination = _backup_path(output_dir, target.kind)
    plan = {
        'target': target.display,
        'destination': str(destination),
        'dry_run': dry_run,
    }
    if target.kind == 'postgres':
        # Names only: never print option values, which may be paths/secrets.
        plan['connection_options'] = sorted(pg_option_env(target.options))
    if dry_run:
        if target.kind == 'postgres':
            plan['command'] = build_pg_command(database_url, destination)[2]
        plan['retain'] = retain
        return plan

    output_dir.mkdir(parents=True, exist_ok=True)
    if target.kind == 'postgres':
        command, extra_env, display = build_pg_command(database_url, destination)
        env = dict(os.environ)
        env.update(extra_env)
        subprocess.run(command, check=True, env=env)
        plan['command'] = display
    else:
        source = target.path
        if not source.exists():
            raise FileNotFoundError(f'SQLite database not found: {source}')
        with sqlite3.connect(f'{source.resolve().as_uri()}?mode=ro', uri=True) as origin:
            with sqlite3.connect(destination) as copy:
                origin.backup(copy)

    plan['size_bytes'] = destination.stat().st_size
    plan['removed'] = _apply_retention(
        output_dir,
        'dump' if target.kind == 'postgres' else 'sqlite3',
        retain,
    )
    return plan


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--database-url', default=os.environ.get('DATABASE_URL'),
        help='Defaults to DATABASE_URL.',
    )
    parser.add_argument(
        '--output-dir', default=os.environ.get('BACKUP_DIR', 'backups'),
        help='Defaults to BACKUP_DIR or ./backups.',
    )
    parser.add_argument('--retain', type=int, default=None)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    try:
        plan = create_backup(
            database_url=args.database_url,
            output_dir=Path(args.output_dir),
            retain=args.retain,
            dry_run=args.dry_run,
        )
    except (ValueError, FileNotFoundError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Backup failed: {error}\n')
    print(f"Backup {plan['destination']} ({plan['target']})")
    if 'command' in plan:
        print(f"Command: {plan['command']}")
    if 'size_bytes' in plan:
        print(f"Size: {plan['size_bytes']} bytes")
    if plan.get('removed'):
        print(f"Pruned: {', '.join(plan['removed'])}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
