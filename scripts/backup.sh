#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

fail() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || fail "Docker is not installed or not on PATH."
docker info >/dev/null 2>&1 || fail "Docker is unavailable. Start Docker Desktop/Engine and try again."
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is unavailable."
[ -f .env ] || fail "Missing .env."
docker compose ps --services --status running | grep -qx db || fail "The Compose database service is not running."
docker compose ps --services --status running | grep -qx backend || fail "The Compose backend service is not running."

mkdir -p backups
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
db_file="backups/loris-pmo-${timestamp}.dump"
doc_file="backups/loris-pmo-documents-${timestamp}.tar.gz"
db_tmp="${db_file}.tmp"
doc_tmp="${doc_file}.tmp"
trap 'rm -f -- "$db_tmp" "$doc_tmp"' EXIT HUP INT TERM

printf 'Backing up PostgreSQL...\n'
docker compose exec -T db sh -c \
  'exec pg_dump --format=custom --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  >"$db_tmp"
[ -s "$db_tmp" ] || fail "PostgreSQL produced an empty dump."
docker compose exec -T db pg_restore --list <"$db_tmp" >/dev/null

printf 'Backing up private document storage...\n'
docker compose exec -T backend sh -c \
  'mkdir -p /app/data/documents && exec tar -C /app/data -czf - documents' \
  >"$doc_tmp"
[ -s "$doc_tmp" ] || fail "Document storage produced an empty archive."
tar -tzf "$doc_tmp" >/dev/null

mv "$db_tmp" "$db_file"
mv "$doc_tmp" "$doc_file"
trap - EXIT HUP INT TERM

printf 'Backup complete:\n  %s\n  %s\n' "$db_file" "$doc_file"
printf 'The backups/ directory is gitignored. Store both files securely and keep matching timestamps together.\n'
