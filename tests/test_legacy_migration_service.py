import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

from legacy_migration_service import migrate_legacy_sqlite
from server import DATABASE_PATH, db_connection, init_database, utc_now


LEGACY_SOURCE = "legacy-file.xlsx"


def cleanup():
    with db_connection() as conn:
        conn.execute("DELETE FROM mac_history WHERE source = ?", (LEGACY_SOURCE,))
        conn.execute("DELETE FROM mac_movements WHERE source = ?", (LEGACY_SOURCE,))
        conn.execute("DELETE FROM vendor_model_history WHERE source = ?", (LEGACY_SOURCE,))
        conn.execute("DELETE FROM snapshots WHERE id = 'legacy-analysis-1'")
        conn.execute("DELETE FROM snapshots WHERE source = 'legacy:vendor_model_history'")
        conn.execute("DELETE FROM vendor_mappings WHERE oui = 'AABBCC'")
        conn.execute("DELETE FROM model_mappings WHERE prefix = 'AABBCCDD01'")
        conn.execute("DELETE FROM performance_metrics WHERE details = 'legacy-test-metric'")


def create_history_db(root: Path):
    conn = sqlite3.connect(root / "mac_history.db")
    conn.executescript(
        """
        CREATE TABLE mac_history (
            id INTEGER PRIMARY KEY,
            mac TEXT,
            mac_formatted TEXT,
            oui_3byte TEXT,
            mac_5byte TEXT,
            timestamp TEXT,
            source_file TEXT,
            vendor TEXT,
            vendor_confidence REAL,
            vendor_source TEXT,
            model TEXT,
            model_confidence REAL,
            model_source TEXT,
            ip TEXT,
            address TEXT,
            room TEXT,
            switch_ip TEXT,
            switch_port TEXT,
            match_details TEXT
        );
        CREATE TABLE mac_movements (
            id INTEGER PRIMARY KEY,
            mac TEXT,
            from_value TEXT,
            to_value TEXT,
            field_name TEXT,
            timestamp TEXT,
            source_file TEXT
        );
        """
    )
    conn.execute(
        "INSERT INTO mac_history (mac, mac_formatted, oui_3byte, timestamp, source_file, vendor, model, ip, address, room, switch_ip, switch_port) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("AABBCCDD0102", "AA:BB:CC:DD:01:02", "AABBCC", "2026-01-01T10:00:00Z", LEGACY_SOURCE, "LegacyVendor", "LegacyModel", "10.0.0.10", "Building 1", "101", "10.0.0.1", "Gi1/0/1"),
    )
    conn.execute(
        "INSERT INTO mac_movements (mac, field_name, from_value, to_value, source_file, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        ("AABBCCDD0102", "room", "100", "101", LEGACY_SOURCE, "2026-01-02T10:00:00Z"),
    )
    conn.commit()
    conn.close()


def create_vendor_model_db(root: Path):
    conn = sqlite3.connect(root / "vendor_model_history.db")
    conn.executescript(
        """
        CREATE TABLE oui_vendor_history (id INTEGER PRIMARY KEY, oui_3byte TEXT, vendor TEXT, occurrences INTEGER, first_seen TEXT, last_seen TEXT);
        CREATE TABLE mac5_model_history (id INTEGER PRIMARY KEY, mac_5byte TEXT, model TEXT, occurrences INTEGER, first_seen TEXT, last_seen TEXT);
        CREATE TABLE history_loads (id INTEGER PRIMARY KEY, filename TEXT, load_date TEXT, devices_count INTEGER, new_vendors_added INTEGER, new_models_added INTEGER, enriched_from_history INTEGER);
        """
    )
    conn.execute("INSERT INTO oui_vendor_history (oui_3byte, vendor) VALUES (?, ?)", ("AABBCC", "LegacyVendor"))
    conn.execute("INSERT INTO mac5_model_history (mac_5byte, model) VALUES (?, ?)", ("AABBCCDD01", "LegacyModel"))
    conn.execute(
        "INSERT INTO history_loads (filename, load_date, devices_count, new_vendors_added, new_models_added, enriched_from_history) VALUES (?, ?, ?, ?, ?, ?)",
        ("legacy-vendors.xlsx", "2026-01-03T10:00:00Z", 7, 1, 1, 2),
    )
    conn.commit()
    conn.close()


def create_stats_db(root: Path):
    conn = sqlite3.connect(root / "mac_analyzer_stats.db")
    conn.executescript(
        """
        CREATE TABLE analysis_history (id INTEGER PRIMARY KEY, timestamp TEXT, filename TEXT, devices_count INTEGER, strategy TEXT, processing_time REAL);
        CREATE TABLE performance_metrics (id INTEGER PRIMARY KEY, operation TEXT, timestamp TEXT, duration_seconds REAL, details TEXT);
        """
    )
    conn.execute(
        "INSERT INTO analysis_history (id, timestamp, filename, devices_count, strategy, processing_time) VALUES (?, ?, ?, ?, ?, ?)",
        (1, "2026-01-04T10:00:00Z", "legacy-analysis.xlsx", 11, "primary", 1.2),
    )
    conn.execute(
        "INSERT INTO performance_metrics (operation, timestamp, duration_seconds, details) VALUES (?, ?, ?, ?)",
        ("legacy_export", "2026-01-05T10:00:00Z", 2.5, "legacy-test-metric"),
    )
    conn.commit()
    conn.close()


def test_legacy_sqlite_migration_dry_run_and_import():
    init_database()
    cleanup()
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        create_history_db(root)
        create_vendor_model_db(root)
        create_stats_db(root)

        dry = migrate_legacy_sqlite(root, DATABASE_PATH, utc_now(), dry_run=True)
        assert dry["summary"]["available"] == 7
        assert dry["summary"]["imported"] == 0

        result = migrate_legacy_sqlite(root, DATABASE_PATH, utc_now(), dry_run=False)
        assert result["summary"]["available"] == 7
        assert result["summary"]["imported"] >= 7
        assert result["summary"]["errors"] == 0

    with db_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM mac_history WHERE source = ?", (LEGACY_SOURCE,)).fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM mac_movements WHERE source = ?", (LEGACY_SOURCE,)).fetchone()[0] == 1
        assert conn.execute("SELECT vendor FROM vendor_mappings WHERE oui = 'AABBCC'").fetchone()["vendor"] == "LegacyVendor"
        assert conn.execute("SELECT model FROM model_mappings WHERE prefix = 'AABBCCDD01'").fetchone()["model"] == "LegacyModel"
        assert conn.execute("SELECT COUNT(*) FROM snapshots WHERE id = 'legacy-analysis-1'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM performance_metrics WHERE details = 'legacy-test-metric'").fetchone()[0] == 1
    cleanup()


if __name__ == "__main__":
    test_legacy_sqlite_migration_dry_run_and_import()
    print("legacy migration service test passed")
