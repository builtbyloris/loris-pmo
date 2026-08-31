#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

if ! command -v docker >/dev/null 2>&1; then
  printf 'Error: Docker is not installed or not on PATH.\n' >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  printf 'Error: Docker is unavailable. Start Docker Desktop/Engine and try again.\n' >&2
  exit 1
fi

printf '%s\n' 'Loris PMO Compose services:'
docker compose ps

if docker compose exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
  printf 'PostgreSQL: healthy\n'
else
  printf 'PostgreSQL: unavailable or not ready\n' >&2
fi

status_file=$(mktemp "${TMPDIR:-/tmp}/loris-pmo-status.XXXXXX")
trap 'rm -f -- "$status_file"' EXIT HUP INT TERM
if docker compose exec -T backend python -c \
  "import json, urllib.request; payload=json.load(urllib.request.urlopen('http://localhost:8000/health', timeout=2)); assert payload['status']=='ok'; print(payload.get('version', 'unknown'))" \
  >"$status_file" 2>/dev/null; then
  version=$(cat "$status_file")
  printf 'Backend: healthy (version %s)\n' "$version"
else
  printf 'Backend: unavailable or not healthy\n' >&2
  exit 1
fi
