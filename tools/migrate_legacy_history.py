"""Import MAC history from the legacy PyQt SQLite database into the web database."""

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
    rows = old.execute(
        "SELECT mac, mac_formatted, oui_3byte, vendor, model, ip, address, room, "
        "switch_ip, switch_port, source_file, timestamp FROM mac_history"
    ).fetchall()
    for row in rows:
        new.execute(
            "INSERT INTO mac_history (mac, mac_formatted, oui, vendor, model, ip, address, room, switch_ip, switch_port, source, recorded_at) "
            "SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? "
            "WHERE NOT EXISTS (SELECT 1 FROM mac_history WHERE mac = ? AND recorded_at = ? AND source = ?)",
            (
                row["mac"], row["mac_formatted"] or row["mac"], row["oui_3byte"], row["vendor"],
                row["model"], row["ip"], row["address"], row["room"], row["switch_ip"],
                row["switch_port"], row["source_file"], row["timestamp"],
                row["mac"], row["timestamp"], row["source_file"],
            ),
        )
    new.commit()
    print(f"Imported {len(rows)} legacy history rows.")


if __name__ == "__main__":
    main()
