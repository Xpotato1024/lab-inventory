from __future__ import annotations

import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class DatabaseVerificationError(RuntimeError):
    pass


def verify_sqlite(path: Path) -> None:
    path = path.resolve()
    if not path.is_file():
        raise DatabaseVerificationError(f"Database file does not exist: {path}")

    uri = f"file:{path.as_posix()}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True, timeout=10) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or integrity[0] != "ok":
                detail = integrity[0] if integrity else "no result"
                raise DatabaseVerificationError(f"SQLite integrity check failed: {detail}")

            foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
            if foreign_key_errors:
                raise DatabaseVerificationError(
                    f"SQLite foreign-key check found {len(foreign_key_errors)} violation(s)"
                )
    except sqlite3.DatabaseError as exc:
        raise DatabaseVerificationError(f"SQLite verification failed for {path}: {exc}") from exc


def online_backup(source: Path, destination: Path) -> Path:
    source = source.resolve()
    destination = destination.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    if temporary.exists():
        temporary.unlink()

    try:
        try:
            with sqlite3.connect(source, timeout=10) as source_connection:
                with sqlite3.connect(temporary, timeout=10) as destination_connection:
                    source_connection.backup(destination_connection)
        except sqlite3.DatabaseError as exc:
            raise DatabaseVerificationError(f"SQLite backup failed: {exc}") from exc

        verify_sqlite(temporary)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()

    return destination


def restore_backup(backup: Path, target: Path, recovery_dir: Path) -> Path | None:
    backup = backup.resolve()
    target = target.resolve()
    recovery_dir = recovery_dir.resolve()

    verify_sqlite(backup)
    target.parent.mkdir(parents=True, exist_ok=True)
    recovery_dir.mkdir(parents=True, exist_ok=True)

    recovery_copy: Path | None = None
    if target.exists():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        recovery_copy = recovery_dir / f"pre-restore-{timestamp}.sqlite3"
        online_backup(target, recovery_copy)

    temporary = target.with_name(f".{target.name}.restore.tmp")
    if temporary.exists():
        temporary.unlink()

    try:
        shutil.copy2(backup, temporary)
        verify_sqlite(temporary)

        for suffix in ("-wal", "-shm"):
            companion = Path(f"{target}{suffix}")
            if companion.exists():
                companion.unlink()

        os.replace(temporary, target)
        verify_sqlite(target)
    finally:
        if temporary.exists():
            temporary.unlink()

    return recovery_copy
