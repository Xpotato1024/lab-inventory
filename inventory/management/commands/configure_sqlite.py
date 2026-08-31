from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Configure SQLite journal mode required by the workstation deployment."

    def handle(self, *args, **options):
        if connection.vendor != "sqlite":
            raise CommandError("configure_sqlite is only valid for the SQLite V1 backend")

        with connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode=WAL")
            row = cursor.fetchone()

        mode = row[0].lower() if row else "unknown"
        if mode != "wal":
            raise CommandError(f"Failed to enable SQLite WAL mode; journal_mode={mode}")

        self.stdout.write(self.style.SUCCESS("SQLite journal_mode=WAL"))
