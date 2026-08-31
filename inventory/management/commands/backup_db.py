import os
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from inventory.db_tools import DatabaseVerificationError, online_backup


class Command(BaseCommand):
    help = "Create and verify an online SQLite backup without stopping the application."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=Path,
            help="Destination file. Defaults to LAB_INVENTORY_BACKUP_DIR with a timestamp.",
        )

    def handle(self, *args, **options):
        if settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError("backup_db currently supports the accepted SQLite V1 backend only")

        source = Path(settings.DATABASES["default"]["NAME"])
        backup_dir = Path(os.environ.get("LAB_INVENTORY_BACKUP_DIR", "/backups"))
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destination = options["output"] or backup_dir / f"lab-inventory-{timestamp}.sqlite3"

        try:
            result = online_backup(source, destination)
        except (OSError, DatabaseVerificationError, FileNotFoundError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(f"Backup created and verified: {result}"))
