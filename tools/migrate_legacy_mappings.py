"""Import vendor and model mappings learned by the legacy application."""

import sqlite3

try:
    from ._bootstrap import ROOT
except ImportError:
    from _bootstrap import ROOT

from server import DATABASE_PATH, STORAGE, init_database, utc_now

LEGACY = STORAGE.legacy / "vendor_model_history.db"


def main():
    if not LEGACY.exists():
        raise SystemExit("Legacy vendor_model_history.db was not found.")
    init_database()
    old = sqlite3.connect(LEGACY)
    old.row_factory = sqlite3.Row
    new = sqlite3.connect(DATABASE_PATH)
    imported = 0
    for table, key, value, target, target_key, target_value in (
        ("oui_vendor_history", "oui_3byte", "vendor", "vendor_mappings", "oui", "vendor"),
        ("mac5_model_history", "mac_5byte", "model", "model_mappings", "prefix", "model"),
    ):
        try:
            rows = old.execute(f"SELECT {key}, {value} FROM {table}").fetchall()
        except sqlite3.Error:
            continue
        for row in rows:
            if not row[key] or not row[value]:
                continue
            new.execute(
                f"INSERT INTO {target} ({target_key}, {target_value}, source, updated_at) VALUES (?, ?, 'legacy', ?) "
                f"ON CONFLICT({target_key}) DO UPDATE SET {target_value}=excluded.{target_value}, source='legacy', updated_at=excluded.updated_at",
                (str(row[key]).upper(), row[value], utc_now()),
            )
            imported += 1
    new.commit()
    print(f"Imported {imported} legacy mappings.")


if __name__ == "__main__":
    main()
