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

printf 'Stopping Loris PMO without deleting PostgreSQL or document volumes...\n'
docker compose down
printf 'Stopped. Data volumes were retained. Never add -v unless permanent local data deletion is intended.\n'
