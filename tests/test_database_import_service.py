import sqlite3
import tempfile
from pathlib import Path

from backend.services.system.database_import_service import inspect_and_merge_database


SCHEMA = """
CREATE TABLE mac_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mac TEXT NOT NULL,
    vendor TEXT,
    source TEXT,
    recorded_at TEXT NOT NULL
);
CREATE TABLE ip_address_mappings (
    switch_ip TEXT PRIMARY KEY,
    physical_address TEXT NOT NULL,
    source TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE smartroom_room_mappings (
    smartroom_id TEXT PRIMARY KEY,
    room TEXT NOT NULL,
    source TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _create_database(path: Path, *, source: bool) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(SCHEMA)
        if source:
            connection.execute(
                "INSERT INTO mac_history (mac, vendor, source, recorded_at) VALUES (?, ?, ?, ?)",
                ("AABBCC000001", "Imported Vendor", "uploaded.sqlite3", "2026-08-05T10:00:00Z"),
            )
            connection.execute(
                "INSERT INTO ip_address_mappings VALUES (?, ?, ?, ?)",
                ("10.0.0.10", "Building A", "uploaded", "2026-08-05T10:00:00Z"),
            )
            connection.execute(
                "INSERT INTO smartroom_room_mappings VALUES (?, ?, ?, ?)",
                ("SR-101", "101", "uploaded", "2026-08-05T10:00:00Z"),
            )
        connection.commit()
    finally:
        connection.close()


def test_database_import_is_validated_additive_and_idempotent():
    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        source = root / "source.sqlite3"
        target = root / "target.sqlite3"
        _create_database(source, source=True)
        _create_database(target, source=False)
        connection = sqlite3.connect(target)
        try:
            connection.execute(
                "INSERT INTO mac_history (mac, vendor, source, recorded_at) VALUES (?, ?, ?, ?)",
                ("AABBCC000099", "Existing Vendor", "current", "2026-08-04T10:00:00Z"),
            )
            connection.execute(
                "INSERT INTO ip_address_mappings VALUES (?, ?, ?, ?)",
                ("10.0.0.10", "Current protected address", "manual", "2026-08-04T10:00:00Z"),
            )
            connection.commit()
        finally:
            connection.close()

        first = inspect_and_merge_database(source, target)
        second = inspect_and_merge_database(source, target)
        assert first["integrity"] == "ok"
        assert first["imported"] == 2
        assert second["imported"] == 0
        connection = sqlite3.connect(target)
        try:
            assert connection.execute("SELECT COUNT(*) FROM mac_history").fetchone()[0] == 2
            assert connection.execute("SELECT physical_address FROM ip_address_mappings WHERE switch_ip = '10.0.0.10'").fetchone()[0] == "Current protected address"
            assert connection.execute("SELECT room FROM smartroom_room_mappings WHERE smartroom_id = 'SR-101'").fetchone()[0] == "101"
        finally:
            connection.close()


def test_database_import_rejects_non_sqlite_file():
    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        source = root / "invalid.sqlite3"
        target = root / "target.sqlite3"
        source.write_bytes(b"not a sqlite database" * 20)
        _create_database(target, source=False)
        try:
            inspect_and_merge_database(source, target)
        except ValueError as error:
            assert "не является базой SQLite" in str(error)
        else:
            raise AssertionError("Invalid SQLite file was accepted")


if __name__ == "__main__":
    test_database_import_is_validated_additive_and_idempotent()
    test_database_import_rejects_non_sqlite_file()
    print("database import service test passed")
