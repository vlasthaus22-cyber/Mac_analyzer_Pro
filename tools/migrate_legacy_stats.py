"""Import analysis history rows from the legacy statistics SQLite database."""

import sqlite3

try:
    from ._bootstrap import ROOT
except ImportError:
    from _bootstrap import ROOT

from server import DATABASE_PATH, STORAGE, init_database

LEGACY = STORAGE.legacy / "mac_analyzer_stats.db"


def main():
    if not LEGACY.exists():
        raise SystemExit("Legacy mac_analyzer_stats.db was not found.")
    init_database()
    old = sqlite3.connect(LEGACY)
    old.row_factory = sqlite3.Row
    new = sqlite3.connect(DATABASE_PATH)
    try:
        rows = old.execute("SELECT * FROM analysis_history").fetchall()
    except sqlite3.Error:
        rows = []
    for row in rows:
        data = dict(row)
        name = str(data.get("filename") or "Legacy analysis")
        created_at = str(data.get("timestamp") or data.get("date") or "1970-01-01T00:00:00Z")
        new.execute(
            "INSERT OR IGNORE INTO snapshots (id, name, source, device_count, devices_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "legacy-" + str(data.get("id") or created_at),
                name,
                name,
                int(data.get("total_devices") or 0),
                "[]",
                created_at,
            ),
        )
    new.commit()
    print(f"Imported {len(rows)} legacy statistics rows.")


if __name__ == "__main__":
    main()
