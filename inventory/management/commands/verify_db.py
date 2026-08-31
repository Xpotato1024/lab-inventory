from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from inventory.db_tools import DatabaseVerificationError, verify_sqlite


class Command(BaseCommand):
    help = "Run SQLite integrity and foreign-key checks on the operational DB or a backup."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", type=Path, help="Optional SQLite file to verify")

    def handle(self, *args, **options):
        path = options["path"] or Path(settings.DATABASES["default"]["NAME"])
        try:
            verify_sqlite(path)
        except DatabaseVerificationError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(f"Database verification passed: {path}"))
