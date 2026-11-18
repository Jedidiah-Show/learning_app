#!/usr/bin/env bash
# Release source export for RUACH LMS.
#
# Exports *committed* source (git archive of HEAD) into a tarball that is safe
# to distribute. The script:
#
#   1. Verifies the repository is in an approved state (clean worktree, or
#      --allow-dirty with an explicit acknowledgement).
#   2. Exports committed content only — never arbitrary working-directory
#      files such as .env, uploads or local databases.
#   3. Scans the exported tree for prohibited file patterns and fails closed.
#   4. Writes an archive manifest (file list + sizes).
#   5. Emits a SHA-256 checksum of the archive.
#
# Usage:
#   scripts/export_release_source.sh <output-dir> [--allow-dirty]
#
# Outputs (inside <output-dir>):
#   ruach-source-<version>-<shortsha>.tar.gz
#   ruach-source-<version>-<shortsha>.tar.gz.sha256
#   MANIFEST.txt
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

OUTDIR="${1:-}"
ALLOW_DIRTY=0
for arg in "$@"; do
  case "$arg" in
    --allow-dirty) ALLOW_DIRTY=1 ;;
  esac
done

if [[ -z "$OUTDIR" || "$OUTDIR" == --* ]]; then
  echo "usage: scripts/export_release_source.sh <output-dir> [--allow-dirty]" >&2
  exit 2
fi
OUTDIR="$(realpath -m -- "$OUTDIR")"
case "$OUTDIR" in
  /|"$REPO_ROOT"|"$REPO_ROOT"/*)
    echo "error: output must be outside the repository" >&2
    exit 2
    ;;
esac

# --- 1. Approved repository state -----------------------------------------
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "error: not a git repository" >&2
  exit 1
fi
if [[ -n "$(git status --porcelain)" && "$ALLOW_DIRTY" -ne 1 ]]; then
  echo "error: working tree has uncommitted changes." >&2
  echo "       Commit them, or re-run with --allow-dirty to export HEAD anyway." >&2
  exit 1
fi

VERSION="$(git describe --tags --always --dirty 2>/dev/null || git rev-parse --short HEAD)"
COMMIT="$(git rev-parse HEAD)"
SHORT_SHA="$(git rev-parse --short HEAD)"
APP_VERSION="$(grep -E "^APP_VERSION" app/version.py 2>/dev/null | head -1 | sed -E 's/.*= *"([^"]+)".*/\1/' || true)"
APP_VERSION="${APP_VERSION:-1.1.0}"
NAME="ruach-source-${APP_VERSION}-${SHORT_SHA}"

mkdir -p -- "$OUTDIR"
STAGING="$(mktemp -d "${TMPDIR:-/tmp}/ruach-export.XXXXXX")"
trap 'rm -rf -- "$STAGING"' EXIT

# --- 2. Export committed source only ---------------------------------------
git archive --format=tar --prefix="${NAME}/" HEAD | tar -x -C "$STAGING"
SRC="$STAGING/$NAME"

# --- 3. Prohibited-pattern scan (fail closed) ------------------------------
# Patterns matched against paths relative to the export root.
PROHIBITED_REGEX='(^|/)(\.env($|\.)|\.env\.local$|client_secret[^/]*\.json$|credentials?[^/]*\.json$|service-account[^/]*\.json$|token\.json$|id_rsa[^/]*$|id_ed25519[^/]*$|[^/]*\.(pem|key|p12|pfx|keystore|jks|asc)$|[^/]*\.(db|db-journal|db-wal|db-shm|sqlite|sqlite3|dump|sql\.gz)$|node_modules/|\.venv/|venv/|\.qoder/|__pycache__/|\.pytest_cache/|test-results/|playwright-report/|instance/|uploads?/|\.vercel/|backup[^/]*\.dump$)'

mapfile -t OFFENDERS < <(cd "$SRC" && find . -mindepth 1 -print | sed 's|^\./||' | grep -E "$PROHIBITED_REGEX" | grep -vE '^\.env\.example$' || true)
if [[ "${#OFFENDERS[@]}" -gt 0 ]]; then
  echo "error: export contains prohibited files:" >&2
  printf '  - %s\n' "${OFFENDERS[@]}" >&2
  exit 1
fi

# Content scan: look for high-confidence secret literals in text files.
# Placeholders (GENERATE/SET_IN_RENDER/<...>/example) are allowed.
CONTENT_HITS="$(cd "$SRC" && grep -RInE \
  -e '-----BEGIN (RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----' \
  -e 'AIza[0-9A-Za-z_-]{20,}' \
  -e 'sk-[A-Za-z0-9]{20,}' \
  -e 'ghp_[A-Za-z0-9]{20,}' \
  -e 'xox[baprs]-[A-Za-z0-9-]{10,}' \
  --exclude-dir=.git . || true)"
if [[ -n "$CONTENT_HITS" ]]; then
  echo "error: export contains high-confidence secret material:" >&2
  echo "$CONTENT_HITS" >&2
  exit 1
fi

# --- 4. Archive + manifest -------------------------------------------------
ARCHIVE="$OUTDIR/$NAME.tar.gz"
tar -czf "$ARCHIVE" -C "$STAGING" "$NAME"

( cd "$SRC" && find . -type f -printf '%s\t%p\n' | sed 's|\./||' | LC_ALL=C sort -k2 ) > "$OUTDIR/MANIFEST.txt"
{
  echo "# RUACH LMS source export manifest"
  echo "version: $APP_VERSION"
  echo "git_commit: $COMMIT"
  echo "git_ref: $VERSION"
  echo "exported_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "file_count: $(wc -l < "$OUTDIR/MANIFEST.txt")"
  echo "bytes_uncompressed: $(cd "$SRC" && find . -type f -printf '%s\n' | awk '{s+=$1} END {print s+0}')"
  echo "archive_bytes: $(stat -c%s "$ARCHIVE")"
} >> "$OUTDIR/MANIFEST.txt"

# --- 5. Checksum ------------------------------------------------------------
( cd "$OUTDIR" && sha256sum "$(basename "$ARCHIVE")" > "$(basename "$ARCHIVE").sha256" )

echo "Export complete:"
echo "  archive:  $ARCHIVE"
echo "  checksum: $ARCHIVE.sha256"
echo "  manifest: $OUTDIR/MANIFEST.txt"
echo "  commit:   $COMMIT"
