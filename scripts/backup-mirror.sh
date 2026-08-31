#!/bin/sh
set -eu

if [ ! -f .env ]; then
  echo "ERROR: .env does not exist." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
. ./.env
set +a

host_backup_dir=${LAB_INVENTORY_HOST_BACKUP_DIR:-}
offsite_dir=${LAB_INVENTORY_OFFSITE_BACKUP_DIR:-}
container_backup_dir=${LAB_INVENTORY_BACKUP_DIR:-/backups}

if [ -z "$host_backup_dir" ]; then
  echo "ERROR: LAB_INVENTORY_HOST_BACKUP_DIR is empty." >&2
  exit 1
fi
if [ -z "$offsite_dir" ]; then
  echo "ERROR: LAB_INVENTORY_OFFSITE_BACKUP_DIR is empty." >&2
  echo "Configure a mounted path backed by a different physical system before using this script." >&2
  exit 1
fi
if [ ! -d "$host_backup_dir" ] || [ ! -w "$host_backup_dir" ]; then
  echo "ERROR: local host backup directory is missing or not writable: $host_backup_dir" >&2
  exit 1
fi
if [ ! -d "$offsite_dir" ] || [ ! -w "$offsite_dir" ]; then
  echo "ERROR: off-workstation backup directory is missing or not writable: $offsite_dir" >&2
  exit 1
fi

stamp=$(date -u +%Y%m%dT%H%M%SZ)
filename="lab-inventory-${stamp}.sqlite3"
container_output="${container_backup_dir%/}/$filename"
host_output="${host_backup_dir%/}/$filename"
mirror_output="${offsite_dir%/}/$filename"
temporary_mirror="${offsite_dir%/}/.${filename}.tmp.$$"

cleanup() {
  rm -f "$temporary_mirror"
}
trap cleanup EXIT HUP INT TERM

echo "Creating verified online backup: $host_output"
docker compose exec -T web python manage.py backup_db --output "$container_output"

if [ ! -f "$host_output" ]; then
  echo "ERROR: application reported a backup, but the host file is missing: $host_output" >&2
  exit 1
fi

echo "Copying to separate storage: $mirror_output"
cp -p "$host_output" "$temporary_mirror"

if ! cmp -s "$host_output" "$temporary_mirror"; then
  echo "ERROR: mirrored backup differs from verified local backup." >&2
  exit 1
fi

mv "$temporary_mirror" "$mirror_output"
trap - EXIT HUP INT TERM

echo "Backup mirrored successfully: $mirror_output"
