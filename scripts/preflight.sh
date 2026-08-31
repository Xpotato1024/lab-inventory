#!/bin/sh
set -eu

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is not installed or not in PATH." >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: Docker Compose v2 is not available." >&2
  exit 1
fi
if [ ! -f .env ]; then
  echo "ERROR: .env does not exist. Copy .env.production.example and edit it first." >&2
  exit 1
fi

set -a
# Production .env values are deliberately restricted to shell-safe host/path/token values.
# shellcheck disable=SC1091
. ./.env
set +a

case "${DJANGO_SECRET_KEY:-}" in
  ""|replace-with-a-long-random-secret|development-only-not-for-production)
    echo "ERROR: DJANGO_SECRET_KEY is missing or still a placeholder." >&2
    exit 1
    ;;
esac

if [ "${DJANGO_DEBUG:-1}" != "0" ]; then
  echo "ERROR: DJANGO_DEBUG must be 0 for the production workstation deployment." >&2
  exit 1
fi

for variable in LAB_INVENTORY_HOST_DATA_DIR LAB_INVENTORY_HOST_BACKUP_DIR; do
  eval "directory=\${$variable:-}"
  if [ -z "$directory" ]; then
    echo "ERROR: $variable is empty." >&2
    exit 1
  fi
  if [ ! -d "$directory" ]; then
    echo "ERROR: $variable does not exist: $directory" >&2
    echo "Create the persistent directory before running preflight." >&2
    exit 1
  fi
  if [ ! -w "$directory" ]; then
    echo "ERROR: $variable is not writable by the current workstation account: $directory" >&2
    exit 1
  fi
done

echo "[1/4] Validate Compose configuration"
docker compose config >/dev/null

echo "[2/4] Build application image"
docker compose build web

echo "[3/4] Run Django deployment checks without starting the service"
docker compose run --rm --no-deps web python manage.py check --deploy --fail-level ERROR

echo "[4/4] Configuration looks usable"
echo "Preflight passed. No long-running application container was started."
