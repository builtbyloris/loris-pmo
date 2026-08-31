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
[ -f .env ] || fail "Missing .env. Copy .env.example to .env and replace all placeholders."

printf 'Starting Loris PMO...\n'
docker compose up -d --build

attempt=0
max_attempts=60
until docker compose exec -T backend python -c \
  "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)" \
  >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge "$max_attempts" ]; then
    docker compose ps
    fail "Backend did not become healthy within 120 seconds. Inspect: docker compose logs backend db"
  fi
  sleep 2
done

printf '\nLoris PMO is ready.\n'
printf 'Frontend:    http://localhost:5173\n'
printf 'Backend:     http://localhost:8000\n'
printf 'API docs:    http://localhost:8000/api/docs\n'
printf 'Health:      http://localhost:8000/health\n'
printf 'Create user: docker compose exec backend python -m app.cli create-user\n'
