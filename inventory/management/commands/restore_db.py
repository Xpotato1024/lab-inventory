import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections

from inventory.db_tools import DatabaseVerificationError, restore_backup


class Command(BaseCommand):
    help = "Restore a verified SQLite backup. Intended to be invoked only by the offline restore wrapper."

    def add_arguments(self, parser):
        parser.add_argument("backup", type=Path)
        parser.add_argument("--confirm-offline", action="store_true")

    def handle(self, *args, **options):
        if not options["confirm_offline"] or os.environ.get("LAB_INVENTORY_RESTORE_MODE") != "1":
            raise CommandError(
                "Restore refused. Use the documented restore wrapper so the web service is stopped first."
            )

        if settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError("restore_db currently supports the accepted SQLite V1 backend only")

        backup = options["backup"]
        target = Path(settings.DATABASES["default"]["NAME"])
        recovery_dir = Path(os.environ.get("LAB_INVENTORY_BACKUP_DIR", "/backups")) / "recovery"

        connections.close_all()
        try:
            recovery_copy = restore_backup(backup, target, recovery_dir)
        except (OSError, DatabaseVerificationError, FileNotFoundError) as exc:
            raise CommandError(str(exc)) from exc

        if recovery_copy:
            self.stdout.write(f"Pre-restore recovery copy: {recovery_copy}")
        self.stdout.write(self.style.SUCCESS(f"Restore completed and verified: {target}"))
