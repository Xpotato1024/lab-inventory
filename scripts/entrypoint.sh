#!/bin/sh
set -eu

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

mkdir -p "$(dirname "${LAB_INVENTORY_DB:-/data/db.sqlite3}")" "${LAB_INVENTORY_BACKUP_DIR:-/backups}"

python manage.py migrate --noinput
python manage.py configure_sqlite
python manage.py collectstatic --noinput
python manage.py check --deploy --fail-level ERROR

exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-2}" \
  --threads "${GUNICORN_THREADS:-2}" \
  --access-logfile - \
  --error-logfile -
