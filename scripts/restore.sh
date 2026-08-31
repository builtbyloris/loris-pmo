#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

usage() {
  printf 'Usage: %s [--yes] DATABASE_DUMP [DOCUMENT_ARCHIVE]\n' "$0"
  printf 'Restores the local Compose database and optionally its matching document archive.\n'
}

fail() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

yes=false
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  usage
  exit 0
fi
if [ "${1:-}" = "--yes" ]; then
  yes=true
  shift
fi
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || { usage >&2; exit 2; }

db_backup=$1
doc_backup=${2:-}
[ -f "$db_backup" ] || fail "Database backup does not exist: $db_backup"
if [ -n "$doc_backup" ]; then
  [ -f "$doc_backup" ] || fail "Document archive does not exist: $doc_backup"
  tar -tzf "$doc_backup" >/dev/null || fail "Document archive is not a readable gzip tar file."
  tar -tzf "$doc_backup" | grep -Eq '^documents(/|$)' || fail "Document archive does not contain the expected documents/ root."
  if ! tar -tzf "$doc_backup" | awk '
    BEGIN { safe = 1 }
    /^\// { safe = 0 }
    /(^|\/)\.\.($|\/)/ { safe = 0 }
    END { exit safe ? 0 : 1 }
  '; then
    fail "Document archive contains an unsafe absolute or parent path."
  fi
  if ! tar -tvzf "$doc_backup" | awk '
    BEGIN { safe = 1 }
    { kind = substr($1, 1, 1); if (kind != "-" && kind != "d") safe = 0 }
    END { exit safe ? 0 : 1 }
  '; then
    fail "Document archive contains an unsupported link or special-file entry."
  fi
fi

command -v docker >/dev/null 2>&1 || fail "Docker is not installed or not on PATH."
docker info >/dev/null 2>&1 || fail "Docker is unavailable. Start Docker Desktop/Engine and try again."
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is unavailable."
[ -f .env ] || fail "Missing .env."

docker compose up -d db >/dev/null
attempt=0
until docker compose exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  [ "$attempt" -lt 30 ] || fail "PostgreSQL did not become ready."
  sleep 2
done
docker compose exec -T db pg_restore --list <"$db_backup" >/dev/null || fail "Database backup is not a valid PostgreSQL custom-format dump."

target=$(docker compose exec -T db sh -c 'printf "%s/%s" "$POSTGRES_USER" "$POSTGRES_DB"')
printf 'This will replace the current local PostgreSQL schema at %s' "$target"
if [ -n "$doc_backup" ]; then
  printf ' and replace the document volume'
fi
printf '.\nPre-restore safety backups will be written under backups/.\n'

if [ "$yes" != true ]; then
  if [ ! -t 0 ]; then
    fail "Interactive confirmation is required. Re-run in a terminal or pass --yes deliberately."
  fi
  read -r -p 'Type RESTORE to continue: ' confirmation
  [ "$confirmation" = "RESTORE" ] || fail "Restore cancelled."
fi

mkdir -p backups
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
safety_db="backups/pre-restore-${timestamp}.dump"
safety_docs="backups/pre-restore-documents-${timestamp}.tar.gz"

printf 'Creating pre-restore PostgreSQL safety backup...\n'
docker compose exec -T db sh -c \
  'exec pg_dump --format=custom --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  >"$safety_db"
docker compose exec -T db pg_restore --list <"$safety_db" >/dev/null

if [ -n "$doc_backup" ]; then
  printf 'Creating pre-restore document safety backup...\n'
  docker compose run --rm --no-deps -T backend sh -c \
    'mkdir -p /app/data/documents && exec tar -C /app/data -czf - documents' \
    >"$safety_docs"
  tar -tzf "$safety_docs" >/dev/null
fi

services_stopped=false
restore_completed=false
restore_exit() {
  if [ "$services_stopped" = true ] && [ "$restore_completed" != true ]; then
    printf 'Restore did not complete. Backend/frontend remain stopped; use %s to recover.\n' "$safety_db" >&2
  fi
}
trap restore_exit EXIT HUP INT TERM

printf 'Stopping application access during restore...\n'
docker compose stop backend frontend >/dev/null 2>&1 || true
services_stopped=true

printf 'Restoring PostgreSQL...\n'
docker compose exec -T db sh -c \
  'dropdb --force --if-exists -U "$POSTGRES_USER" "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" -O "$POSTGRES_USER" "$POSTGRES_DB"'
docker compose exec -T db sh -c \
  'exec pg_restore --exit-on-error --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  <"$db_backup"

if [ -n "$doc_backup" ]; then
  printf 'Restoring document storage...\n'
  docker compose run --rm --no-deps -T backend sh -c \
    'mkdir -p /app/data/documents && find /app/data/documents -mindepth 1 -delete && exec tar -C /app/data -xzf -' \
    <"$doc_backup"
fi

printf 'Restarting application services...\n'
docker compose up -d backend frontend >/dev/null
services_stopped=false
restore_completed=true
trap - EXIT HUP INT TERM

printf 'Restore complete. Safety backup: %s\n' "$safety_db"
if [ -f "$safety_docs" ]; then
  printf 'Document safety backup: %s\n' "$safety_docs"
fi
printf 'Run ./scripts/status.sh, verify project counts, and test one document download.\n'
