#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <backup-filename>" >&2
  echo "Example: $0 lab-inventory-20260831T120000Z.sqlite3" >&2
  exit 2
fi

backup_name=$(basename "$1")
backup_path="/backups/${backup_name}"

echo "Stopping web service before restore..."
docker compose stop web

echo "Restoring ${backup_name}..."
if ! docker compose run --rm --no-deps \
  -e LAB_INVENTORY_RESTORE_MODE=1 \
  web python manage.py restore_db "${backup_path}" --confirm-offline; then
  echo "Restore failed. The web service remains stopped for investigation." >&2
  exit 1
fi

echo "Starting web service..."
docker compose up -d web

echo "Restore completed. Check service state with: docker compose ps"
