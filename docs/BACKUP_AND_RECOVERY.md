# Backup and Recovery (M5)

These scripts are intentionally small and dependency-free. They use the same `DATABASE_URL` as the application; production should supply Postgres credentials through the environment, not through argv.

## 1. Backup

```bash
# Inspect the plan without touching data (safe in CI or a release gate)
python -m scripts.backup_database --dry-run

# Real backup with 14-generation retention
python -m scripts.backup_database --output-dir /var/backups/ruach --retain 14
```

Behavior:

- Postgres → `pg_dump --format=custom --no-owner --no-privileges`; password is passed through `PGPASSWORD`, never printed.
- SQLite → online backup API, so a live local database is copied consistently. SQLite URLs must be absolute and file-backed; `:memory:` is refused.
- Files are named `ruach-<UTC timestamp>.dump` or `ruach-<UTC timestamp>.sqlite3`.
- `--retain` prunes older files of the same type after a successful backup.
- Failures exit non-zero; a failed backup blocks the release checklist.

Schedule: take a backup before every manual migration and at least daily while production data is being written. Retention of 14 generations is a starting point; adjust to the organisation's data policy.

## 2. Restore

```bash
# Always inspect first
python -m scripts.restore_database --backup /var/backups/ruach/ruach-....dump --dry-run

# Explicit destructive confirmation
python -m scripts.restore_database --backup /var/backups/ruach/ruach-....dump --confirm
```

Safety rules:

- Empty files are refused.
- Postgres backups must end in `.dump`; SQLite backups in `.sqlite3`.
- `--confirm` is required for any data change; a plain invocation is a dry run.
- SQLite writes to a temporary sibling and then atomically replaces the target.
- Stop the web process before a SQLite restore so no writer holds an open connection.

Do not run `flask db downgrade` as a rollback. Restore the backup instead, then redeploy the matching application commit.

## 3. Restore drill

Perform a drill before the first production release and after any backup script change:

1. Create a throwaway database from the current schema.
2. Insert one recognizable sentinel row.
3. Run `python -m scripts.backup_database` against it.
4. Modify or delete the sentinel row.
5. Run `python -m scripts.restore_database --confirm`.
6. Verify the sentinel row is present and record the command output in `M5_TEST_REPORT.md`.

The automated regression suite performs the same round trip against a temporary SQLite database. That verifies script logic, not an external Postgres host.

## 4. Failure scenarios

| Scenario | Response |
|---|---|
| `pg_dump` missing or not authorized | Install client tooling / grant read permission; re-run backup. Do not deploy. |
| Backup directory unwritable | Fix permissions or point `BACKUP_DIR` at a mounted volume. |
| Restore refuses backup suffix | Use the matching format; do not rename blindly. |
| Restore interrupted | Postgres: re-run `pg_restore`. SQLite: the atomic sibling temp file prevents a partial target; remove any leftover `.restore-*` file. |
| Restored data behind application schema | Restore the matching release commit and run the guarded migration workflow only after a fresh backup. |

## 5. Relationship to migration workflow

`MIGRATION.md` remains authoritative for schema changes. Backups are a prerequisite, not a replacement for the guarded migration workflow. Multiple Alembic heads caused by the pre-existing untracked `1a7665109d7c` migration are recorded debt; resolve them in a separate, explicitly authorized change.
