"""Import MAC movement history from the legacy PyQt database."""

import sqlite3

try:
    from ._bootstrap import ROOT
except ImportError:
    from _bootstrap import ROOT

from server import DATABASE_PATH, STORAGE, init_database

LEGACY = STORAGE.legacy / "mac_history.db"


def main():
    if not LEGACY.exists():
        raise SystemExit("Legacy mac_history.db was not found.")
    init_database()
    old = sqlite3.connect(LEGACY)
    old.row_factory = sqlite3.Row
    new = sqlite3.connect(DATABASE_PATH)
    try:
        rows = old.execute(
            "SELECT mac, field_name, from_value, to_value, source_file, timestamp FROM mac_movements"
        ).fetchall()
    except sqlite3.Error:
        rows = []
    for row in rows:
        new.execute(
            "INSERT INTO mac_movements (mac, field_name, from_value, to_value, source, changed_at) "
            "SELECT ?, ?, ?, ?, ?, ? WHERE NOT EXISTS "
            "(SELECT 1 FROM mac_movements WHERE mac = ? AND field_name = ? AND changed_at = ? AND source = ?)",
            (
                row["mac"], row["field_name"], row["from_value"], row["to_value"],
                row["source_file"], row["timestamp"], row["mac"], row["field_name"],
                row["timestamp"], row["source_file"],
            ),
        )
    new.commit()
    print(f"Imported {len(rows)} legacy movement rows.")


if __name__ == "__main__":
    main()
