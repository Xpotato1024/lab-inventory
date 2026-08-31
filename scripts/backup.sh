#!/bin/sh
set -eu

docker compose exec -T web python manage.py backup_db
