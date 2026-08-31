import sqlite3
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from inventory.db_tools import (
    DatabaseVerificationError,
    online_backup,
    restore_backup,
    verify_sqlite,
)


class SQLiteToolsTests(SimpleTestCase):
    def create_database(self, path: Path, value: str = "original") -> None:
        with sqlite3.connect(path) as connection:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
            connection.execute(
                "CREATE TABLE child (id INTEGER PRIMARY KEY, parent_id INTEGER NOT NULL REFERENCES parent(id))"
            )
            connection.execute("INSERT INTO parent(id, value) VALUES(1, ?)", (value,))
            connection.execute("INSERT INTO child(id, parent_id) VALUES(1, 1)")

    def test_online_backup_creates_verified_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.sqlite3"
            destination = root / "backup.sqlite3"
            self.create_database(source)

            online_backup(source, destination)
            verify_sqlite(destination)

            with sqlite3.connect(destination) as connection:
                value = connection.execute("SELECT value FROM parent WHERE id=1").fetchone()[0]
            self.assertEqual(value, "original")

    def test_restore_preserves_pre_restore_recovery_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.sqlite3"
            backup = root / "backup.sqlite3"
            recovery_dir = root / "recovery"
            self.create_database(target, "current")
            self.create_database(backup, "backup")

            recovery_copy = restore_backup(backup, target, recovery_dir)

            self.assertIsNotNone(recovery_copy)
            verify_sqlite(target)
            verify_sqlite(recovery_copy)
            with sqlite3.connect(target) as connection:
                value = connection.execute("SELECT value FROM parent WHERE id=1").fetchone()[0]
            self.assertEqual(value, "backup")

    def test_verify_rejects_non_database_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.sqlite3"
            path.write_text("not a sqlite database", encoding="utf-8")
            with self.assertRaises((DatabaseVerificationError, sqlite3.DatabaseError)):
                verify_sqlite(path)
